import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.schemas.audio import (
    AudioListItem,
    AudioResponse,
    ProgressResponse,
    ProgressUpdateRequest,
    TranscribeResponse,
)
from app.security.dependencies import CurrentLearner
from app.services.audio import (
    NOTE,
    RESOURCE,
    delete_audio,
    generate_audio,
    get_owned_artifact,
    get_progress,
    list_audio,
    mark_reviewed,
    save_progress,
    transcribe_audio,
)

router = APIRouter(prefix="/api/v1/audio", tags=["audio"])
Db = Annotated[Session, Depends(get_db)]

logger = logging.getLogger(__name__)


def audio_response(artifact) -> AudioResponse:
    return AudioResponse(
        id=str(artifact.id),
        source_type=artifact.source_type,
        source_id=str(artifact.source_id),
        text=artifact.text,
        status=artifact.status,
        error_detail=artifact.error_detail,
        content_type=artifact.content_type,
        duration_seconds=artifact.duration_seconds,
        created_at=artifact.created_at,
    )


@router.get("", response_model=list[AudioListItem])
def list_artifacts(
    learner: CurrentLearner, db: Db, context_id: UUID | None = None
) -> list[AudioListItem]:
    """Durable audio listing for the account (optionally per learning context)."""
    return [AudioListItem(**item) for item in list_audio(db, owner_id=learner.id, context_id=context_id)]


@router.post("/notes/{note_id}/generate", response_model=AudioResponse, status_code=201)
def generate_note_audio(note_id: UUID, learner: CurrentLearner, db: Db) -> AudioResponse:
    try:
        artifact = generate_audio(
            db, owner_id=learner.id, source_type=NOTE, source_id=note_id
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return audio_response(artifact)


@router.post("/resources/{resource_id}/generate", response_model=AudioResponse, status_code=201)
def generate_resource_audio(
    resource_id: UUID, learner: CurrentLearner, db: Db
) -> AudioResponse:
    try:
        artifact = generate_audio(
            db, owner_id=learner.id, source_type=RESOURCE, source_id=resource_id
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return audio_response(artifact)


@router.get("/{artifact_id}", response_model=AudioResponse)
def detail(artifact_id: UUID, learner: CurrentLearner, db: Db) -> AudioResponse:
    try:
        artifact = get_owned_artifact(db, owner_id=learner.id, artifact_id=artifact_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return audio_response(artifact)


@router.get("/{artifact_id}/play")
def play(artifact_id: UUID, learner: CurrentLearner, db: Db) -> Response:
    try:
        artifact = get_owned_artifact(db, owner_id=learner.id, artifact_id=artifact_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if artifact.status != "READY" or not artifact.audio_bytes:
        raise HTTPException(status_code=409, detail="Audio is not ready")
    return Response(
        content=artifact.audio_bytes,
        media_type=artifact.content_type or "audio/mpeg",
    )


@router.get("/{artifact_id}/progress", response_model=ProgressResponse)
def progress(artifact_id: UUID, learner: CurrentLearner, db: Db) -> ProgressResponse:
    try:
        item = get_progress(db, owner_id=learner.id, artifact_id=artifact_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProgressResponse(
        position_seconds=item.position_seconds, completed=item.completed
    )


@router.put("/{artifact_id}/progress", response_model=ProgressResponse)
def update_progress(
    artifact_id: UUID,
    request: ProgressUpdateRequest,
    learner: CurrentLearner,
    db: Db,
) -> ProgressResponse:
    try:
        item = save_progress(
            db,
            owner_id=learner.id,
            artifact_id=artifact_id,
            position_seconds=request.position_seconds,
            completed=request.completed,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ProgressResponse(
        position_seconds=item.position_seconds, completed=item.completed
    )


@router.post("/{artifact_id}/review", response_model=AudioResponse)
def review(artifact_id: UUID, learner: CurrentLearner, db: Db) -> AudioResponse:
    try:
        artifact = mark_reviewed(db, owner_id=learner.id, artifact_id=artifact_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return audio_response(artifact)


@router.delete("/{artifact_id}")
def delete(artifact_id: UUID, learner: CurrentLearner, db: Db) -> dict[str, object]:
    try:
        delete_audio(db, owner_id=learner.id, artifact_id=artifact_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": True}


@router.post("/transcribe", response_model=TranscribeResponse)
def transcribe(
    file: Annotated[UploadFile, File(...)], learner: CurrentLearner
) -> TranscribeResponse:
    # Bound memory usage: reject oversized uploads before reading into RAM.
    max_bytes = 10 * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(status_code=413, detail="Audio upload exceeds 10 MB")
    content = file.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="Audio upload exceeds 10 MB")
    try:
        text = transcribe_audio(audio=content, content_type=file.content_type or "audio/webm")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        # Provider failures (e.g. cloud STT rejects the payload with 400)
        # must degrade to 422, never leak as a 500. Details stay server-side.
        logger.exception("transcription provider failed")
        raise HTTPException(
            status_code=422, detail="Speech-to-text provider rejected the audio"
        ) from None
    return TranscribeResponse(text=text)
