from typing import Annotated
import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.schemas.study import (
    SourceReference,
    StudyMessage,
    StudyMessageCreate,
    StudyMessageResponse,
    StudySessionCreate,
    StudySessionResponse,
)
from app.security.dependencies import CurrentLearner
from app.security.rate_limit import rate_limited
from app.services.daily_review import finish_day
from app.services.idempotency import ClaimLost
from app.services.memory import delete_message as delete_message_service
from app.services.progress import record_activity
from app.services.response_style import resolve_style
from app.services.study import (
    SessionSummary,
    answer_question,
    create_session,
    delete_session,
    get_owned_session,
    list_messages,
    list_sessions,
    persist_conversation_turn,
    session_summaries,
)
from app.services.study_requests import (
    ReplyPending,
    ReplyStopped,
    answer_and_save,
    last_tutor_message,
    name_chat,
    stop_reply,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/study", tags=["study"])
Db = Annotated[Session, Depends(get_db)]


def _ai_rate_limit():
    settings = get_settings()
    return rate_limited(
        settings.aria_rate_limit_requests, settings.aria_rate_limit_window_seconds
    )


@router.post("/contexts/{context_id}/finish-day", dependencies=[Depends(_ai_rate_limit())])
async def finish_learning_day(context_id: UUID, learner: CurrentLearner, db: Db) -> dict[str, str]:
    try:
        assessment = await finish_day(db, owner_id=learner.id, context_id=context_id)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"assessment_id": str(assessment.id), "review_date": assessment.daily_review_date}


def session_response(session, summary: SessionSummary | None = None) -> StudySessionResponse:
    return StudySessionResponse(
        id=str(session.id),
        context_id=str(session.context_id),
        mode=session.mode,
        status=session.status,
        created_at=session.created_at,
        title=summary.title if summary else None,
        preview=summary.preview if summary else None,
        message_count=summary.message_count if summary else 0,
        last_message_at=summary.last_message_at if summary else None,
    )


