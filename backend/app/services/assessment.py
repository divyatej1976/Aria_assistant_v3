import logging
import random
from dataclasses import replace
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.registry import get_llm_provider_for_owner
from app.assessment.formats import format_registry
from app.assessment.mcq import (
    GeneratedMCQ,
    generate_conversation_mcqs,
    generate_mcqs_deterministic,
    generate_mcqs_structured,
)
from app.assessment.shapes import correct_text, shape_questions, short_answer_matches
from app.core.errors import ValidationError
from app.db.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AttemptAnswer,
    Concept,
    ConversationMessage,
    Evaluation,
    LearnerConceptState,
    StudySession,
)
from app.services.concepts import list_concepts, sync_concepts
from app.services.contexts import get_owned_context
from app.services.evidence import record_assessment_evidence
from app.services.text import tokenize

logger = logging.getLogger(__name__)


def get_owned_assessment(
    db: Session, *, owner_id: UUID, assessment_id: UUID
) -> Assessment | None:
    return db.scalar(
        select(Assessment).where(
            Assessment.id == assessment_id, Assessment.owner_id == owner_id
        )
    )


def get_owned_attempt(
    db: Session, *, owner_id: UUID, attempt_id: UUID
) -> AssessmentAttempt | None:
    return db.scalar(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id, AssessmentAttempt.owner_id == owner_id
        )
    )


SOURCES = ("library", "chats", "topic", "weak")


def chats_transcript(db: Session, *, owner_id: UUID, context_id: UUID, session_ids: list[UUID]) -> str:
    """The learner's chosen chats in this subject, as one transcript to quiz on."""
    if not session_ids:
        raise ValidationError("Choose at least one chat to quiz on")
    owned = set(db.scalars(select(StudySession.id).where(
        StudySession.id.in_(session_ids), StudySession.owner_id == owner_id,
        StudySession.context_id == context_id,
    )))
    if owned != set(session_ids):
        raise ValidationError("Selected chats do not belong to this subject")
    messages = db.scalars(select(ConversationMessage).where(
        ConversationMessage.study_session_id.in_(owned), ConversationMessage.owner_id == owner_id,
        ConversationMessage.role.in_(("user", "assistant")),
    ).order_by(ConversationMessage.study_session_id, ConversationMessage.position)).all()
    if not any(message.role == "assistant" for message in messages):
        raise ValidationError("These chats have no tutor answers yet. Chat with ARIA first, then make a quiz.")
    return "\n\n".join(message.content.strip() for message in messages if message.content.strip())[-20_000:]


def weak_concept_ids(db: Session, *, owner_id: UUID, context_id: UUID) -> list[UUID]:
    rows = db.scalars(select(LearnerConceptState.concept_id).join(
        Concept, Concept.id == LearnerConceptState.concept_id,
    ).where(
        LearnerConceptState.owner_id == owner_id, Concept.owner_id == owner_id,
        Concept.context_id == context_id,
        LearnerConceptState.state.in_(("NEEDS_REVIEW", "DEVELOPING")),
    ))
    return list(dict.fromkeys(rows))


