"""Audio: text-to-speech generation, playback, progress, review, and STT."""

from uuid import UUID

from sqlalchemy import delete, select
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
from app.services.progress import record_activity

NOTE = "NOTE"
RESOURCE = "RESOURCE"
# Guard against oversized `audio_artifacts.text`/binary rows and long
# synchronous TTS calls: sources above this many characters are rejected.
# (CloudTTSProvider additionally truncates its request to 4000 chars.)
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
        text = " ".join(chunk.content for chunk in chunks)
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


def generate_audio(
    db: Session,
    *,
    owner_id: UUID,
    source_type: str,
    source_id: UUID,
    provider=None,
) -> AudioArtifact:
    """Simple read-aloud (Step 3): raw note/resource text straight to TTS.

    No LLM script generation happens here; Groq-scripted dialogue is a
    separate Step 3b enhancement. Generation runs synchronously in-request
    and stores bytes in PostgreSQL (`audio_bytes`); large resources can
    therefore create oversized rows and long requests. Production scale
    should move this to a background queue + object storage (`storage_key`).
    """
    text, _label = _source_text(db, owner_id=owner_id, source_type=source_type, source_id=source_id)
    artifact = db.scalar(
        select(AudioArtifact).where(
            AudioArtifact.owner_id == owner_id,
            AudioArtifact.source_type == source_type,
            AudioArtifact.source_id == source_id,
        )
    )
    if artifact is None:
        artifact = AudioArtifact(
            owner_id=owner_id,
            source_type=source_type,
            source_id=source_id,
            text=text,
            status="PROCESSING",
        )
        db.add(artifact)
        db.flush()
    artifact.text = text
    artifact.status = "PROCESSING"
    artifact.error_detail = None
    # Keep any previously-good bytes until the new generation succeeds: a
    # failed regeneration must not destroy working audio (playback is then
    # honestly blocked via the READY check instead of silently reverting).
    db.add(artifact)
    db.commit()
    db.refresh(artifact)

    tts = provider or get_tts_provider()
    try:
        audio_bytes, content_type, duration = tts.generate(text=text)
    except Exception as exc:
        artifact.status = "FAILED"
        artifact.error_detail = str(exc)[:500]
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
        return artifact
    artifact.status = "READY"
    artifact.audio_bytes = audio_bytes
    artifact.content_type = content_type
    artifact.duration_seconds = duration
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def process_audio_queue(db: Session, *, limit: int = 5, provider=None) -> int:
    """Generate audio for artifacts stuck in PENDING/PROCESSING. Scheduler job.

    Per-item isolation: one broken artifact (e.g., its source note/resource
    was deleted in a race) is cleaned up or failed without stalling the queue.
    """
    artifacts = list(
        db.scalars(
            select(AudioArtifact)
            .where(AudioArtifact.status.in_(["PENDING", "PROCESSING"]))
            .order_by(AudioArtifact.created_at)
            .limit(limit)
        )
    )
    processed = 0
    for artifact in artifacts:
        processed += 1
        try:
            generate_audio(
                db,
                owner_id=artifact.owner_id,
                source_type=artifact.source_type,
                source_id=artifact.source_id,
                provider=provider,
            )
        except ValidationError:
            # Source gone: the artifact is an orphan; remove it and its progress.
            db.execute(
                delete(AudioProgress).where(AudioProgress.artifact_id == artifact.id)
            )
            artifact_ref = db.get(AudioArtifact, artifact.id)
            if artifact_ref is not None:
                db.delete(artifact_ref)
            db.commit()
        except Exception as exc:  # noqa: BLE001 - queue must never stall
            artifact.status = "FAILED"
            artifact.error_detail = str(exc)[:500]
            db.add(artifact)
            db.commit()
    return processed


def delete_audio(db: Session, *, owner_id: UUID, artifact_id: UUID) -> None:
    artifact = get_owned_artifact(db, owner_id=owner_id, artifact_id=artifact_id)
    progress = db.scalar(
        select(AudioProgress).where(
            AudioProgress.owner_id == owner_id, AudioProgress.artifact_id == artifact.id
        )
    )
    if progress is not None:
        db.delete(progress)
    db.delete(artifact)
    db.commit()


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
    for artifact in db.scalars(
        select(AudioArtifact).where(
            AudioArtifact.owner_id == owner_id,
            AudioArtifact.source_type == source_type,
            AudioArtifact.source_id == source_id,
        )
    ):
        db.delete(artifact)
    db.commit()


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
