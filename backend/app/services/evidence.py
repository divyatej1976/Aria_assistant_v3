from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.models import Assessment, AssessmentAttempt, AssessmentQuestion, Concept, Evaluation, Evidence
from app.services.contexts import get_owned_context

SIGNAL_CORRECT = "CORRECT"
SIGNAL_INCORRECT = "INCORRECT"


def record_assessment_evidence(
    db: Session,
    *,
    owner_id: UUID,
    attempt_id: UUID,
    evaluation_id: UUID,
    details: list[dict[str, object]],
) -> list[Evidence]:
    context_id = db.scalar(select(Assessment.context_id)
        .join(AssessmentAttempt, AssessmentAttempt.assessment_id == Assessment.id)
        .join(Evaluation, Evaluation.attempt_id == AssessmentAttempt.id)
        .where(AssessmentAttempt.id == attempt_id, Evaluation.id == evaluation_id,
               Assessment.owner_id == owner_id, AssessmentAttempt.owner_id == owner_id,
               Evaluation.owner_id == owner_id))
    if context_id is None:
        raise ValidationError("Evaluation does not belong to this learner and attempt")
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    try:
        selected = [(UUID(str(detail["concept_id"])), UUID(str(detail["question_id"])))
                    for detail in details if detail.get("concept_id")]
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ValidationError("Invalid evidence reference") from exc
    if selected:
        concepts = set(db.scalars(select(Concept.id).where(
            Concept.id.in_({concept for concept, _ in selected}),
            Concept.owner_id == owner_id, Concept.context_id == context_id)))
        assessment_id = db.scalar(select(AssessmentAttempt.assessment_id).where(AssessmentAttempt.id == attempt_id))
        questions = dict(db.execute(select(AssessmentQuestion.id, AssessmentQuestion.concept_id).where(
            AssessmentQuestion.id.in_({question for _, question in selected}),
            AssessmentQuestion.assessment_id == assessment_id, AssessmentQuestion.owner_id == owner_id)).all())
        if any(concept not in concepts or questions.get(question) != concept for concept, question in selected):
            raise ValidationError("Evidence references do not belong to this assessment and subject")
    created: list[Evidence] = []
    for detail in details:
        concept_id = detail.get("concept_id")
        if not concept_id:
            continue
        evidence = Evidence(
            owner_id=owner_id,
            concept_id=UUID(str(concept_id)),
            evaluation_id=evaluation_id,
            signal=SIGNAL_CORRECT if detail["correct"] else SIGNAL_INCORRECT,
            provenance={
                "attempt_id": str(attempt_id),
                "evaluation_id": str(evaluation_id),
                "question_id": detail["question_id"],
                "correct_option": detail["correct_option"],
            },
        )
        db.add(evidence)
        created.append(evidence)
    return created


def list_context_evidence(
    db: Session, *, owner_id: UUID, context_id: UUID
) -> list[tuple[Evidence, Concept]]:
    return list(
        db.execute(
            select(Evidence, Concept)
            .join(Concept, Concept.id == Evidence.concept_id)
            .where(Evidence.owner_id == owner_id, Concept.owner_id == owner_id, Concept.context_id == context_id)
            .order_by(Evidence.created_at)
        )
    )


def invalidate_evidence(
    db: Session, *, owner_id: UUID, evidence_id: UUID, context_id: UUID
) -> Evidence:
    evidence = db.scalar(
        select(Evidence)
        .join(Evaluation, Evaluation.id == Evidence.evaluation_id)
        .join(AssessmentAttempt, AssessmentAttempt.id == Evaluation.attempt_id)
        .join(Assessment, Assessment.id == AssessmentAttempt.assessment_id)
        .where(
            Evidence.id == evidence_id,
            Evidence.owner_id == owner_id,
            Assessment.context_id == context_id,
            Assessment.owner_id == owner_id,
        )
    )
    if evidence is None:
        raise LookupError("Evidence not found")
    evidence.valid = False
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence
