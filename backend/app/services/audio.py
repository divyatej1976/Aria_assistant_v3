"""Audio: text-to-speech generation, playback, progress, review, and STT."""

import logging
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import Event, Thread
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.orm import Session

from app.ai.providers import (
    ChainedTTSProvider,
    CloudSTTProvider,
    CloudTTSProvider,
    GroqSTTProvider,
    GroqTTSProvider,
    LocalTTSProvider,
)
from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.models import AudioArtifact, AudioProgress, Note, Resource, ResourceChunk
from app.services.audio_storage import get_audio_storage
from app.services.progress import record_activity

logger = logging.getLogger(__name__)

NOTE = "NOTE"
RESOURCE = "RESOURCE"
# Guard against oversized `audio_artifacts.text`/binary rows and long
# synchronous TTS calls: sources above this many characters are rejected.
# Cloud providers segment the complete source within each request's limit.
MAX_AUDIO_CHARS = 20_000


def get_tts_provider():
    """Provider chain: Groq TTS (GROQ_API_KEY) -> OpenAI TTS key -> local.

    'auto' keeps the local pyttsx3 fallback as the last resort so audio
    generation still works in containers without cloud access; 'cloud'
    restricts to cloud providers only (local if none configured, as before).
    """
    settings = get_settings()
    cloud: list = []
    if settings.groq_api_key:
        cloud.append(
            GroqTTSProvider(
                api_key=settings.groq_api_key,
                model=settings.aria_tts_model,
                voice=settings.aria_tts_voice,
            )
        )
    if settings.aria_tts_api_key:
        cloud.append(CloudTTSProvider(api_key=settings.aria_tts_api_key))
    if settings.aria_tts_provider == "local":
        return LocalTTSProvider()
    if settings.aria_tts_provider == "cloud":
        if not cloud:
            return LocalTTSProvider()
        if len(cloud) == 1:
            return cloud[0]
        return ChainedTTSProvider(cloud)
    return ChainedTTSProvider([*cloud, LocalTTSProvider()])


def get_stt_provider():
    settings = get_settings()
    if settings.groq_api_key:
        return GroqSTTProvider(api_key=settings.groq_api_key, model=settings.aria_stt_model)
    if settings.aria_stt_api_key:
        return CloudSTTProvider(api_key=settings.aria_stt_api_key)
    raise ValidationError(
        "Speech-to-text is not configured. Set GROQ_API_KEY or ARIA_STT_API_KEY to enable voice questions."
    )


def _source_text(
    db: Session, *, owner_id: UUID, source_type: str, source_id: UUID
) -> tuple[str, str]:
    if source_type == NOTE:
        note = db.scalar(
            select(Note).where(Note.id == source_id, Note.owner_id == owner_id)
        )
        if note is None:
            raise ValidationError("Note not found")
        text = note.body
        label = f"Note: {note.title}"
    elif source_type == RESOURCE:
        resource = db.scalar(
            select(Resource).where(Resource.id == source_id, Resource.owner_id == owner_id)
        )
        if resource is None:
            raise ValidationError("Resource not found")
        chunks = db.scalars(
            select(ResourceChunk)
            .where(ResourceChunk.resource_id == resource.id)
            .order_by(ResourceChunk.chunk_index)
        ).all()
        text = resource.source_text or ""
        if not text.strip():
            # Legacy resources may have only overlapping retrieval chunks.
            pieces: list[str] = []
            previous = ""
            for chunk in chunks:
                current = chunk.content
                overlap = next((
                    size for size in range(min(120, len(previous), len(current)), 0, -1)
                    if previous[-size:] == current[:size]
                ), 0)
                pieces.append(current[overlap:])
                previous = current
            text = "".join(pieces)
        label = f"Resource: {resource.title}"
    else:
        raise ValidationError("Unsupported audio source")
    if not text.strip():
        raise ValidationError("No readable text in this source")
    if len(text) > MAX_AUDIO_CHARS:
        # Guard against oversized artifact rows and long synchronous TTS calls.
        raise ValidationError(
            f"Source is too long for audio conversion (over {MAX_AUDIO_CHARS} characters). "
            "Split it into smaller notes or resources."
        )
    return text, label


