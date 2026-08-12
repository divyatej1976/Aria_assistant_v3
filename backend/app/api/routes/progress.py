from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.progress import (
    ActivityResponse,
    BadgeResponse,
    ConsistencyResponse,
)
from app.security.dependencies import CurrentLearner
from app.services.progress import (
    activity_timeline,
    badges,
    consistency,
)

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/consistency", response_model=ConsistencyResponse)
def consistency_endpoint(learner: CurrentLearner, db: Db) -> ConsistencyResponse:
    return ConsistencyResponse(**consistency(db, owner_id=learner.id))


@router.get("/badges", response_model=list[BadgeResponse])
def badges_endpoint(learner: CurrentLearner, db: Db) -> list[BadgeResponse]:
    return [BadgeResponse(**item) for item in badges(db, owner_id=learner.id)]


@router.get("/activity", response_model=list[ActivityResponse])
def activity_endpoint(learner: CurrentLearner, db: Db) -> list[ActivityResponse]:
    return [
        ActivityResponse(
            id=str(item.id),
            activity_type=item.activity_type,
            occurred_on=item.occurred_on,
            created_at=item.created_at,
        )
        for item in activity_timeline(db, owner_id=learner.id)
    ]
