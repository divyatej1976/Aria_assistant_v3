"""Explicit end-of-day reviews, scoped to the learner's local day and subject."""

from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.models import Assessment, ConversationMessage, Resource, ResourceChunk, StudySession
from app.services.assessment import create_assessment
from app.services.concepts import concept_id_for_chunk, sync_concepts
from app.services.contexts import get_owned_context
from app.services.progress import learner_timezone
from app.services.study import SMALL_TALK_RE


async def finish_day(db: Session, *, owner_id: UUID, context_id: UUID) -> Assessment:
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    timezone = learner_timezone(db, owner_id=owner_id)
    day = datetime.now(timezone).date()
    key = day.isoformat()
    existing = db.scalar(select(Assessment).where(
        Assessment.owner_id == owner_id, Assessment.context_id == context_id,
        Assessment.daily_review_date == key,
    ))
    if existing is not None:
        return existing
    start = datetime.combine(day, time.min, tzinfo=timezone).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=timezone).astimezone(UTC)
    messages = list(db.scalars(select(ConversationMessage).join(
        StudySession, StudySession.id == ConversationMessage.study_session_id,
    ).where(
        ConversationMessage.owner_id == owner_id, StudySession.owner_id == owner_id,
        StudySession.context_id == context_id,
        ConversationMessage.created_at >= start, ConversationMessage.created_at < end,
    ).order_by(ConversationMessage.created_at.desc(), ConversationMessage.position.desc()).limit(1000)))
    learning_turn: dict[UUID, bool] = {}
    answers = []
    for message in reversed(messages):
        if message.role == "user":
            text = message.content.strip()
            learning_turn[message.study_session_id] = (
                any(character.isalnum() for character in text)
                and SMALL_TALK_RE.fullmatch(text) is None
            )
        elif message.role == "assistant" and learning_turn.get(message.study_session_id, False):
            answers.append(message)
    if not answers:
        raise ValidationError("Explore a topic with your tutor today before finishing your day.")
    transcript = "\n\n".join(message.content for message in answers)[-20_000:]
    if not transcript.strip():
        raise ValidationError("Wait for your tutor's reply before finishing your day.")
    # Only concepts backed by this day's owned, ready citations may affect mastery.
    concepts = set()
    if any(message.source_refs for message in answers):
        await sync_concepts(db, owner_id=owner_id, context_id=context_id)
    for message in answers:
        for ref in message.source_refs or []:
            try:
                chunk_id = UUID(str(ref.get("chunk_id")))
            except (ValueError, TypeError):
                continue
            chunk = db.scalar(select(ResourceChunk).join(Resource).where(
                ResourceChunk.id == chunk_id, ResourceChunk.owner_id == owner_id,
                Resource.owner_id == owner_id, Resource.context_id == context_id,
                Resource.processing_status == "READY",
            ))
            if chunk is not None:
                concept_id = concept_id_for_chunk(db, owner_id=owner_id, chunk_id=chunk.id)
                if concept_id is not None:
                    concepts.add(concept_id)
    return await create_assessment(
        db, owner_id=owner_id, context_id=context_id, format_name="mcq",
        question_count=5, difficulty="medium", mode="DAILY_REVIEW",
        concept_ids=list(concepts), study_transcript=transcript, daily_review_date=key,
    )
