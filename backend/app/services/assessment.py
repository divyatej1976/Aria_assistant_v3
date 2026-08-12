from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.assessment.formats import format_registry
from app.assessment.mcq import (
    GeneratedMCQ,
    generate_mcqs_deterministic,
    generate_mcqs_structured,
)
from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AttemptAnswer,
    Evaluation,
)
from app.services.concepts import list_concepts, sync_concepts
from app.services.evidence import record_assessment_evidence
from app.services.text import tokenize


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
    concept_ids: list[str],
) -> Assessment:
    definition = format_registry.get(format_name)
    if definition.name != "mcq":
        raise ValidationError(f"Format registry entry has no R0 generator: {definition.name}")
    await sync_concepts(db, owner_id=owner_id, context_id=context_id)
    settings = get_settings()
    if settings.groq_api_key:
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
        db, owner_id=owner_id, context_id=context_id, questions=questions
    )
    assessment = Assessment(
        owner_id=owner_id,
        context_id=context_id,
        format=definition.name,
        mode=mode,
        configuration={
            "question_count": question_count,
            "difficulty": difficulty,
            "concept_ids": concept_ids,
        },
    )
    db.add(assessment)
    db.flush()
    _persist_questions(db, owner_id=owner_id, assessment_id=assessment.id, questions=questions)
    db.commit()
    db.refresh(assessment)
    return assessment


def _assign_question_concepts(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    questions: list[GeneratedMCQ],
) -> list[GeneratedMCQ]:
    concepts = list_concepts(db, owner_id=owner_id, context_id=context_id)
    concept_terms = [(concept.id, set(tokenize(concept.name))) for concept in concepts]
    assigned: list[GeneratedMCQ] = []
    for question in questions:
        letter_index = "ABCD".index(question.correct_option)
        option_text = question.options[letter_index]
        option_terms = set(tokenize(option_text))
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


def _replace_answers(
    db: Session,
    *,
    owner_id: UUID,
    attempt_id: UUID,
    assessment_id: UUID,
    answers: dict[str, str],
) -> None:
    db.execute(delete(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt_id))
    valid = _question_ids(db, owner_id=owner_id, assessment_id=assessment_id)
    for question_id, selected in answers.items():
        try:
            parsed = UUID(question_id)
        except ValueError:
            continue
        if parsed in valid:
            db.add(
                AttemptAnswer(
                    owner_id=owner_id,
                    attempt_id=attempt_id,
                    question_id=parsed,
                    selected_option=selected,
                )
            )


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
        evaluation = db.scalar(select(Evaluation).where(Evaluation.attempt_id == existing.id))
        if evaluation is None:
            raise ValidationError("Existing attempt is not evaluable yet")
        return existing, evaluation, evaluation.details.get("questions", [])

    attempt = get_owned_attempt(db, owner_id=owner_id, attempt_id=attempt_id)
    if attempt is None:
        raise ValidationError("Attempt not found or not owned by learner")
    already = db.scalar(select(Evaluation).where(Evaluation.attempt_id == attempt.id))
    if already is not None:
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

    questions = list_assessment_questions(
        db, assessment_id=attempt.assessment_id, owner_id=owner_id
    )
    if not questions:
        raise ValidationError("Assessment has no questions")
    saved = {
        answer.question_id: answer.selected_option
        for answer in db.scalars(
            select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)
        )
    }
    details: list[dict[str, object]] = []
    score = 0
    for question in questions:
        selected = saved.get(question.id)
        correct = selected == question.correct_option
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
    db.flush()
    record_assessment_evidence(
        db,
        owner_id=owner_id,
        attempt_id=attempt.id,
        evaluation_id=evaluation.id,
        details=details,
    )
    db.commit()
    db.refresh(attempt)
    db.refresh(evaluation)
    return attempt, evaluation, details