def list_audio(
    db: Session, *, owner_id: UUID, context_id: UUID | None = None
) -> list[dict]:
    """Durable artifact listing (replaces the frontend localStorage index).

    Owner-scoped always; optionally narrowed to one learning context by
    joining through the polymorphic NOTE/RESOURCE source.
    """
    note_rows = db.execute(
        select(AudioArtifact, Note.title, Note.context_id)
        .join(Note, Note.id == AudioArtifact.source_id)
        .where(
            AudioArtifact.owner_id == owner_id,
            AudioArtifact.source_type == NOTE,
        )
    ).all()
    resource_rows = db.execute(
        select(AudioArtifact, Resource.title, Resource.context_id)
        .join(Resource, Resource.id == AudioArtifact.source_id)
        .where(
            AudioArtifact.owner_id == owner_id,
            AudioArtifact.source_type == RESOURCE,
        )
    ).all()
    # One batched progress query instead of N+1.
    artifact_ids = [a.id for a, _, _ in [*note_rows, *resource_rows]]
    progress_map: dict[UUID, AudioProgress] = {}
    if artifact_ids:
        for progress in db.scalars(
            select(AudioProgress).where(
                AudioProgress.owner_id == owner_id,
                AudioProgress.artifact_id.in_(artifact_ids),
            )
        ):
            progress_map[progress.artifact_id] = progress
    items: list[dict] = []
    for artifact, title, ctx in [*note_rows, *resource_rows]:
        if context_id is not None and ctx != context_id:
            continue
        progress = progress_map.get(artifact.id)
        items.append(
            {
                "id": str(artifact.id),
                "source_type": artifact.source_type,
                "source_id": str(artifact.source_id),
                "title": title,
                "status": artifact.status,
                "content_type": artifact.content_type,
                "duration_seconds": artifact.duration_seconds,
                "position_seconds": progress.position_seconds if progress else 0,
                "completed": progress.completed if progress else False,
                "created_at": artifact.created_at,
            }
        )
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return items


def get_owned_artifact(db: Session, *, owner_id: UUID, artifact_id: UUID) -> AudioArtifact:
    artifact = db.scalar(
        select(AudioArtifact).where(
            AudioArtifact.id == artifact_id, AudioArtifact.owner_id == owner_id
        )
    )
    if artifact is None:
        raise ValidationError("Audio not found")
    return artifact


LEASE_SECONDS = 120
MAX_RECOVERY_ATTEMPTS = 3


def _claimable(now):
    return or_(
        AudioArtifact.status != "PROCESSING",
        AudioArtifact.lease_until.is_(None),
        AudioArtifact.lease_until <= now,
    )


@contextmanager
def _renew_audio_lease(db: Session, artifact_id: UUID, token: UUID):
    """Renew using independent transactions while the provider blocks."""
    stop = Event()
    bind = db.get_bind()

    def renew():
        while not stop.wait(LEASE_SECONDS / 4):
            try:
                with Session(bind) as heartbeat:
                    result = heartbeat.execute(
                        update(AudioArtifact).where(
                            AudioArtifact.id == artifact_id,
                            AudioArtifact.generation_token == token,
                            AudioArtifact.status == "PROCESSING",
                        ).values(lease_until=datetime.now(UTC) + timedelta(seconds=LEASE_SECONDS))
                    )
                    heartbeat.commit()
                    if result.rowcount != 1:
                        return
            except Exception:
                logger.exception("audio lease renewal failed")
                # Without renewal the lease expires; fencing prevents stale writes.

    thread = Thread(target=renew, daemon=True, name="aria-audio-lease")
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=5)


