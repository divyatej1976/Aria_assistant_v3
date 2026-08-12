from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AdaptationDecision, LearnerConceptState
from app.services.learner_state import (
    STATE_DEVELOPING,
    STATE_NEEDS_REVIEW,
    context_states_with_concepts,
    recompute_learner_states,
)
from app.services.memory import weak_prerequisite_names

DECISION_FOCUS_STUDY = "FOCUS_STUDY"
DECISION_RETEST_TARGETED = "RETEST_TARGETED"
DECISION_NO_ACTION = "NO_ACTION"


def _decision_for_state(
    state: LearnerConceptState, concept_name: str
) -> tuple[str, str] | None:
    if state.state == STATE_NEEDS_REVIEW:
        return (
            DECISION_FOCUS_STUDY,
            f"Focus study on '{concept_name}': recent incorrect answers suggest it needs review.",
        )
    if state.state == STATE_DEVELOPING:
        return (
            DECISION_FOCUS_STUDY,
            f"Focus study on '{concept_name}': understanding is still developing.",
        )
    return None


def generate_adaptation_decisions(
    db: Session, *, owner_id: UUID, context_id: UUID
) -> list[AdaptationDecision]:
    db.execute(
        delete(AdaptationDecision).where(
            AdaptationDecision.owner_id == owner_id,
            AdaptationDecision.context_id == context_id,
            AdaptationDecision.status == "READY",
        )
    )
    pairs = context_states_with_concepts(db, owner_id=owner_id, context_id=context_id)
    decisions: list[AdaptationDecision] = []
    weak_names: list[str] = []
    for learner_state, concept in pairs:
        decision = _decision_for_state(learner_state, concept.name)
        if decision is not None:
            decision_type, reason = decision
            if learner_state.state == STATE_NEEDS_REVIEW:
                weak_prerequisites = weak_prerequisite_names(
                    db, owner_id=owner_id, concept_id=concept.id
                )
                if weak_prerequisites:
                    names = ", ".join(weak_prerequisites)
                    reason += (
                        f" A weak prerequisite ({names}) may be the cause, so it may help "
                        "to review that foundation first."
                    )
            decisions.append(
                AdaptationDecision(
                    owner_id=owner_id,
                    context_id=context_id,
                    concept_id=concept.id,
                    decision_type=decision_type,
                    reason=reason,
                )
            )
            weak_names.append(concept.name)
    if weak_names:
        decisions.append(
            AdaptationDecision(
                owner_id=owner_id,
                context_id=context_id,
                concept_id=None,
                decision_type=DECISION_RETEST_TARGETED,
                reason=f"Reassess the weak concepts: {', '.join(weak_names)}.",
            )
        )
    for decision in decisions:
        db.add(decision)
    db.commit()
    return decisions


def run_learner_loop(
    db: Session, *, owner_id: UUID, context_id: UUID
) -> tuple[list[LearnerConceptState], list[AdaptationDecision]]:
    states = recompute_learner_states(db, owner_id=owner_id, context_id=context_id)
    decisions = generate_adaptation_decisions(db, owner_id=owner_id, context_id=context_id)
    return states, decisions


def list_decisions(
    db: Session, *, owner_id: UUID, context_id: UUID
) -> list[AdaptationDecision]:
    return list(
        db.scalars(
            select(AdaptationDecision)
            .where(
                AdaptationDecision.owner_id == owner_id,
                AdaptationDecision.context_id == context_id,
                AdaptationDecision.status == "READY",
            )
            .order_by(AdaptationDecision.created_at)
        )
    )
