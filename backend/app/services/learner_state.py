from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Concept, Evidence, LearnerConceptState
from app.services.concepts import list_concepts
from app.services.contexts import get_owned_context
from app.services.evidence import SIGNAL_CORRECT, SIGNAL_INCORRECT

STATE_UNTESTED = "UNTESTED"
STATE_DEVELOPING = "DEVELOPING"
STATE_NEEDS_REVIEW = "NEEDS_REVIEW"
STATE_SUPPORTED = "SUPPORTED"

SUPPORTED_CONSECUTIVE = 2


def compute_state(signals: list[str]) -> tuple[str, int]:
    if not signals:
        return STATE_UNTESTED, 0
    consecutive_correct = 0
    for signal in reversed(signals):
        if signal == SIGNAL_CORRECT:
            consecutive_correct += 1
        else:
            break
    correct = sum(1 for signal in signals if signal == SIGNAL_CORRECT)
    incorrect = len(signals) - correct
    confidence = max(0, min(100, 10 + correct * 20 - incorrect * 30))
    if signals[-1] == SIGNAL_INCORRECT:
        state = STATE_NEEDS_REVIEW
    elif consecutive_correct >= SUPPORTED_CONSECUTIVE:
        state = STATE_SUPPORTED
    else:
        state = STATE_DEVELOPING
    return state, confidence


def reason_for(state: str, correct: int, incorrect: int) -> str:
    if state == STATE_NEEDS_REVIEW:
        return (
            f"Recent incorrect answers suggest this needs review "
            f"({correct} correct, {incorrect} incorrect)."
        )
    if state == STATE_SUPPORTED:
        return (
            f"Consistent correct answers support this concept "
            f"({correct} correct, {incorrect} incorrect)."
        )
    if state == STATE_DEVELOPING:
        return (
            f"Early evidence shows understanding is developing "
            f"({correct} correct, {incorrect} incorrect)."
        )
    return "No evidence yet."


def recompute_learner_states(
    db: Session, *, owner_id: UUID, context_id: UUID
) -> list[LearnerConceptState]:
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    concepts = list_concepts(db, owner_id=owner_id, context_id=context_id)
    states: list[LearnerConceptState] = []
    evidence_by_concept: dict[UUID, list[Evidence]] = {}
    for item in db.scalars(
        select(Evidence).join(Concept, Concept.id == Evidence.concept_id).where(
            Evidence.owner_id == owner_id, Concept.owner_id == owner_id,
            Concept.context_id == context_id, Evidence.valid.is_(True),
        ).order_by(Evidence.created_at)
    ):
        evidence_by_concept.setdefault(item.concept_id, []).append(item)
    existing_states = {item.concept_id: item for item in db.scalars(
        select(LearnerConceptState).join(Concept, Concept.id == LearnerConceptState.concept_id).where(
            LearnerConceptState.owner_id == owner_id, Concept.owner_id == owner_id,
            Concept.context_id == context_id,
        )
    )}
    for concept in concepts:
        evidence = evidence_by_concept.get(concept.id, [])
        signals = [item.signal for item in evidence]
        state, confidence = compute_state(signals)
        correct = sum(1 for item in evidence if item.signal == SIGNAL_CORRECT)
        incorrect = len(evidence) - correct
        learner_state = existing_states.get(concept.id)
        if learner_state is None:
            learner_state = LearnerConceptState(
                owner_id=owner_id,
                concept_id=concept.id,
                state=state,
                confidence=confidence,
                reason=reason_for(state, correct, incorrect),
                supporting_evidence=[str(item.id) for item in evidence],
            )
            db.add(learner_state)
        else:
            learner_state.state = state
            learner_state.confidence = confidence
            learner_state.reason = reason_for(state, correct, incorrect)
            learner_state.supporting_evidence = [str(item.id) for item in evidence]
            db.add(learner_state)
        states.append(learner_state)
    db.commit()
    return states


def context_states_with_concepts(
    db: Session, *, owner_id: UUID, context_id: UUID
) -> list[tuple[LearnerConceptState, Concept]]:
    return list(
        db.execute(
            select(LearnerConceptState, Concept)
            .join(Concept, Concept.id == LearnerConceptState.concept_id)
            .where(
                LearnerConceptState.owner_id == owner_id,
                Concept.context_id == context_id,
                Concept.owner_id == owner_id,
            )
            .order_by(Concept.name)
        )
    )