async def create_assessment(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    format_name: str,
    question_count: int,
    difficulty: str,
    mode: str,
    concept_ids: list[UUID | str],
    study_transcript: str | None = None,
    daily_review_date: str | None = None,
    source: str = "library",
    session_ids: list[UUID] | None = None,
    topic: str | None = None,
    settings: dict | None = None,
) -> Assessment:
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    if source not in SOURCES:
        raise ValidationError(f"Unsupported quiz source: {source}")
    if study_transcript is None and source == "chats":
        study_transcript = chats_transcript(db, owner_id=owner_id, context_id=context_id,
                                            session_ids=list(session_ids or []))
    elif study_transcript is None and source == "topic":
        if not (topic or "").strip():
            raise ValidationError("Type a topic to quiz on")
        if get_llm_provider_for_owner(db, owner_id=owner_id) is None:
            raise ValidationError("Topic quizzes need the AI tutor. Choose your chats or library instead.")
        study_transcript = f"Topic chosen by the learner: {topic.strip()[:300]}"
    elif source == "weak":
        concept_ids = weak_concept_ids(db, owner_id=owner_id, context_id=context_id)
        if not concept_ids:
            raise ValidationError("No weak spots yet. Take a quiz first so ARIA can see what to review.")
    try:
        selected_ids = {UUID(str(value)) for value in (concept_ids or [])}
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError("Invalid concept ID") from exc
    if selected_ids:
        valid_ids = set(db.scalars(select(Concept.id).where(
            Concept.id.in_(selected_ids), Concept.owner_id == owner_id, Concept.context_id == context_id,
        )))
        if valid_ids != selected_ids:
            raise ValidationError("Selected concepts do not belong to this subject")
    definition = format_registry.get(format_name)
    if study_transcript is None:
        await sync_concepts(db, owner_id=owner_id, context_id=context_id)
    if study_transcript is not None:
        questions = await generate_conversation_mcqs(
            db, owner_id=owner_id, transcript=study_transcript,
            count=question_count, difficulty=difficulty,
        )
    elif get_llm_provider_for_owner(db, owner_id=owner_id) is not None:
        try:
            questions = await generate_mcqs_structured(
                db,
                owner_id=owner_id,
                context_id=context_id,
                count=question_count,
                difficulty=difficulty,
                concept_ids=concept_ids,
            )
        except ValidationError:
            raise
        except Exception as exc:
            # Quotation drills from raw PDF text read as broken questions; an honest retry beats them.
            logger.warning("library quiz generation failed", exc_info=True)
            raise ValidationError("ARIA couldn't write your questions just now. Please try again.") from exc
    else:
        questions = generate_mcqs_deterministic(
            db,
            owner_id=owner_id,
            context_id=context_id,
            count=question_count,
            difficulty=difficulty,
            concept_ids=concept_ids,
        )
    if not questions:
        raise ValidationError("Add ready study material before creating an assessment")
    questions = shape_questions(questions, definition.name, seed=str(uuid4()))
    # Quizzes the learner chose (their chats, a topic, their library) file answers under the AI's
    # topic labels, so every quiz builds up Progress; the automatic daily review stays as it was.
    learner_chosen = source in ("chats", "topic", "library") and mode != "DAILY_REVIEW"
    questions = _assign_question_concepts(
        db, owner_id=owner_id, context_id=context_id, questions=questions,
        allowed_ids=selected_ids if study_transcript is not None and not learner_chosen else None,
        create_named=learner_chosen,
    )
    assessment = Assessment(
        owner_id=owner_id,
        context_id=context_id,
        format=definition.name,
        mode=mode,
        daily_review_date=daily_review_date,
        configuration={
            "question_count": question_count,
            "difficulty": difficulty,
            "concept_ids": [str(c) for c in (concept_ids or [])],
            "source": source,
            "session_ids": [str(value) for value in (session_ids or [])],
            "topic": topic,
            **(settings or {}),
            **({"source": "tutoring_conversation", "mastery_evidence": bool(selected_ids)}
               if study_transcript is not None and source == "library" else {}),
        },
    )
    db.add(assessment)
    try:
        db.flush()
        _persist_questions(db, owner_id=owner_id, assessment_id=assessment.id, questions=questions)
        db.commit()
    except IntegrityError:
        db.rollback()
        if daily_review_date is not None:
            existing = db.scalar(select(Assessment).where(
                Assessment.owner_id == owner_id, Assessment.context_id == context_id,
                Assessment.daily_review_date == daily_review_date,
            ))
            if existing is not None:
                return existing
        raise
    db.refresh(assessment)
    return assessment


def _concepts_from_labels(
    db: Session, *, owner_id: UUID, context_id: UUID, questions: list[GeneratedMCQ]
) -> list[GeneratedMCQ]:
    """Link each labelled question to the subject's concept of that name, creating it if new."""
    labels = {q.concept_name.casefold(): q.concept_name for q in questions if q.concept_name and q.concept_id is None}
    if not labels:
        return questions
    by_name = {c.name.casefold(): c for c in list_concepts(db, owner_id=owner_id, context_id=context_id)}
    for key, name in labels.items():
        if key not in by_name:
            by_name[key] = Concept(owner_id=owner_id, context_id=context_id, name=name)
            db.add(by_name[key])
    db.flush()
    return [replace(q, concept_id=by_name[q.concept_name.casefold()].id)
            if q.concept_name and q.concept_id is None else q for q in questions]