@router.get("/sessions", response_model=list[StudySessionResponse])
def sessions(
    learner: CurrentLearner, db: Db, context_id: UUID,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[StudySessionResponse]:
    try:
        items = list_sessions(db, owner_id=learner.id, context_id=context_id, limit=limit, offset=offset)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    summaries = session_summaries(db, owner_id=learner.id, session_ids=[item.id for item in items])
    return [session_response(item, summaries.get(item.id)) for item in items]


@router.get("/sessions/{session_id}/messages", response_model=list[StudyMessage])
def messages(
    session_id: UUID, learner: CurrentLearner, db: Db,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    before_position: Annotated[int | None, Query(ge=1)] = None,
) -> list[StudyMessage]:
    try:
        get_owned_session(db, owner_id=learner.id, session_id=session_id)
        items = list_messages(
            db, owner_id=learner.id, session_id=session_id,
            limit=limit, before_position=before_position,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [
        StudyMessage(
            id=str(message.id),
            role=message.role,
            content=message.content,
            position=message.position,
            fallback_used=message.fallback_used,
            depth=message.response_depth,
            action=_message_action(db, learner.id, message),
            sources=[SourceReference(**ref) for ref in message.source_refs],
        )
        for message in items
    ]


def _message_action(db, owner_id, message):
    if not message.action:
        return None
    from app.services.brain.actions import get_status
    return get_status(db, owner_id=owner_id, action_id=message.id)


@router.post(
    "/sessions/{session_id}/messages/stream",
    dependencies=[Depends(_ai_rate_limit())],
)
async def stream_message(
    session_id: UUID, request: StudyMessageCreate, learner: CurrentLearner, db: Db
) -> StreamingResponse:
    """Like POST /messages, but the reply arrives as it is written: one JSON object per line.

    {"type": "delta", "text": ...} for each new piece, then {"type": "done", "message": ...} with
    the saved reply (the same body POST /messages returns) or {"type": "error", ...}.
    """
    try:
        session = get_owned_session(db, owner_id=learner.id, session_id=session_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if request.request_id is None:
        raise HTTPException(status_code=422, detail="request_id is required to stream a reply")
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def run() -> None:
        try:
            response = await answer_and_save(
                db, owner_id=learner.id, session=session, content=request.content,
                request_id=request.request_id, depth=request.depth, screen=request.screen,
                on_delta=lambda text: queue.put_nowait({"type": "delta", "text": text}),
            )
            record_activity(db, owner_id=learner.id, activity_type="study", source_id=session.id)
            queue.put_nowait({"type": "done", "message": response.model_dump()})
        except (ReplyPending, ClaimLost, ReplyStopped) as exc:
            queue.put_nowait({"type": "error", "status": 409, "detail": str(exc)})
        except Exception:
            logger.exception("streamed reply failed")
            queue.put_nowait({"type": "error", "status": 500,
                              "detail": "Your reply could not be loaded. Please try again."})

    async def events():
        task = asyncio.create_task(run())
        try:
            while True:
                event = await queue.get()
                yield json.dumps(event) + "\n"
                if event["type"] != "delta":
                    break
        finally:
            # If the browser goes away, the reply still finishes and is saved (or discarded by Stop)
            # before this request's database session closes.
            await asyncio.shield(task)

    return StreamingResponse(events(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.post("/sessions/{session_id}/messages/{request_id}/stop")
def stop_message(session_id: UUID, request_id: UUID, learner: CurrentLearner, db: Db) -> dict[str, bool]:
    """Stop a reply that is still being prepared: when it finishes it is thrown away."""
    try:
        get_owned_session(db, owner_id=learner.id, session_id=session_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    stop_reply(session_id=session_id, request_id=request_id)
    return {"stopped": True}


@router.delete("/sessions/{session_id}/messages/{message_id}")
def delete_message(
    session_id: UUID, message_id: UUID, learner: CurrentLearner, db: Db
) -> dict[str, object]:
    try:
        get_owned_session(db, owner_id=learner.id, session_id=session_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not delete_message_service(
        db, owner_id=learner.id, session_id=session_id, message_id=message_id
    ):
        raise HTTPException(status_code=404, detail="Message not found")
    return {"deleted": True}



@router.delete("/sessions/{session_id}")
def delete_session_route(session_id: UUID, learner: CurrentLearner, db: Db) -> dict[str, bool]:
    if not delete_session(db, owner_id=learner.id, session_id=session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}

@router.post("/sessions", status_code=201)
def create(
    request: StudySessionCreate, learner: CurrentLearner, db: Db
) -> StudySessionResponse:
    try:
        session = create_session(
            db, owner_id=learner.id, context_id=request.context_id, mode=request.mode
        )
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return session_response(session)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=StudyMessageResponse,
    dependencies=[Depends(_ai_rate_limit())],
)
async def send_message(
    session_id: UUID, request: StudyMessageCreate, learner: CurrentLearner, db: Db
) -> StudyMessageResponse:
    try:
        session = get_owned_session(db, owner_id=learner.id, session_id=session_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if request.request_id is not None or get_settings().aria_brain_routing:
        try:
            response = await answer_and_save(
                db, owner_id=learner.id, session=session, content=request.content,
                request_id=request.request_id, depth=request.depth, screen=request.screen,
            )
        except (ReplyPending, ClaimLost, ReplyStopped) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        record_activity(db, owner_id=learner.id, activity_type="study", source_id=session.id)
        return response
    style = resolve_style(request.content, request.depth, request.screen,
                          last_tutor_message(db, owner_id=learner.id, session_id=session.id))
    result = await answer_question(
        db,
        owner_id=learner.id,
        context_id=session.context_id,
        question=request.content,
        session_id=session.id,
        style=style,
    )
    refs = [
        {
            "resource_id": source.resource_id,
            "chunk_id": source.chunk_id,
            "title": source.source_title,
            "score": source.score,
        }
        for source in result.sources
    ]
    persist_conversation_turn(
        db,
        owner_id=learner.id,
        session=session,
        user_content=request.content,
        assistant_content=result.content,
        assistant_refs=refs,
        fallback_used=result.fallback_used,
        response_depth=style.depth,
    )
    if not session.title and not result.fallback_used:
        await name_chat(db, owner_id=learner.id, session=session, question=request.content)
    record_activity(db, owner_id=learner.id, activity_type="study", source_id=session.id)
    return StudyMessageResponse(
        session_id=str(session.id),
        content=result.content,
        sources=[
            SourceReference(
                resource_id=source.resource_id,
                chunk_id=source.chunk_id,
                title=source.source_title,
                score=source.score,
            )
            for source in result.sources
        ],
        fallback_used=result.fallback_used,
        depth=style.depth,
    )
