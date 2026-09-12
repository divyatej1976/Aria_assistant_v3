from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.schemas.push import (
    PushSubscriptionRequest,
    PushSubscriptionResponse,
    PushUnsubscribeRequest,
)
from app.security.dependencies import CurrentLearner
from app.services.push import list_subscriptions, subscribe, unsubscribe

router = APIRouter(prefix="/api/v1/push", tags=["push"])
Db = Annotated[Session, Depends(get_db)]


def response_for(subscription) -> PushSubscriptionResponse:
    return PushSubscriptionResponse(
        id=str(subscription.id),
        endpoint=subscription.endpoint,
        created_at=subscription.created_at.isoformat(),
    )


@router.post(
    "/subscribe",
    response_model=PushSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def subscribe_endpoint(
    request: PushSubscriptionRequest, learner: CurrentLearner, db: Db
) -> PushSubscriptionResponse:
    try:
        subscription = subscribe(
            db,
            owner_id=learner.id,
            endpoint=request.endpoint,
            p256dh=request.p256dh,
            auth=request.auth,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return response_for(subscription)


@router.post("/unsubscribe")
def unsubscribe_endpoint(
    request: PushUnsubscribeRequest, learner: CurrentLearner, db: Db
) -> dict[str, bool]:
    removed = unsubscribe(db, owner_id=learner.id, endpoint=request.endpoint)
    return {"unsubscribed": removed}


@router.get("/subscriptions", response_model=list[PushSubscriptionResponse])
def subscriptions(learner: CurrentLearner, db: Db) -> list[PushSubscriptionResponse]:
    return [response_for(item) for item in list_subscriptions(db, owner_id=learner.id)]
