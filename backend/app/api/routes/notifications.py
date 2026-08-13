from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.planner import NotificationResponse
from app.security.dependencies import CurrentLearner
from app.services.notifications import (
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])
Db = Annotated[Session, Depends(get_db)]


def notification_response(notification) -> NotificationResponse:
    return NotificationResponse(
        id=str(notification.id),
        ntype=notification.ntype,
        title=notification.title,
        body=notification.body,
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


@router.get("", response_model=list[NotificationResponse])
def notifications(learner: CurrentLearner, db: Db) -> list[NotificationResponse]:
    return [
        notification_response(item)
        for item in list_notifications(db, owner_id=learner.id)
    ]


@router.get("/unread-count")
def unread_count(learner: CurrentLearner, db: Db) -> dict[str, int]:
    items = list_notifications(db, owner_id=learner.id)
    return {"unread": sum(1 for item in items if item.read_at is None)}


@router.post("/read-all")
def read_all(learner: CurrentLearner, db: Db) -> dict[str, int]:
    return {"marked": mark_all_notifications_read(db, owner_id=learner.id)}


@router.post("/{notification_id}/read")
def read(
    notification_id: UUID, learner: CurrentLearner, db: Db
) -> dict[str, object]:
    notification = mark_notification_read(
        db, owner_id=learner.id, notification_id=notification_id
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"read": True}