def generate_audio(
    db: Session, *, owner_id: UUID, source_type: str, source_id: UUID,
    provider=None, recovery: bool = False,
) -> AudioArtifact:
    """Claim one source atomically, synthesize outside its transaction, then fence publication."""
    source_model = Note if source_type == NOTE else Resource if source_type == RESOURCE else None
    if source_model is None:
        raise ValidationError("Unsupported audio source")
    # A source-row write serializes first creation as well as existing claims
    # on SQLite/PostgreSQL. No source update is committed to learner content.
    locked = db.execute(update(source_model).where(
        source_model.id == source_id, source_model.owner_id == owner_id,
    ).values(updated_at=source_model.updated_at))
    if locked.rowcount != 1:
        db.rollback()
        raise ValidationError("Audio source not found")
    try:
        text, _ = _source_text(db, owner_id=owner_id, source_type=source_type, source_id=source_id)
    except Exception:
        db.rollback()
        raise
    artifact = db.scalar(select(AudioArtifact).where(
        AudioArtifact.owner_id == owner_id,
        AudioArtifact.source_type == source_type,
        AudioArtifact.source_id == source_id,
    ).order_by(AudioArtifact.created_at, AudioArtifact.id).execution_options(populate_existing=True))
    if artifact is None:
        artifact = AudioArtifact(owner_id=owner_id, source_type=source_type,
                                 source_id=source_id, text=text, status="PENDING")
        db.add(artifact)
        db.flush()
    now = datetime.now(UTC)
    token = uuid4()
    eligibility = _claimable(now)
    if recovery:
        eligibility = and_(eligibility, AudioArtifact.status.in_(["PENDING", "PROCESSING"]))
        if artifact.generation_attempts >= MAX_RECOVERY_ATTEMPTS:
            db.execute(update(AudioArtifact).where(
                AudioArtifact.id == artifact.id, eligibility,
            ).values(status="FAILED", lease_until=None, generation_token=None,
                     error_detail="Audio recovery limit reached. Please retry manually."))
            db.commit()
            db.refresh(artifact)
            return artifact
    attempts = AudioArtifact.generation_attempts + 1 if recovery else 1
    claimed = db.execute(update(AudioArtifact).where(
        AudioArtifact.id == artifact.id, eligibility,
    ).values(status="PROCESSING", text=text, error_detail=None,
             generation_token=token, lease_until=now + timedelta(seconds=LEASE_SECONDS),
             generation_attempts=attempts).execution_options(synchronize_session=False))
    db.commit()
    db.refresh(artifact)
    if claimed.rowcount != 1:
        return artifact
    artifact_id = artifact.id
    old_key = artifact.storage_key
    new_key = None
    with _renew_audio_lease(db, artifact_id, token):
        try:
            audio_bytes, content_type, duration = (provider or get_tts_provider()).generate(text=text)
        except Exception as exc:
            db.rollback()
            logger.warning("audio generation failed error_type=%s", type(exc).__name__)
            db.execute(update(AudioArtifact).where(
                AudioArtifact.id == artifact_id, AudioArtifact.generation_token == token,
            ).values(status="FAILED", lease_until=None, generation_token=None,
                     error_detail="Audio generation failed. Please retry or check audio setup."))
            db.commit()
        else:
            try:
                # A recovered/older worker cannot overwrite another generation's file.
                new_key = get_audio_storage().save(owner_id=owner_id, artifact_id=token,
                                                   content_type=content_type, data=audio_bytes)
                fallback_bytes = None
            except Exception:
                logger.exception("audio storage failed; keeping bytes in DB")
                fallback_bytes = audio_bytes
            published = db.execute(update(AudioArtifact).where(
                AudioArtifact.id == artifact_id, AudioArtifact.generation_token == token,
            ).values(status="READY", lease_until=None, generation_token=None,
                     content_type=content_type, duration_seconds=duration,
                     storage_key=new_key, audio_bytes=fallback_bytes))
            db.commit()
            if published.rowcount == 1:
                if old_key != new_key:
                    _remove_stored([old_key])
            else:
                _remove_stored([new_key])
    current = db.get(AudioArtifact, artifact_id, populate_existing=True)
    if current is None:
        raise ValidationError("Audio source was deleted during generation")
    return current


