from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models import LearningContext
from app.schemas.adaptation import (
    AdaptationDecisionResponse,
    ConceptResponse,
    ConceptStateResponse,
    CycleSummaryResponse,
    EvidenceResponse,
)
from app.security.dependencies import CurrentLearner
from app.services.adaptation import list_decisions, run_learner_loop
from app.services.concepts import list_concepts, sync_concepts
from app.services.evidence import invalidate_evidence, list_context_evidence
from app.services.learner_state import context_states_with_concepts

router = APIRouter(prefix="/api/v1/contexts", tags=["adaptation"])
Db = Annotated[Session, Depends(get_db)]


def get_owned_context(db: Session, *, context_id: UUID, owner_id: UUID) -> LearningContext:
    context = db.scalar(
        select(LearningContext).where(
            LearningContext.id == context_id, LearningContext.owner_id == owner_id
        )
    )
    if context is None:
        raise HTTPException(status_code=404, detail="Learning context not found")
    return context


def summary_response(db: Session, *, owner_id: UUID, context_id: UUID) -> CycleSummaryResponse:
    state_pairs = context_states_with_concepts(db, owner_id=owner_id, context_id=context_id)
    decisions = list_decisions(db, owner_id=owner_id, context_id=context_id)
    return CycleSummaryResponse(
        states=[
            ConceptStateResponse(
                concept_id=str(concept.id),
                concept_name=concept.name,
                state=learner_state.state,
                confidence=learner_state.confidence,
                reason=learner_state.reason,
            )
            for learner_state, concept in state_pairs
        ],
        decisions=[
            AdaptationDecisionResponse(
                concept_id=str(decision.concept_id) if decision.concept_id else None,
                decision_type=decision.decision_type,
                reason=decision.reason,
            )
            for decision in decisions
        ],
    )


@router.post("/{context_id}/concepts/sync", response_model=list[ConceptResponse])
async def sync(
    context_id: UUID, learner: CurrentLearner, db: Db
) -> list[ConceptResponse]:
    get_owned_context(db, context_id=context_id, owner_id=learner.id)
    concepts = await sync_concepts(db, owner_id=learner.id, context_id=context_id)
    return [ConceptResponse(id=str(concept.id), name=concept.name) for concept in concepts]


@router.get("/{context_id}/concepts", response_model=list[ConceptResponse])
def concepts(context_id: UUID, learner: CurrentLearner, db: Db) -> list[ConceptResponse]:
    get_owned_context(db, context_id=context_id, owner_id=learner.id)
    items = list_concepts(db, owner_id=learner.id, context_id=context_id)
    return [ConceptResponse(id=str(concept.id), name=concept.name) for concept in items]


@router.get("/{context_id}/adaptation", response_model=CycleSummaryResponse)
def summary(context_id: UUID, learner: CurrentLearner, db: Db) -> CycleSummaryResponse:
    get_owned_context(db, context_id=context_id, owner_id=learner.id)
    return summary_response(db, owner_id=learner.id, context_id=context_id)


@router.get("/{context_id}/evidence", response_model=list[EvidenceResponse])
def evidence(context_id: UUID, learner: CurrentLearner, db: Db) -> list[EvidenceResponse]:
    get_owned_context(db, context_id=context_id, owner_id=learner.id)
    rows = list_context_evidence(db, owner_id=learner.id, context_id=context_id)
    return [
        EvidenceResponse(
            id=str(item.id),
            concept_id=str(concept.id),
            concept_name=concept.name,
            signal=item.signal,
            valid=item.valid,
            created_at=item.created_at,
        )
        for item, concept in rows
    ]


@router.post(
    "/{context_id}/evidence/{evidence_id}/invalidate", response_model=CycleSummaryResponse
)
def invalidate(
    context_id: UUID, evidence_id: UUID, learner: CurrentLearner, db: Db
) -> CycleSummaryResponse:
    get_owned_context(db, context_id=context_id, owner_id=learner.id)
    try:
        invalidate_evidence(db, owner_id=learner.id, evidence_id=evidence_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Evidence not found") from exc
    run_learner_loop(db, owner_id=learner.id, context_id=context_id)
    return summary_response(db, owner_id=learner.id, context_id=context_id)
