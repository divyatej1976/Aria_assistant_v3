from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.schemas.roadmap import (
    RoadmapCreateRequest,
    RoadmapResponse,
    RoadmapSummaryResponse,
)
from app.security.dependencies import CurrentLearner
from app.security.rate_limit import rate_limited
from app.services.roadmap import (
    create_roadmap,
    delete_roadmap,
    get_roadmap,
    list_roadmaps,
)

router = APIRouter(prefix="/api/v1/roadmaps", tags=["roadmaps"])
Db = Annotated[Session, Depends(get_db)]


def _ai_rate_limit():
    settings = get_settings()
    return rate_limited(settings.aria_rate_limit_requests, settings.aria_rate_limit_window_seconds)


@router.post("", response_model=RoadmapResponse, status_code=201, dependencies=[Depends(_ai_rate_limit())])
async def create_roadmap_endpoint(
    request: RoadmapCreateRequest, learner: CurrentLearner, db: Db
) -> RoadmapResponse:
    if not request.goal.strip():
        raise HTTPException(status_code=400, detail="Learning goal is required")

    roadmap = await create_roadmap(
        db,
        owner_id=learner.id,
        goal=request.goal,
        level=request.level,
        target_date=request.target_date,
        context_id=request.context_id,
        hours_per_week=request.hours_per_week,
    )
    return get_roadmap(db, owner_id=learner.id, roadmap_id=roadmap.id)


@router.get("", response_model=list[RoadmapSummaryResponse])
def list_roadmaps_endpoint(
    learner: CurrentLearner,
    db: Db,
    context_id: UUID | None = Query(None),
) -> list[RoadmapSummaryResponse]:
    return list_roadmaps(db, owner_id=learner.id, context_id=context_id)


@router.get("/{roadmap_id}", response_model=RoadmapResponse)
def get_roadmap_endpoint(
    roadmap_id: UUID, learner: CurrentLearner, db: Db
) -> RoadmapResponse:
    try:
        return get_roadmap(db, owner_id=learner.id, roadmap_id=roadmap_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{roadmap_id}")
def delete_roadmap_endpoint(
    roadmap_id: UUID, learner: CurrentLearner, db: Db
) -> dict[str, bool]:
    if not delete_roadmap(db, owner_id=learner.id, roadmap_id=roadmap_id):
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return {"deleted": True}