def process_audio_queue(db: Session, *, limit: int = 5, provider=None) -> int:
    """Recover pending or expired work; active claims are never selected."""
    artifacts = list(db.scalars(select(AudioArtifact).where(
        AudioArtifact.status.in_(["PENDING", "PROCESSING"]),
        _claimable(datetime.now(UTC)),
    ).order_by(AudioArtifact.created_at).limit(limit)))
    processed = 0
    for artifact in artifacts:
        artifact_id, owner_id = artifact.id, artifact.owner_id
        source_type, source_id = artifact.source_type, artifact.source_id
        try:
            generate_audio(db, owner_id=owner_id, source_type=source_type,
                           source_id=source_id, provider=provider, recovery=True)
            processed += 1
        except ValidationError:
            db.rollback()
            # Clean up only actual orphans; oversized/invalid sources are failures.
            source_model = Note if source_type == NOTE else Resource
            source = db.scalar(select(source_model.id).where(
                source_model.id == source_id, source_model.owner_id == owner_id))
            if source is None:
                if db.get(AudioArtifact, artifact_id, populate_existing=True) is not None:
                    delete_audio(db, owner_id=owner_id, artifact_id=artifact_id)
            else:
                db.execute(update(AudioArtifact).where(
                    AudioArtifact.id == artifact_id, _claimable(datetime.now(UTC)),
                ).values(status="FAILED", error_detail="Audio source cannot be processed. Please check its content."))
                db.commit()
        except Exception:
            db.rollback()
            logger.exception("audio queue failed")
            # Do not overwrite an active claim. Its lease supports recovery.
    return processed


def load_audio_bytes(artifact: AudioArtifact) -> bytes | None:
    """Playback bytes: object storage first, legacy DB bytes as fallback."""
    if artifact.storage_key:
        data = get_audio_storage().load(artifact.storage_key)
        if data is not None:
            return data
    return artifact.audio_bytes


def _remove_stored(keys: list[str | None]) -> None:
    storage = get_audio_storage()
    for key in keys:
        if key:
            try:
                storage.delete(key)
            except Exception:
                logger.exception("audio storage delete failed")



def sweep_audio_files(db: Session, *, limit: int = 500, grace_seconds: int = 3600) -> dict:
    """Retry file cleanup after committed deletions and crash-created orphans.

    Unreferenced files are the durable cleanup work list. The grace period
    protects publication; active generation tokens protect long-running work.
    """
    storage = get_audio_storage()
    candidates = getattr(storage, "cleanup_candidates", None)
    result = {"scanned": 0, "deleted": 0, "failed": 0}
    if candidates is None:
        return result
    iterator = iter(candidates(before=datetime.now(UTC) - timedelta(seconds=max(3600, grace_seconds))))
    from itertools import islice

    while result["deleted"] < limit:
        batch = list(islice(iterator, 100))
        if not batch:
            break
        result["scanned"] += len(batch)
        tokens = [UUID(key.split("/")[1].rsplit(".", 1)[0]) for key in batch]
        rows = list(db.execute(select(
            AudioArtifact.storage_key, AudioArtifact.owner_id, AudioArtifact.generation_token,
        ).where(or_(AudioArtifact.storage_key.in_(batch), AudioArtifact.generation_token.in_(tokens)))))
        referenced = {key for key, _, _ in rows if key}
        active = {(str(owner), str(token)) for _, owner, token in rows if token}
        for key in batch:
            owner, file_name = key.split("/")
            token = file_name.rsplit(".", 1)[0]
            if key in referenced or (owner, token) in active:
                continue
            try:
                storage.delete(key)
                result["deleted"] += 1
            except Exception:
                result["failed"] += 1
                logger.exception("audio orphan cleanup failed")
            if result["deleted"] >= limit:
                break
    return result


