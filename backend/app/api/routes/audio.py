import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.schemas.audio import (
    AudioListItem,
    AudioResponse,
    ProgressResponse,
    ProgressUpdateRequest,
    TranscribeResponse,
    TextAudioRequest,
)
from app.security.dependencies import CurrentLearner
from app.security.rate_limit import rate_limited
from app.services.audio import (
    NOTE,
    RESOURCE,
    delete_audio,
    generate_audio,
    get_owned_artifact,
    get_progress,
    list_audio,
    load_audio_bytes,
    mark_reviewed,
    save_progress,
    transcribe_audio,
)
from app.db.models import ConversationMessage, LearningContext, Resource, StudySession
from app.services.resource_ingestion import create_text_resource

router = APIRouter(prefix="/api/v1/audio", tags=["audio"])
Db = Annotated[Session, Depends(get_db)]

logger = logging.getLogger(__name__)


def _ai_rate_limit():
    settings = get_settings()
    return rate_limited(
        settings.aria_rate_limit_requests, settings.aria_rate_limit_window_seconds
    )


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


@router.post(
    "/notes/{note_id}/generate",
    response_model=AudioResponse,
    status_code=201,
    dependencies=[Depends(_ai_rate_limit())],
)
def generate_note_audio(note_id: UUID, learner: CurrentLearner, db: Db) -> AudioResponse:
    try:
        artifact = generate_audio(
            db, owner_id=learner.id, source_type=NOTE, source_id=note_id
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return audio_response(artifact)


@router.post(
    "/resources/{resource_id}/generate",
    response_model=AudioResponse,
    status_code=201,
    dependencies=[Depends(_ai_rate_limit())],
)
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


async def _generate_from_text(db: Session, *, owner_id: UUID, context_id: UUID,
                              title: str, text: str) -> AudioResponse:
    if not db.scalar(select(LearningContext).where(
        LearningContext.id == context_id, LearningContext.owner_id == owner_id,
    )):
        raise HTTPException(status_code=404, detail="Learning context not found")
    text, title = text.strip(), title.strip()
    if not text or not title:
        raise HTTPException(status_code=422, detail="Enter a title and some text to create audio")
    if len(text) > 20_000:
        raise HTTPException(status_code=422, detail="This conversation is too long for one episode. Paste a section of up to 20,000 characters in Audio studio.")
    # Reuse an unchanged snapshot on retry, including after a lost response.
    resource = db.scalar(select(Resource).where(
        Resource.owner_id == owner_id, Resource.context_id == context_id,
        Resource.title == title, Resource.source_text == text, Resource.resource_type == "TEXT",
    ).order_by(Resource.created_at, Resource.id))
    try:
        if resource is None:
            resource = await create_text_resource(db, owner_id=owner_id,
                context_id=context_id, title=title, text=text)
        artifact = await run_in_threadpool(generate_audio, db, owner_id=owner_id,
            source_type=RESOURCE, source_id=resource.id)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return audio_response(artifact)


@router.post("/text/generate", response_model=AudioResponse, status_code=201,
             dependencies=[Depends(_ai_rate_limit())])
async def generate_text_audio(request: TextAudioRequest, learner: CurrentLearner, db: Db) -> AudioResponse:
    return await _generate_from_text(db, owner_id=learner.id, context_id=request.context_id,
                                    title=request.title, text=request.text)


@router.post("/sessions/{session_id}/generate", response_model=AudioResponse, status_code=201,
             dependencies=[Depends(_ai_rate_limit())])
async def generate_session_audio(session_id: UUID, learner: CurrentLearner, db: Db) -> AudioResponse:
    session = db.scalar(select(StudySession).where(
        StudySession.id == session_id, StudySession.owner_id == learner.id,
    ))
    if session is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = db.scalars(select(ConversationMessage).where(
        ConversationMessage.study_session_id == session.id,
        ConversationMessage.owner_id == learner.id,
    ).order_by(ConversationMessage.position, ConversationMessage.created_at, ConversationMessage.id)).all()
    if not any(m.role in ("assistant", "aria") and m.content.strip() for m in messages):
        raise HTTPException(status_code=422, detail="Get a tutor response before creating audio from this conversation")
    text = "\n\n".join(
        f"{'You' if m.role == 'user' else 'ARIA'}: {m.content.strip()}"
        for m in messages if m.role in ("user", "assistant", "aria") and m.content.strip()
    )
    first_question = next((m.content for m in messages if m.role == "user"), "Tutor conversation")
    title = f"Chat: {first_question}"[:200]
    return await _generate_from_text(db, owner_id=learner.id, context_id=session.context_id,
                                    title=title, text=text)


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
    data = load_audio_bytes(artifact)
    if artifact.status != "READY" or not data:
        raise HTTPException(status_code=409, detail="Audio is not ready")
    return Response(
        content=data,
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


@router.post("/transcribe", response_model=TranscribeResponse, dependencies=[Depends(_ai_rate_limit())])
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
    except Exception as exc:
        # Provider failures (e.g. cloud STT rejects the payload with 400)
        # must degrade to 422 without exposing provider text or credentials.
        logger.error("transcription provider failed error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=422, detail="Speech-to-text provider rejected the audio"
        ) from None
    return TranscribeResponse(text=text)
