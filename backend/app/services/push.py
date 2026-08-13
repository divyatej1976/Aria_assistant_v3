"""Web push notifications using VAPID; logs delivery when not configured."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import PushSubscription

logger = logging.getLogger(__name__)


class WebPushProvider:
    def __init__(self, *, public_key: str, private_key: str, subject: str) -> None:
        self.public_key = public_key
        self.private_key = private_key
        self.subject = subject

    def send(self, *, subscription: PushSubscription, title: str, body: str) -> str:
        import json

        from pywebpush import WebPushException, webpush

        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=self.private_key,
                vapid_claims={"sub": self.subject},
            )
            return "sent"
        except WebPushException as exc:
            if exc.response is not None and exc.response.status_code in (404, 410):
                logger.info("web push subscription gone: %s", exc.response.status_code)
                return "gone"
            logger.warning("web push failed: %s", exc)
            return "failed"


class LogPushProvider:
    def send(self, *, subscription: PushSubscription, title: str, body: str) -> str:
        endpoint = subscription.endpoint[:40]
        logger.info("push to=%s title=%s body=%s", endpoint, title, body)
        return "logged"


def get_push_provider():
    settings = get_settings()
    if settings.aria_vapid_public_key and settings.aria_vapid_private_key:
        return WebPushProvider(
            public_key=settings.aria_vapid_public_key,
            private_key=settings.aria_vapid_private_key,
            subject=settings.aria_vapid_subject,
        )
    return LogPushProvider()


def subscribe(
    db: Session, *, owner_id: UUID, endpoint: str, p256dh: str, auth: str
) -> PushSubscription:
    subscription = db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    if subscription is None:
        subscription = PushSubscription(
            owner_id=owner_id, endpoint=endpoint, p256dh=p256dh, auth=auth
        )
    else:
        subscription.owner_id = owner_id
        subscription.p256dh = p256dh
        subscription.auth = auth
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def unsubscribe(db: Session, *, owner_id: UUID, endpoint: str) -> bool:
    subscription = db.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.owner_id == owner_id,
        )
    )
    if subscription is None:
        return False
    db.delete(subscription)
    db.commit()
    return True


def list_subscriptions(db: Session, *, owner_id: UUID) -> list[PushSubscription]:
    return list(
        db.scalars(
            select(PushSubscription).where(PushSubscription.owner_id == owner_id)
        )
    )


def send_push(
    db: Session, *, owner_id: UUID, title: str, body: str, provider=None
) -> dict[str, int]:
    provider = provider or get_push_provider()
    counts = {"sent": 0, "logged": 0, "failed": 0, "removed": 0}
    for subscription in list_subscriptions(db, owner_id=owner_id):
        status = provider.send(subscription=subscription, title=title, body=body)
        if status == "sent":
            counts["sent"] += 1
        elif status == "logged":
            counts["logged"] += 1
        elif status == "gone":
            db.delete(subscription)
            counts["removed"] += 1
        else:
            counts["failed"] += 1
    db.commit()
    return counts