def requeue_missing_audio(db: Session) -> int:
    """Operator-requested recovery after restoring a database without its audio volume."""
    changed = 0
    artifacts = db.scalars(select(AudioArtifact).where(
        AudioArtifact.status == "READY", AudioArtifact.audio_bytes.is_(None),
    ).execution_options(yield_per=100))
    for artifact in artifacts:
        if load_audio_bytes(artifact) is not None:
            continue
        result = db.execute(update(AudioArtifact).where(
            AudioArtifact.id == artifact.id, AudioArtifact.status == "READY",
            AudioArtifact.storage_key == artifact.storage_key,
        ).values(status="PENDING", generation_token=None, lease_until=None,
                 generation_attempts=0, error_detail="Audio file missing after restore; awaiting regeneration."))
        changed += result.rowcount
    db.commit()
    return changed

def delete_audio(db: Session, *, owner_id: UUID, artifact_id: UUID) -> None:
    artifact = get_owned_artifact(db, owner_id=owner_id, artifact_id=artifact_id)
    # Execute child deletion before scheduling the parent DELETE: without an
    # ORM relationship, the unit of work cannot infer this FK ordering.
    db.execute(delete(AudioProgress).where(AudioProgress.artifact_id == artifact.id))
    storage_key = artifact.storage_key
    db.delete(artifact)
    db.commit()
    _remove_stored([storage_key])


def delete_artifacts_for_source(
    db: Session, *, owner_id: UUID, source_type: str, source_id: UUID
) -> None:
    # Children first: AudioProgress.artifact_id -> audio_artifacts (RESTRICT).
    artifact_ids = select(AudioArtifact.id).where(
        AudioArtifact.owner_id == owner_id,
        AudioArtifact.source_type == source_type,
        AudioArtifact.source_id == source_id,
    )
    db.execute(delete(AudioProgress).where(AudioProgress.artifact_id.in_(artifact_ids)))
    artifacts = db.scalars(
        select(AudioArtifact).where(
            AudioArtifact.owner_id == owner_id,
            AudioArtifact.source_type == source_type,
            AudioArtifact.source_id == source_id,
        )
    ).all()
    keys = [artifact.storage_key for artifact in artifacts]
    for artifact in artifacts:
        db.delete(artifact)
    db.commit()
    _remove_stored(keys)


def get_progress(db: Session, *, owner_id: UUID, artifact_id: UUID) -> AudioProgress:
    artifact = get_owned_artifact(db, owner_id=owner_id, artifact_id=artifact_id)
    progress = db.scalar(
        select(AudioProgress).where(
            AudioProgress.owner_id == owner_id, AudioProgress.artifact_id == artifact.id
        )
    )
    if progress is None:
        progress = AudioProgress(owner_id=owner_id, artifact_id=artifact.id)
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress


def save_progress(
    db: Session, *, owner_id: UUID, artifact_id: UUID, position_seconds: int, completed: bool
) -> AudioProgress:
    get_owned_artifact(db, owner_id=owner_id, artifact_id=artifact_id)
    progress = db.scalar(
        select(AudioProgress).where(
            AudioProgress.owner_id == owner_id, AudioProgress.artifact_id == artifact_id
        )
    )
    if progress is None:
        progress = AudioProgress(
            owner_id=owner_id,
            artifact_id=artifact_id,
            position_seconds=position_seconds,
            completed=completed,
        )
        db.add(progress)
    else:
        progress.position_seconds = position_seconds
        progress.completed = completed
        db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


def mark_reviewed(db: Session, *, owner_id: UUID, artifact_id: UUID) -> AudioArtifact:
    artifact = get_owned_artifact(db, owner_id=owner_id, artifact_id=artifact_id)
    record_activity(db, owner_id=owner_id, activity_type="revision", source_id=artifact.id)
    return artifact


def transcribe_audio(*, audio: bytes, content_type: str, provider=None) -> str:
    stt = provider or get_stt_provider()
    return stt.transcribe(audio=audio, content_type=content_type)
