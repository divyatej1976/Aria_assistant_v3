"""Owned action records. New flows execute in LangGraph, never the legacy engine."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import Event, Thread
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.models import AudioArtifact, AuditLog, BrainAction, ConversationMessage, Resource
from app.schemas.brain import ActionResponse


class ActionMissing(ValidationError):
    pass


class ActionBusy(ValidationError):
    pass


def owned_action(db, *, owner_id, action_id):
    action = db.scalar(
        select(BrainAction)
        .join(ConversationMessage, ConversationMessage.id == BrainAction.id)
        .where(
            BrainAction.id == action_id,
            BrainAction.owner_id == owner_id,
            ConversationMessage.owner_id == owner_id,
        )
        .execution_options(populate_existing=True)
    )
    if action is None:
        raise ActionMissing("Action not found")
    return action


def view(action) -> ActionResponse:
    return ActionResponse(
        id=str(action.id),
        capability=action.capability,
        status=action.status,
        artifact_id=str(action.artifact_id) if action.artifact_id else None,
        error_code=action.error_code,
        auto_run=get_settings().aria_brain_routing,
        message={
            "proposed": "Create an audio episode from this conversation.",
            "running": "Creating your conversation audio…",
            "done": "Your conversation audio is ready.",
            "failed": "Audio could not be created. Your saved source is kept for retry.",
            "cancelled": "Audio creation was cancelled before execution.",
        }[action.status],
    )


def audit(db, action, outcome, error_code=None):
    # Allowlisted values, not arbitrary text or model-provided params/summaries.
    db.add(
        AuditLog(
            owner_id=action.owner_id,
            agent="langgraph",
            action=outcome,
            detail={
                "capability": "audio.from_session",
                "action_id": str(action.id),
                "session_id": str(action.session_id),
                "source_id": str(action.source_id),
                "outcome": outcome,
                "error_code": error_code,
            },
        )
    )


async def prepare_audio_action(db, *, owner_id, session, action_id) -> BrainAction:
    from app.services.audio import MAX_AUDIO_CHARS, session_audio_source
    from app.services.brain.snapshot import build_snapshot
    from app.services.resource_ingestion import create_text_resource

    build_snapshot(db, owner_id=owner_id, context_id=session.context_id)
    source_id = uuid5(NAMESPACE_URL, f"aria:audio-action-source:{owner_id}:{action_id}")
    source = db.get(Resource, source_id)
    if source is None:
        _, title, text, cutoff = session_audio_source(db, owner_id=owner_id, session_id=session.id)
        if len(text) > MAX_AUDIO_CHARS:
            raise ValidationError("This conversation is too long. Paste a shorter section in Audio studio.")
        # Immutable source is committed by ingestion before the reply. A retry
        # uses this deterministic ID even if messages were added or deleted.
        source = await create_text_resource(
            db, owner_id=owner_id, context_id=session.context_id, title=title, text=text, resource_id=source_id
        )
    else:
        if source.owner_id != owner_id or source.context_id != session.context_id:
            raise ActionMissing("Source not found")
        cutoff = 0  # source reference, rather than live messages, owns replay
    action = BrainAction(
        id=action_id,
        owner_id=owner_id,
        context_id=session.context_id,
        session_id=session.id,
        capability="audio.from_session",
        source_id=source.id,
        through_position=cutoff,
        status="proposed",
    )
    return action


def get_status(db, *, owner_id, action_id) -> ActionResponse:
    action = owned_action(db, owner_id=owner_id, action_id=action_id)
    if action.status in ("done", "cancelled", "proposed"):
        return view(action)
    artifact = db.scalar(
        select(AudioArtifact)
        .where(
            AudioArtifact.owner_id == owner_id,
            AudioArtifact.source_id == action.source_id,
            AudioArtifact.source_type == "RESOURCE",
        )
        .order_by(AudioArtifact.created_at, AudioArtifact.id)
    )
    # Recovery of a lost HTTP response or a crash after publishing audio does
    # not call the provider again. Source identity is the durable checkpoint.
    if artifact is not None and artifact.status == "READY":
        changed = db.execute(
            update(BrainAction)
            .where(
                BrainAction.id == action.id,
                BrainAction.owner_id == owner_id,
                BrainAction.status.in_(["running", "failed"]),
            )
            .values(status="done", artifact_id=artifact.id, error_code=None, lease_until=None, claim_id=None)
        ).rowcount
        if changed:
            audit(db, action, "done")
        db.commit()
        db.refresh(action)
    elif action.status == "running":

        def alive(lease):
            if lease is None:
                return False
            return (lease if lease.tzinfo else lease.replace(tzinfo=UTC)) > datetime.now(UTC)

        if not alive(action.lease_until) and not (
            artifact and artifact.status == "PROCESSING" and alive(artifact.lease_until)
        ):
            changed = db.execute(
                update(BrainAction)
                .where(
                    BrainAction.id == action.id,
                    BrainAction.owner_id == owner_id,
                    BrainAction.status == "running",
                    BrainAction.claim_id == action.claim_id,
                    BrainAction.lease_until == action.lease_until,
                )
                .values(status="failed", error_code="worker_interrupted", claim_id=None, lease_until=None)
            ).rowcount
            if changed:
                audit(db, action, "failed", "worker_interrupted")
            db.commit()
            db.refresh(action)
    return view(action)


def cancel(db, *, owner_id, action_id) -> ActionResponse:
    action = owned_action(db, owner_id=owner_id, action_id=action_id)
    changed = db.execute(
        update(BrainAction)
        .where(
            BrainAction.id == action.id,
            BrainAction.owner_id == owner_id,
            BrainAction.status.in_(["proposed", "failed"]),
        )
        .values(status="cancelled", error_code=None, lease_until=None, claim_id=None)
    ).rowcount
    if not changed and action.status != "cancelled":
        db.rollback()
        raise ActionBusy("This action has already started or finished and cannot be cancelled.")
    if changed:
        audit(db, action, "cancelled")
        db.commit()
    db.refresh(action)
    return view(action)


@contextmanager
def renew_action(db, action_id, token):
    stop = Event()
    bind = db.get_bind()

    def heartbeat():
        while not stop.wait(30):
            try:
                with Session(bind) as session:
                    changed = session.execute(
                        update(BrainAction)
                        .where(
                            BrainAction.id == action_id, BrainAction.claim_id == token, BrainAction.status == "running"
                        )
                        .values(lease_until=datetime.now(UTC) + timedelta(minutes=5))
                    ).rowcount
                    session.commit()
                    if not changed:
                        return
            except Exception:
                return  # completion is fenced by the same claim token

    thread = Thread(target=heartbeat, daemon=True, name="aria-graph-lease")
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=5)


async def run(db, *, owner_id, action_id) -> ActionResponse:
    if not get_settings().aria_brain_routing:
        raise ValidationError("Chat actions are currently disabled")
    current = get_status(db, owner_id=owner_id, action_id=action_id)
    if current.status in ("done", "cancelled"):
        return current
    now, token = datetime.now(UTC), uuid4()
    changed = db.execute(
        update(BrainAction)
        .where(
            BrainAction.id == action_id,
            BrainAction.owner_id == owner_id,
            or_(
                BrainAction.status.in_(["proposed", "failed"]),
                (BrainAction.status == "running")
                & or_(BrainAction.lease_until <= now, BrainAction.lease_until.is_(None)),
            ),
        )
        .values(
            status="running",
            claim_id=token,
            lease_until=now + timedelta(minutes=5),
            attempts=BrainAction.attempts + 1,
            error_code=None,
        )
    ).rowcount
    db.commit()
    if not changed:
        return get_status(db, owner_id=owner_id, action_id=action_id)
    try:
        from app.services.brain.graph import execute_graph

        with renew_action(db, action_id, token):
            await execute_graph(db, owner_id=owner_id, action_id=action_id, claim_id=token)
    except Exception:
        db.rollback()
        updated = db.execute(
            update(BrainAction)
            .where(BrainAction.id == action_id, BrainAction.owner_id == owner_id, BrainAction.claim_id == token)
            .values(status="failed", error_code="audio_generation_failed", claim_id=None, lease_until=None)
        ).rowcount
        if updated:
            audit(db, owned_action(db, owner_id=owner_id, action_id=action_id), "failed", "audio_generation_failed")
        db.commit()
    return get_status(db, owner_id=owner_id, action_id=action_id)


def delete_session_actions(db, *, owner_id, session_id):
    # Checkpoints contain only opaque IDs. Removing domain rows makes them
    # unusable; checkpoint retention/cleanup is owned by the runtime store.
    db.execute(delete(BrainAction).where(BrainAction.owner_id == owner_id, BrainAction.session_id == session_id))
