from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models import ConversationMessage, LearningContext, StudySession
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
from app.services.study import answer_question

router = APIRouter(prefix="/api/v1/study", tags=["study"])
Db = Annotated[Session, Depends(get_db)]


def get_context(db: Session, *, context_id: UUID, owner_id: UUID) -> LearningContext:
    context = db.scalar(
        select(LearningContext).where(
            LearningContext.id == context_id, LearningContext.owner_id == owner_id
        )
    )
    if context is None:
        raise HTTPException(status_code=404, detail="Learning context not found")
    return context


def get_session(
    db: Session, *, session_id: UUID, owner_id: UUID, context_id: UUID | None = None
) -> StudySession:
    query = select(StudySession).where(
        StudySession.id == session_id, StudySession.owner_id == owner_id
    )
    if context_id is not None:
        query = query.where(StudySession.context_id == context_id)
    session = db.scalar(query)
    if session is None:
        raise HTTPException(status_code=404, detail="Study session not found")
    return session


def session_response(session: StudySession) -> StudySessionResponse:
    return StudySessionResponse(
        id=str(session.id),
        context_id=str(session.context_id),
        mode=session.mode,
        status=session.status,
        created_at=session.created_at,
    )


@router.get("/sessions", response_model=list[StudySessionResponse])
def list_sessions(
    learner: CurrentLearner, db: Db, context_id: str
) -> list[StudySessionResponse]:
    context_uuid = UUID(context_id)
    get_context(db, context_id=context_uuid, owner_id=learner.id)
    sessions = db.scalars(
        select(StudySession)
        .where(StudySession.owner_id == learner.id, StudySession.context_id == context_uuid)
        .order_by(StudySession.created_at)
    ).all()
    return [session_response(item) for item in sessions]


@router.get("/sessions/{session_id}/messages", response_model=list[StudyMessage])
def list_messages(
    session_id: UUID, learner: CurrentLearner, db: Db
) -> list[StudyMessage]:
    get_session(db, session_id=session_id, owner_id=learner.id)
    messages = db.scalars(
        select(ConversationMessage)
        .where(
            ConversationMessage.study_session_id == session_id,
            ConversationMessage.owner_id == learner.id,
        )
        .order_by(ConversationMessage.position, ConversationMessage.created_at)
    ).all()
    return [
        StudyMessage(
            id=str(message.id),
            role=message.role,
            content=message.content,
            sources=[SourceReference(**ref) for ref in message.source_refs],
        )
        for message in messages
    ]


@router.delete("/sessions/{session_id}/messages/{message_id}")
def delete_message(
    session_id: UUID, message_id: UUID, learner: CurrentLearner, db: Db
) -> dict[str, object]:
    get_session(db, session_id=session_id, owner_id=learner.id)
    if not delete_message_service(db, owner_id=learner.id, message_id=message_id):
        raise HTTPException(status_code=404, detail="Message not found")
    return {"deleted": True}


@router.post("/sessions", status_code=201)
def create_session(
    request: StudySessionCreate, learner: CurrentLearner, db: Db
) -> dict[str, str]:
    context_id = UUID(request.context_id)
    get_context(db, context_id=context_id, owner_id=learner.id)
    session = StudySession(owner_id=learner.id, context_id=context_id, mode=request.mode)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "id": str(session.id),
        "context_id": str(session.context_id),
        "mode": session.mode,
        "status": session.status,
    }


@router.post("/sessions/{session_id}/messages", response_model=StudyMessageResponse)
async def send_message(
    session_id: UUID, request: StudyMessageCreate, learner: CurrentLearner, db: Db
) -> StudyMessageResponse:
    session = get_session(db, session_id=session_id, owner_id=learner.id)
    message_count = db.scalar(
        select(func.count(ConversationMessage.id)).where(
            ConversationMessage.study_session_id == session.id,
            ConversationMessage.owner_id == learner.id,
        )
    )
    user_position = (message_count or 0) + 1
    db.add(
        ConversationMessage(
            owner_id=learner.id,
            study_session_id=session.id,
            role="user",
            content=request.content,
            position=user_position,
        )
    )
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
    db.add(
        ConversationMessage(
            owner_id=learner.id,
            study_session_id=session.id,
            role="assistant",
            content=result.content,
            source_refs=refs,
            position=user_position + 1,
        )
    )
    db.commit()
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