def _assign_question_concepts(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    questions: list[GeneratedMCQ],
    allowed_ids: set[UUID] | None = None,
    create_named: bool = False,
) -> list[GeneratedMCQ]:
    if create_named:
        questions = _concepts_from_labels(db, owner_id=owner_id, context_id=context_id, questions=questions)
    concepts = list_concepts(db, owner_id=owner_id, context_id=context_id)
    if allowed_ids is not None:
        concepts = [concept for concept in concepts if concept.id in allowed_ids]
    valid_ids = {concept.id for concept in concepts}
    concept_terms = [(concept.id, set(tokenize(concept.name))) for concept in concepts]
    assigned: list[GeneratedMCQ] = []
    for question in questions:
        concept_id = question.concept_id
        if concept_id is not None and concept_id not in valid_ids:
            raise ValidationError("Generated question references a concept outside this subject")
        if concept_id is None:
            option_terms = set()
            options = question.options or [question.correct_option]
            if allowed_ids is not None and question.options:
                correct = question.correct_option
                if correct in "ABCD" and len(correct) == 1:
                    options = [question.options["ABCD".index(correct)]]
                else:
                    options = [correct] if correct in question.options else []
            for option in options:
                option_terms.update(tokenize(option))
            concept_id = next(
                (
                    concept_id
                    for concept_id, terms in concept_terms
                    if terms and terms <= option_terms
                ),
                None,
            )
        assigned.append(replace(question, concept_id=concept_id))
    return assigned


def shuffle_options(question: GeneratedMCQ, rng: random.Random | None = None) -> GeneratedMCQ:
    """Shuffle a multiple-choice question so the answer isn't usually first (LLMs favour option A)."""
    options, correct = list(question.options or []), question.correct_option
    if question.kind != "mcq" or len(options) < 2:
        return question
    letters = "ABCDEFGH"[: len(options)]
    is_letter = len(correct) == 1 and correct in letters
    answer = options[letters.index(correct)] if is_letter else correct
    if answer not in options:
        return question
    (rng or random).shuffle(options)
    return replace(question, options=options, correct_option=letters[options.index(answer)] if is_letter else answer)


def _persist_questions(
    db: Session, *, owner_id: UUID, assessment_id: UUID, questions: list[GeneratedMCQ]
) -> None:
    # Seeded by the prompt: answer positions vary across questions but are reproducible.
    questions = [shuffle_options(question, random.Random(question.prompt)) for question in questions]
    for position, question in enumerate(questions, start=1):
        db.add(
            AssessmentQuestion(
                owner_id=owner_id,
                assessment_id=assessment_id,
                concept_id=question.concept_id,
                position=position,
                prompt=question.prompt,
                options=question.options,
                correct_option=question.correct_option,
                kind=question.kind,
                explanation=question.explanation,
            )
        )


def list_assessment_questions(
    db: Session, *, assessment_id: UUID, owner_id: UUID
) -> list[AssessmentQuestion]:
    return list(
        db.scalars(
            select(AssessmentQuestion)
            .where(
                AssessmentQuestion.assessment_id == assessment_id,
                AssessmentQuestion.owner_id == owner_id,
            )
            .order_by(AssessmentQuestion.position)
        )
    )


