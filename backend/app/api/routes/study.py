from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
from app.services.memory import delete_message as delete_message_service
from app.services.progress import record_activity
from app.services.study import (
    answer_question,
    create_session,
    get_owned_session,
    list_messages,
    list_sessions,
    persist_conversation_turn,
)

router = APIRouter(prefix="/api/v1/study", tags=["study"])
Db = Annotated[Session, Depends(get_db)]


def session_response(session) -> StudySessionResponse:
    return StudySessionResponse(
        id=str(session.id),
        context_id=str(session.context_id),
        mode=session.mode,
        status=session.status,
        created_at=session.created_at,
    )


@router.get("/sessions", response_model=list[StudySessionResponse])
def sessions(learner: CurrentLearner, db: Db, context_id: str) -> list[StudySessionResponse]:
    context_uuid = UUID(context_id)
    try:
        items = list_sessions(db, owner_id=learner.id, context_id=context_uuid)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [session_response(item) for item in items]


@router.get("/sessions/{session_id}/messages", response_model=list[StudyMessage])
def messages(session_id: UUID, learner: CurrentLearner, db: Db) -> list[StudyMessage]:
    try:
        get_owned_session(db, owner_id=learner.id, session_id=session_id)
        items = list_messages(db, owner_id=learner.id, session_id=session_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [
        StudyMessage(
            id=str(message.id),
            role=message.role,
            content=message.content,
            sources=[SourceReference(**ref) for ref in message.source_refs],
        )
        for message in items
    ]


@router.delete("/sessions/{session_id}/messages/{message_id}")
def delete_message(
    session_id: UUID, message_id: UUID, learner: CurrentLearner, db: Db
) -> dict[str, object]:
    try:
        get_owned_session(db, owner_id=learner.id, session_id=session_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not delete_message_service(db, owner_id=learner.id, message_id=message_id):
        raise HTTPException(status_code=404, detail="Message not found")
    return {"deleted": True}


@router.post("/sessions", status_code=201)
def create(
    request: StudySessionCreate, learner: CurrentLearner, db: Db
) -> StudySessionResponse:
    context_id = UUID(request.context_id)
    try:
        session = create_session(
            db, owner_id=learner.id, context_id=context_id, mode=request.mode
        )
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return session_response(session)


@router.post("/sessions/{session_id}/messages", response_model=StudyMessageResponse)
async def send_message(
    session_id: UUID, request: StudyMessageCreate, learner: CurrentLearner, db: Db
) -> StudyMessageResponse:
    try:
        session = get_owned_session(db, owner_id=learner.id, session_id=session_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = await answer_question(
        db,
        owner_id=learner.id,
        context_id=session.context_id,
        question=request.content,
        session_id=session.id,
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
    )
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
    )
