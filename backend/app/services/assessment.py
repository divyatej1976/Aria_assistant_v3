import logging
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
from app.core.errors import ValidationError
from app.db.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AttemptAnswer,
    Concept,
    Evaluation,
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
) -> Assessment:
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
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
    if definition.name != "mcq":
        raise ValidationError(f"Format registry entry has no R0 generator: {definition.name}")
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
        except Exception:
            questions = generate_mcqs_deterministic(
                db,
                owner_id=owner_id,
                context_id=context_id,
                count=question_count,
                difficulty=difficulty,
                concept_ids=concept_ids,
            )
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
    questions = _assign_question_concepts(
        db, owner_id=owner_id, context_id=context_id, questions=questions,
        allowed_ids=selected_ids if study_transcript is not None else None,
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
            **({"source": "tutoring_conversation", "mastery_evidence": bool(selected_ids)}
               if study_transcript is not None else {}),
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


def _assign_question_concepts(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    questions: list[GeneratedMCQ],
    allowed_ids: set[UUID] | None = None,
) -> list[GeneratedMCQ]:
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
            options = question.options
            if allowed_ids is not None:
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
        assigned.append(
            GeneratedMCQ(
                prompt=question.prompt,
                options=question.options,
                correct_option=question.correct_option,
                concept_id=concept_id,
            )
        )
    return assigned


def _persist_questions(
    db: Session, *, owner_id: UUID, assessment_id: UUID, questions: list[GeneratedMCQ]
) -> None:
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