def start_attempt(db: Session, *, owner_id: UUID, assessment_id: UUID) -> AssessmentAttempt:
    assessment = get_owned_assessment(db, owner_id=owner_id, assessment_id=assessment_id)
    if assessment is None:
        raise ValidationError("Assessment not found or not owned by learner")
    attempt = AssessmentAttempt(
        owner_id=owner_id,
        assessment_id=assessment_id,
        status="IN_PROGRESS",
        idempotency_key=str(uuid4()),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def save_answers(
    db: Session, *, owner_id: UUID, attempt_id: UUID, answers: dict[str, str]
) -> AssessmentAttempt:
    attempt = get_owned_attempt(db, owner_id=owner_id, attempt_id=attempt_id)
    if attempt is None:
        raise ValidationError("Attempt not found or not owned by learner")
    if attempt.status == "SUBMITTED":
        raise ValidationError("Attempt already submitted")
    _replace_answers(
        db,
        owner_id=owner_id,
        attempt_id=attempt.id,
        assessment_id=attempt.assessment_id,
        answers=answers,
    )
    db.commit()
    db.refresh(attempt)
    return attempt


def answer_text(question: AssessmentQuestion) -> str:
    return question.correct_option if question.kind == "short_answer" else correct_text(question)


def check_answer(
    db: Session, *, owner_id: UUID, attempt_id: UUID, question_id: UUID, answer: str,
) -> tuple[bool, str, str | None]:
    """Save one answer and say whether it is right (practice mode only)."""
    attempt = get_owned_attempt(db, owner_id=owner_id, attempt_id=attempt_id)
    if attempt is None:
        raise ValidationError("Attempt not found or not owned by learner")
    if attempt.status == "SUBMITTED":
        raise ValidationError("Attempt already submitted")
    question = db.scalar(select(AssessmentQuestion).where(
        AssessmentQuestion.id == question_id, AssessmentQuestion.owner_id == owner_id,
        AssessmentQuestion.assessment_id == attempt.assessment_id,
    ))
    if question is None:
        raise ValidationError("Question does not belong to this assessment")
    saved = db.scalar(select(AttemptAnswer).where(
        AttemptAnswer.attempt_id == attempt.id, AttemptAnswer.owner_id == owner_id,
        AttemptAnswer.question_id == question.id,
    ))
    if saved is None:
        db.add(AttemptAnswer(owner_id=owner_id, attempt_id=attempt.id, question_id=question.id,
                             selected_option=answer))
    else:
        saved.selected_option = answer
    db.commit()
    return _answer_is_correct(question, answer), answer_text(question), question.explanation


def _question_ids(db: Session, *, owner_id: UUID, assessment_id: UUID) -> set[UUID]:
    rows = db.execute(
        select(AssessmentQuestion.id).where(
            AssessmentQuestion.assessment_id == assessment_id,
            AssessmentQuestion.owner_id == owner_id,
        )
    )
    return {row[0] for row in rows}


def _answer_is_correct(question: AssessmentQuestion, selected: str | None) -> bool:
    """Compare a submitted answer with the correct option.

    Accepts both contracts: the option LETTER (A-D, stored in correct_option,
    used by API probes) and the option TEXT (what the UI and E2E helpers
    submit, e.g. "Loops repeat a block while a condition holds"). Comparing
    raw text to the letter scored every UI answer wrong on lenient SQLite.
    """
    if selected is None:
        return False
    if question.kind == "short_answer":
        return short_answer_matches(question.correct_option, selected)
    if selected == question.correct_option:
        return True
    try:
        letter = "ABCD"[question.options.index(selected)]
    except (ValueError, IndexError):
        return False
    return letter == question.correct_option


def _replace_answers(
    db: Session,
    *,
    owner_id: UUID,
    attempt_id: UUID,
    assessment_id: UUID,
    answers: dict[str, str],
) -> None:
    valid = _question_ids(db, owner_id=owner_id, assessment_id=assessment_id)
    try:
        parsed_answers = {UUID(str(question_id)): selected for question_id, selected in answers.items()}
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError("Invalid question ID") from exc
    if len(parsed_answers) != len(answers):
        raise ValidationError("Duplicate question IDs")
    if not set(parsed_answers) <= valid:
        raise ValidationError("Questions do not belong to this assessment")
    db.execute(delete(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt_id, AttemptAnswer.owner_id == owner_id))
    for question_id, selected in parsed_answers.items():
        db.add(AttemptAnswer(owner_id=owner_id, attempt_id=attempt_id,
                             question_id=question_id, selected_option=selected))


def _validate_replayed_answers(db: Session, *, owner_id: UUID, attempt_id: UUID, answers: dict[str, str]) -> None:
    # Empty means "submit the autosaved answers" in the existing API contract.
    if not answers:
        return
    try:
        requested = {UUID(str(key)): value for key, value in answers.items()}
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError("Invalid question ID") from exc
    if len(requested) != len(answers):
        raise ValidationError("Duplicate question IDs")
    saved = {row.question_id: row.selected_option for row in db.scalars(
        select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt_id, AttemptAnswer.owner_id == owner_id)
    )}
    if requested != saved:
        raise ValidationError("Submission answers differ from the completed attempt")


