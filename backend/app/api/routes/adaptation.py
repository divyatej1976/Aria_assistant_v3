from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.db.models import Concept, LearningContext
from app.schemas.adaptation import (
    AdaptationDecisionResponse,
    ConceptResponse,
    ConceptStateResponse,
    CycleSummaryResponse,
    EvidenceResponse,
)
from app.schemas.memory import PrerequisiteAddRequest, PrerequisiteResponse
from app.security.dependencies import CurrentLearner
from app.services.adaptation import list_decisions, run_learner_loop
from app.services.concepts import list_concepts, sync_concepts
from app.services.evidence import invalidate_evidence, list_context_evidence
from app.services.learner_state import context_states_with_concepts
from app.services.memory import (
    add_prerequisite,
    list_prerequisites,
    remove_prerequisite,
)

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


def get_owned_concept(
    db: Session, *, context_id: UUID, concept_id: UUID, owner_id: UUID
) -> Concept:
    get_owned_context(db, context_id=context_id, owner_id=owner_id)
    concept = db.scalar(
        select(Concept).where(
            Concept.id == concept_id,
            Concept.owner_id == owner_id,
            Concept.context_id == context_id,
        )
    )
    if concept is None:
        raise HTTPException(status_code=404, detail="Concept not found")
    return concept


@router.get(
    "/{context_id}/concepts/{concept_id}/prerequisites",
    response_model=list[PrerequisiteResponse],
)
def prerequisites(
    context_id: UUID, concept_id: UUID, learner: CurrentLearner, db: Db
) -> list[PrerequisiteResponse]:
    get_owned_concept(db, context_id=context_id, concept_id=concept_id, owner_id=learner.id)
    return [
        PrerequisiteResponse(**item)
        for item in list_prerequisites(db, owner_id=learner.id, concept_id=concept_id)
    ]


@router.post(
    "/{context_id}/concepts/{concept_id}/prerequisites",
    response_model=list[PrerequisiteResponse],
    status_code=201,
)
def add_prerequisite_route(
    context_id: UUID,
    concept_id: UUID,
    request: PrerequisiteAddRequest,
    learner: CurrentLearner,
    db: Db,
) -> list[PrerequisiteResponse]:
    get_owned_concept(db, context_id=context_id, concept_id=concept_id, owner_id=learner.id)
    try:
        add_prerequisite(
            db,
            owner_id=learner.id,
            concept_id=concept_id,
            prerequisite_concept_id=request.prerequisite_concept_id,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [
        PrerequisiteResponse(**item)
        for item in list_prerequisites(db, owner_id=learner.id, concept_id=concept_id)
    ]


@router.delete(
    "/{context_id}/concepts/{concept_id}/prerequisites/{prerequisite_concept_id}"
)
def remove_prerequisite_route(
    context_id: UUID,
    concept_id: UUID,
    prerequisite_concept_id: UUID,
    learner: CurrentLearner,
    db: Db,
) -> dict[str, object]:
    get_owned_concept(db, context_id=context_id, concept_id=concept_id, owner_id=learner.id)
    if not remove_prerequisite(
        db,
        owner_id=learner.id,
        concept_id=concept_id,
        prerequisite_concept_id=prerequisite_concept_id,
    ):
        raise HTTPException(status_code=404, detail="Prerequisite link not found")
    return {"deleted": True}


@router.post(
    "/{context_id}/evidence/{evidence_id}/invalidate", response_model=CycleSummaryResponse
)
def invalidate(
    context_id: UUID, evidence_id: UUID, learner: CurrentLearner, db: Db
) -> CycleSummaryResponse:
    get_owned_context(db, context_id=context_id, owner_id=learner.id)
    try:
        invalidate_evidence(db, owner_id=learner.id, evidence_id=evidence_id, context_id=context_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Evidence not found") from exc
    run_learner_loop(db, owner_id=learner.id, context_id=context_id)
    return summary_response(db, owner_id=learner.id, context_id=context_id)
