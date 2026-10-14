"""Generalized idempotency keys for consequential operations.

A client may attach an `Idempotency-Key` header to a consequential request.
The first request executes and its response is stored; retries with the same
key (owner + scope) return the stored response instead of re-executing, so
accidental double submission cannot run a destructive workflow twice.
"""

import hashlib
import json
import logging
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import Event, Thread
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import IdempotencyKey


class ClaimLost(RuntimeError):
    """The workflow no longer owns its idempotency reservation."""


@contextmanager
def keep_claim_alive(db: Session, *, owner_id: UUID, scope: str, key: str, claim_id: UUID):
    """Renew in an independent session, and fence completion on renewal loss."""
    stop, lost = Event(), Event()
    bind = db.get_bind()
    interval = max(0.05, min(30, get_settings().aria_idempotency_ttl_seconds / 3))

    def heartbeat():
        while not stop.wait(interval):
            try:
                with Session(bind) as heartbeat_db:
                    if not renew(heartbeat_db, owner_id=owner_id, scope=scope, key=key, claim_id=claim_id):
                        lost.set()
                        return
            except Exception as exc:
                logging.getLogger(__name__).warning("workflow renewal failed error_type=%s", type(exc).__name__)
                lost.set()
                return

    thread = Thread(target=heartbeat, daemon=True, name="aria-workflow-lease")
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=5)
    if lost.is_set() or thread.is_alive():
        raise ClaimLost("Workflow reservation renewal failed")


def _now() -> datetime:
    return datetime.now(UTC)