def submit_attempt(
    db: Session,
    *,
    owner_id: UUID,
    attempt_id: UUID,
    idempotency_key: str,
    answers: dict[str, str],
) -> tuple[AssessmentAttempt, Evaluation, list[dict[str, object]]]:
    existing = db.scalar(
        select(AssessmentAttempt).where(
            AssessmentAttempt.idempotency_key == idempotency_key,
            AssessmentAttempt.owner_id == owner_id,
        )
    )
    if existing is not None:
        if existing.id != attempt_id:
            raise ValidationError("Idempotency key belongs to another attempt")
        evaluation = db.scalar(select(Evaluation).where(Evaluation.attempt_id == existing.id))
        if evaluation is None:
            raise ValidationError("Existing attempt is not evaluable yet")
        _validate_replayed_answers(db, owner_id=owner_id, attempt_id=existing.id, answers=answers)
        return existing, evaluation, evaluation.details.get("questions", [])

    attempt = get_owned_attempt(db, owner_id=owner_id, attempt_id=attempt_id)
    if attempt is None:
        raise ValidationError("Attempt not found or not owned by learner")
    already = db.scalar(select(Evaluation).where(Evaluation.attempt_id == attempt.id))
    if already is not None:
        _validate_replayed_answers(db, owner_id=owner_id, attempt_id=attempt.id, answers=answers)
        return attempt, already, already.details.get("questions", [])
    if attempt.status == "SUBMITTED":
        raise ValidationError("Attempt already submitted")

    if answers:
        _replace_answers(
            db,
            owner_id=owner_id,
            attempt_id=attempt.id,
            assessment_id=attempt.assessment_id,
            answers=answers,
        )
        db.flush()

    questions = list_assessment_questions(
        db, assessment_id=attempt.assessment_id, owner_id=owner_id
    )
    if not questions:
        raise ValidationError("Assessment has no questions")
    saved = {
        answer.question_id: answer.selected_option
        for answer in db.scalars(
            select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id, AttemptAnswer.owner_id == owner_id)
        )
    }
    details: list[dict[str, object]] = []
    score = 0
    for question in questions:
        selected = saved.get(question.id)
        correct = _answer_is_correct(question, selected)
        score += int(correct)
        details.append(
            {
                "question_id": str(question.id),
                "selected_option": selected,
                "correct": correct,
                "correct_option": question.correct_option,
                "correct_answer": answer_text(question),
                "explanation": question.explanation,
                "concept_id": str(question.concept_id) if question.concept_id else None,
            }
        )
    evaluation = Evaluation(
        owner_id=owner_id,
        attempt_id=attempt.id,
        status="COMPLETED",
        score=score,
        details={"total": len(questions), "questions": details},
    )
    attempt.status = "SUBMITTED"
    attempt.idempotency_key = idempotency_key
    db.add(attempt)
    db.add(evaluation)
    try:
        db.flush()
    except IntegrityError:
        # Concurrent duplicate submit won the race (same attempt evaluated
        # twice, or two attempts stamped with the same key): replay the
        # winner instead of 500ing or double-applying evidence.
        db.rollback()
        winner = db.scalar(
            select(AssessmentAttempt).where(
                AssessmentAttempt.idempotency_key == idempotency_key,
                AssessmentAttempt.owner_id == owner_id,
            )
        )
        if winner is None:
            winner = get_owned_attempt(db, owner_id=owner_id, attempt_id=attempt_id)
        if winner is not None and winner.id != attempt_id:
            raise ValidationError("Idempotency key belongs to another attempt") from None
        if winner is None:
            raise ValidationError("Attempt already submitted") from None
        won = db.scalar(select(Evaluation).where(Evaluation.attempt_id == winner.id))
        if won is None:
            raise ValidationError("Existing attempt is not evaluable yet") from None
        _validate_replayed_answers(db, owner_id=owner_id, attempt_id=winner.id, answers=answers)
        return winner, won, won.details.get("questions", [])
    record_assessment_evidence(
        db,
        owner_id=owner_id,
        attempt_id=attempt.id,
        evaluation_id=evaluation.id,
        details=details,
    )
    db.commit()
    from app.services.notifications import dispatch_notification

    try:
        dispatch_notification(
            db,
            owner_id=owner_id,
            ntype="assessment_result",
            title=f"Assessment complete: {score}/{len(questions)}",
            body=(
                f"You scored {score} of {len(questions)} on the assessment. "
                "Open Progress to see how your learner model updated."
            ),
        )
    except Exception:
        logger.exception("assessment result notification failed")
    db.refresh(attempt)
    db.refresh(evaluation)
    return attempt, evaluation, details
