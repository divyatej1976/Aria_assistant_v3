"""Audio: text-to-speech generation, playback, progress, review, and STT."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers import CloudSTTProvider, CloudTTSProvider, LocalTTSProvider
from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.models import AudioArtifact, AudioProgress, Note, Resource, ResourceChunk
from app.services.progress import record_activity

NOTE = "NOTE"
RESOURCE = "RESOURCE"


def get_tts_provider():
    settings = get_settings()
    if settings.aria_tts_provider == "local":
        return LocalTTSProvider()
    if settings.aria_tts_provider == "cloud":
        if settings.aria_tts_api_key:
            return CloudTTSProvider(api_key=settings.aria_tts_api_key)
        return LocalTTSProvider()
    if settings.aria_tts_api_key:
        return CloudTTSProvider(api_key=settings.aria_tts_api_key)
    return LocalTTSProvider()


def get_stt_provider():
    settings = get_settings()
    if not settings.aria_stt_api_key:
        raise ValidationError(
            "Speech-to-text is not configured. Set ARIA_STT_API_KEY to enable voice questions."
        )
    return CloudSTTProvider(api_key=settings.aria_stt_api_key)


def _source_text(
    db: Session, *, owner_id: UUID, source_type: str, source_id: UUID
) -> tuple[str, str]:
    if source_type == NOTE:
        note = db.scalar(
            select(Note).where(Note.id == source_id, Note.owner_id == owner_id)
        )
        if note is None:
            raise ValidationError("Note not found")
        return note.body, f"Note: {note.title}"
    if source_type == RESOURCE:
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
        if not text.strip():
            raise ValidationError("No readable text in this resource")
        return text, f"Resource: {resource.title}"
    raise ValidationError("Unsupported audio source")


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
    artifact.audio_bytes = None
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
    """Generate audio for artifacts stuck in PENDING/PROCESSING. Scheduler job."""
    artifacts = list(
        db.scalars(
            select(AudioArtifact)
            .where(AudioArtifact.status.in_(["PENDING", "PROCESSING"]))
            .order_by(AudioArtifact.created_at)
            .limit(limit)
        )
    )
    for artifact in artifacts:
        generate_audio(
            db,
            owner_id=artifact.owner_id,
            source_type=artifact.source_type,
            source_id=artifact.source_id,
            provider=provider,
        )
    return len(artifacts)


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
