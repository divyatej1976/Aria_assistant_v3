"""Generalized idempotency keys for consequential operations.

A client may attach an `Idempotency-Key` header to a consequential request.
The first request executes and its response is stored; retries with the same
key (owner + scope) return the stored response instead of re-executing, so
accidental double submission cannot run a destructive workflow twice.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import IdempotencyKey


def _now() -> datetime:
    return datetime.now(UTC)


def find(
    db: Session, *, owner_id: UUID, scope: str, key: str
) -> IdempotencyKey | None:
    return db.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.owner_id == owner_id,
            IdempotencyKey.scope == scope,
            IdempotencyKey.key == key,
        )
    )


def reserve(
    db: Session, *, owner_id: UUID, scope: str, key: str
) -> str:
    """Atomically reserve an idempotency key before executing the work.

    Returns ``"ok"`` when the caller may proceed, or ``"in_progress"`` when
    another request already holds a reservation for the same key (so the
    caller must not re-execute the work). A completed or expired row is taken
    over for a fresh execution. In-progress is inferred from
    ``response_json IS NULL``, so no schema change is required.
    """
    expires_at = _now() + timedelta(seconds=get_settings().aria_idempotency_ttl_seconds)
    for _attempt in range(3):
        entry = find(db, owner_id=owner_id, scope=scope, key=key)
        if entry is not None:
            if entry.response_json is None:
                return "in_progress"
            entry.response_status = None
            entry.response_json = None
            entry.expires_at = expires_at
            db.add(entry)
            try:
                db.commit()
                return "ok"
            except Exception:
                db.rollback()
                continue
        entry = IdempotencyKey(
            owner_id=owner_id,
            scope=scope,
            key=key,
            response_status=None,
            response_json=None,
            expires_at=expires_at,
        )
        db.add(entry)
        try:
            db.commit()
            return "ok"
        except IntegrityError:
            # A concurrent request inserted the same key first; re-check.
            db.rollback()
            continue
    return "in_progress"


def record(
    db: Session,
    *,
    owner_id: UUID,
    scope: str,
    key: str,
    status: int,
    response: dict,
) -> IdempotencyKey:
    expires_at = _now() + timedelta(seconds=get_settings().aria_idempotency_ttl_seconds)
    for _attempt in range(3):
        entry = find(db, owner_id=owner_id, scope=scope, key=key)
        if entry is None:
            entry = IdempotencyKey(
                owner_id=owner_id,
                scope=scope,
                key=key,
                response_status=status,
                response_json=response,
                expires_at=expires_at,
            )
        else:
            entry.response_status = status
            entry.response_json = response
            entry.expires_at = expires_at
        db.add(entry)
        try:
            db.commit()
            break
        except IntegrityError:
            # A concurrent request inserted the same (owner, scope, key) between
            # our find() and insert(); recover by replaying the find.
            db.rollback()
    else:
        raise RuntimeError("Could not store idempotency key after concurrent retries")
    db.refresh(entry)
    return entry


def replayable(entry: IdempotencyKey | None) -> bool:
    if entry is None or entry.response_json is None:
        return False
    expires_at = entry.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at is not None and expires_at < _now():
        return False
    return True
