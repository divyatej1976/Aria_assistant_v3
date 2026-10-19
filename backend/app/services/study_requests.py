"""Retryable tutoring requests with one durable conversation turn per request."""

from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ConversationMessage, StudySession
from app.schemas.study import SourceReference, StudyMessageResponse
from app.services import idempotency
from app.services.response_style import RequestedDepth, Screen, resolve_style
from app.services.study import answer_question, persist_conversation_turn


def last_tutor_message(db: Session, *, owner_id: UUID, session_id: UUID) -> str | None:
    """The tutor's latest reply in this chat, so a learner's answer to its question can be graded."""
    return db.scalar(select(ConversationMessage.content).where(
        ConversationMessage.owner_id == owner_id, ConversationMessage.study_session_id == session_id,
        ConversationMessage.role == "assistant",
    ).order_by(ConversationMessage.position.desc()).limit(1))


class ReplyPending(Exception):
    pass


async def answer_and_save(
    db: Session, *, owner_id: UUID, session: StudySession, content: str, request_id: UUID | None,
    depth: RequestedDepth = "auto", screen: Screen = "regular",
) -> StudyMessageResponse:
    scope = "study:reply"
    key = f"{session.id}:{request_id}" if request_id is not None else None
    message_id = uuid5(NAMESPACE_URL, f"aria:reply:{owner_id}:{key}") if key else None
    # The message identity survives expiration or cleanup of short-lived request
    # keys, and the pair was committed atomically with its response checkpoint.
    if message_id is not None:
        user = db.scalar(select(ConversationMessage).where(
            ConversationMessage.id == message_id, ConversationMessage.owner_id == owner_id,
            ConversationMessage.study_session_id == session.id,
        ))
        if user is not None:
            if user.content != content:
                raise ReplyPending("This retry belongs to a different question. Start a new message.")
            assistant = db.scalar(select(ConversationMessage).where(
                ConversationMessage.owner_id == owner_id,
                ConversationMessage.study_session_id == session.id,
                ConversationMessage.position == user.position + 1,
                ConversationMessage.role == "assistant",
            ))
            if assistant is None:
                raise ReplyPending("The saved reply was removed. Start a new message.")
            return StudyMessageResponse(session_id=str(session.id), content=assistant.content,
                                        id=str(assistant.id), depth=assistant.response_depth,
                                        action=_saved_action(db, owner_id, assistant),
                                        sources=[SourceReference(**ref) for ref in assistant.source_refs],
                                        fallback_used=bool(assistant.fallback_used))
    claim_id = uuid4()
    if key is not None:
        state = idempotency.reserve(db, owner_id=owner_id, scope=scope, key=key, claim_id=claim_id,
                                    request_fingerprint=idempotency.fingerprint({"content": content}))
        if state == "completed":
            return StudyMessageResponse(**idempotency.find(db, owner_id=owner_id, scope=scope, key=key).response_json)
        if state != "ok":
            raise ReplyPending("This reply is still being prepared. Wait a moment and retry.")
    try:
        style = resolve_style(content, depth, screen,
                              last_tutor_message(db, owner_id=owner_id, session_id=session.id))
        assistant_id = uuid5(NAMESPACE_URL, f"aria:assistant:{owner_id}:{key}") if key else uuid4()
        async def respond():
            from app.core.errors import ValidationError
            from app.services.brain.actions import prepare_audio_action
            from app.services.brain.router import route
            from app.services.study import StudyResult
            intent = await route(db, owner_id=owner_id, context_id=session.context_id, message=content)
            if intent.capability == "audio.from_session":
                try:
                    action = await prepare_audio_action(db, owner_id=owner_id, session=session, action_id=assistant_id)
                    return StudyResult("I’ll create audio from this conversation.", [], False), action
                except ValidationError as exc:
                    return StudyResult(str(exc), [], False), None
            return await answer_question(db, owner_id=owner_id, context_id=session.context_id,
                question=content, session_id=session.id, style=style), None
        if key is not None:
            with idempotency.keep_claim_alive(db, owner_id=owner_id, scope=scope, key=key, claim_id=claim_id):
                result, action = await respond()
        else:
            result, action = await respond()
        from app.services.brain.actions import audit, view
        response = StudyMessageResponse(
            id=str(assistant_id), action=view(action) if action else None,
            session_id=str(session.id), content=result.content, fallback_used=result.fallback_used,
            depth=None if action else style.depth,
            sources=[SourceReference(resource_id=ref.resource_id, chunk_id=ref.chunk_id,
                                     title=ref.source_title, score=ref.score) for ref in result.sources],
        )
        def checkpoint():
            if action is not None:
                db.add(action)
                audit(db, action, "proposed")
            if key is not None:
                idempotency.stage_response(db, owner_id=owner_id, scope=scope, key=key,
                                           claim_id=claim_id, response=response.model_dump())
        persist_conversation_turn(
            db, owner_id=owner_id, session=session, user_content=content,
            assistant_content=result.content, assistant_refs=[ref.model_dump() for ref in response.sources],
            fallback_used=result.fallback_used, user_message_id=message_id,
            assistant_message_id=assistant_id, action={"id": str(action.id)} if action else None,
            response_depth=response.depth,
            before_commit=checkpoint,
        )
        return response
    except Exception:
        db.rollback()
        if key is not None:
            idempotency.release(db, owner_id=owner_id, scope=scope, key=key, claim_id=claim_id)
        raise


def _saved_action(db, owner_id, message):
    if not message.action:
        return None
    from app.services.brain.actions import get_status
    return get_status(db, owner_id=owner_id, action_id=message.id)