def fingerprint(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


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
    db: Session, *, owner_id: UUID, scope: str, key: str, request_fingerprint: str | None = None,
    claim_id: UUID | None = None,
) -> str:
    """Claim a missing or expired key; never overwrite a live completed result.

    Returns ok, in_progress, or completed. Expired-row takeover uses a
    conditional update so only one caller observing that expiry may claim it.
    The unreferenced internal row ID is the claim identity and rotates on
    takeover; callers pass it to record/release to fence older executions.
    """
    settings = get_settings()
    ttl_seconds = settings.aria_idempotency_ttl_seconds
    expires_at = _now() + timedelta(seconds=ttl_seconds)
    for _attempt in range(3):
        entry = find(db, owner_id=owner_id, scope=scope, key=key)
        if entry is not None:
            entry_expires = entry.expires_at
            aware_expiry = entry_expires
            if aware_expiry is not None and aware_expiry.tzinfo is None:
                aware_expiry = aware_expiry.replace(tzinfo=UTC)
            if aware_expiry is None or aware_expiry >= _now():
                if request_fingerprint is not None and entry.request_fingerprint != request_fingerprint:
                    return "payload_conflict"
                return "completed" if entry.response_json is not None else "in_progress"
            if entry.response_status is None and entry.workflow_id is not None:
                if request_fingerprint is not None and entry.request_fingerprint != request_fingerprint:
                    return "payload_conflict"
                return "recovery_required"
            claimed = db.execute(update(IdempotencyKey).where(
                IdempotencyKey.id == entry.id,
                IdempotencyKey.owner_id == owner_id,
                IdempotencyKey.expires_at == entry_expires,
            ).values(id=claim_id or uuid4(), response_status=None, response_json=None, workflow_id=None,
                     expires_at=expires_at, request_fingerprint=request_fingerprint),
                execution_options={"synchronize_session": False}).rowcount
            db.commit()
            db.expire_all()
            if claimed:
                return "ok"
            continue
        # Housekeeping on the rare insert path: drop rows long past their TTL
        # so the table cannot grow without bound.
        purge_before = _now() - timedelta(seconds=ttl_seconds)
        db.query(IdempotencyKey).filter(
            IdempotencyKey.expires_at < purge_before,
            (IdempotencyKey.workflow_id.is_(None) | IdempotencyKey.response_status.is_not(None)),
        ).delete(
            synchronize_session=False
        )
        entry = IdempotencyKey(
            id=claim_id or uuid4(),
            owner_id=owner_id,
            scope=scope,
            key=key,
            request_fingerprint=request_fingerprint,
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


def release(
    db: Session, *, owner_id: UUID, scope: str, key: str, claim_id: UUID | None = None
) -> None:
    """Drop a live reservation when execution failed before recording a
    response, so the key is immediately retryable instead of stuck at 409."""
    if claim_id is not None:
        db.execute(delete(IdempotencyKey).where(
            IdempotencyKey.id == claim_id, IdempotencyKey.owner_id == owner_id,
            IdempotencyKey.scope == scope, IdempotencyKey.key == key,
            IdempotencyKey.response_status.is_(None),
        ), execution_options={"synchronize_session": False})
        db.commit()
        db.expire_all()
        return
    entry = find(db, owner_id=owner_id, scope=scope, key=key)
    if entry is not None and entry.response_json is None:
        db.execute(delete(IdempotencyKey).where(
            IdempotencyKey.id == entry.id, IdempotencyKey.owner_id == owner_id,
            IdempotencyKey.response_status.is_(None),
            IdempotencyKey.expires_at == entry.expires_at,
        ), execution_options={"synchronize_session": False})
        db.commit()
        db.expire_all()


def renew(
    db: Session, *, owner_id: UUID, scope: str, key: str, claim_id: UUID,
) -> bool:
    """Extend only a live unfinished claim; never revive lost ownership.

    Use a dedicated session: renewal commits its own transaction and must not
    accidentally commit a workflow handler's pending domain writes.
    """
    now = _now()
    changed = db.execute(update(IdempotencyKey).where(
        IdempotencyKey.id == claim_id, IdempotencyKey.owner_id == owner_id,
        IdempotencyKey.scope == scope, IdempotencyKey.key == key,
        IdempotencyKey.response_status.is_(None), IdempotencyKey.expires_at > now,
    ).values(expires_at=now + timedelta(seconds=get_settings().aria_idempotency_ttl_seconds)),
        execution_options={"synchronize_session": False}).rowcount
    db.commit()
    db.expire_all()
    return bool(changed)


def purge_expired(db: Session, *, now: datetime | None = None) -> int:
    """Delete every key whose TTL has passed. Standalone sweeper.

    Removal criteria match the read semantics exactly:
    - completed rows with expired TTL can no longer be replayed
      (``replayable`` already ignores them);
    - expired reservations without a bound workflow can be reclaimed.
      Unresolved workflow checkpoints survive so potentially committed domain
      work is not repeated after a process crash.
    Live reservations (expires_at in the future) are never touched. Returns
    the number of rows removed. The scheduler runs this under the usual
    advisory lock so concurrent replicas never sweep simultaneously.
    """
    reference = now or _now()
    result = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.expires_at < reference,
            (IdempotencyKey.workflow_id.is_(None) | IdempotencyKey.response_status.is_not(None)),
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return result


def record(
    db: Session,
    *,
    owner_id: UUID,
    scope: str,
    key: str,
    status: int,
    response: dict,
    claim_id: UUID | None = None,
) -> IdempotencyKey:
    expires_at = _now() + timedelta(seconds=get_settings().aria_idempotency_ttl_seconds)
    if claim_id is not None:
        changed = db.execute(update(IdempotencyKey).where(
            IdempotencyKey.id == claim_id, IdempotencyKey.owner_id == owner_id,
            IdempotencyKey.scope == scope, IdempotencyKey.key == key,
            IdempotencyKey.response_status.is_(None), IdempotencyKey.expires_at >= _now(),
        ).values(response_status=status, response_json=response, expires_at=expires_at),
            execution_options={"synchronize_session": False}).rowcount
        db.commit()
        db.expire_all()
        if not changed:
            raise ClaimLost("Idempotency reservation expired or was replaced")
        return find(db, owner_id=owner_id, scope=scope, key=key)
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


def stage_response(
    db: Session, *, owner_id: UUID, scope: str, key: str, claim_id: UUID, response: dict,
) -> None:
    """Fence a response in the caller's domain transaction, without committing."""
    changed = db.execute(update(IdempotencyKey).where(
        IdempotencyKey.id == claim_id, IdempotencyKey.owner_id == owner_id,
        IdempotencyKey.scope == scope, IdempotencyKey.key == key,
        IdempotencyKey.response_status.is_(None), IdempotencyKey.expires_at >= _now(),
    ).values(response_status=200, response_json=response,
             expires_at=_now() + timedelta(seconds=get_settings().aria_idempotency_ttl_seconds)),
        execution_options={"synchronize_session": False}).rowcount
    if changed != 1:
        db.rollback()
        raise ClaimLost("The reply request no longer owns its reservation")


def bind_workflow(
    db: Session, *, owner_id: UUID, scope: str, key: str, claim_id: UUID, workflow_id: UUID,
) -> None:
    """Bind before domain work, in the workflow creation transaction.

    An expired unresolved checkpoint must survive sweeping and cannot be
    reclaimed for a second execution with an uncertain committed outcome.
    """
    changed = db.execute(update(IdempotencyKey).where(
        IdempotencyKey.id == claim_id, IdempotencyKey.owner_id == owner_id,
        IdempotencyKey.scope == scope, IdempotencyKey.key == key,
        IdempotencyKey.response_status.is_(None), IdempotencyKey.expires_at > _now(),
        IdempotencyKey.workflow_id.is_(None),
    ).values(workflow_id=workflow_id)).rowcount
    if changed != 1:
        db.rollback()
        raise ClaimLost("Workflow reservation lost before execution")
