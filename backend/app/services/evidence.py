from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Assessment, AssessmentAttempt, Concept, Evaluation, Evidence

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
            .where(Evidence.owner_id == owner_id, Concept.context_id == context_id)
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
