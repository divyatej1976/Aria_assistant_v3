import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.prompts import get_prompt
from app.ai.providers import DeterministicEmbeddingProvider, RetrievedChunk
from app.ai.registry import (
    get_embedding_provider,
    get_llm_provider,  # noqa: F401  (kept for backwards-compat monkeypatch targets)
    get_llm_provider_for_owner,
)
from app.core.errors import ValidationError
from app.db.models import (
    Concept,
    ConceptChunk,
    ConversationMessage,
    LearnerConceptState,
    Resource,
    ResourceChunk,
    StudySession,
)
from app.services.context_assembly import (
    STUDY_SYSTEM_PROMPT,  # noqa: F401  (re-exported for tests/consumers)
    assemble_context,
    build_prompt,
    build_study_context,  # noqa: F401  (re-exported for tests/consumers)
    build_study_messages,  # noqa: F401  (re-exported for tests/consumers)
    pack_study_context,
)
from app.services.contexts import get_owned_context
from app.services.learner_state import STATE_DEVELOPING, STATE_NEEDS_REVIEW
from app.services.text import bm25_scores, content_terms

logger = logging.getLogger(__name__)

WEAK_BOOST = 1.3

# Pure small-talk (no study content): greetings never match material chunks,
# so without this they die in retrieval with a confusing "no relevant
# information" reply. Anchored to the full message so "hi, explain functions"
# still takes the normal RAG path.
SMALL_TALK_RE = re.compile(
    r"^(hi( there)?|hii+|hello( there)?|hey( there)?|yo|howdy|greetings"
    r"|good\s?(morning|afternoon|evening|day)"
    r"|how are you|what'?s up|thank(s| you)( very much)?|thanks a lot"
    r"|bye|goodbye|good ?night|see you( later)?|who are you)[!.,\s]*$",
    re.IGNORECASE,
)

DETERMINISTIC_GREETING = (
    "Hi there! I'm ARIA, your learning companion. "
    "Ask me anything about your study material and I'll do my best to help."
)


def create_session(
    db: Session, *, owner_id: UUID, context_id: UUID, mode: str
) -> StudySession:
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    session = StudySession(owner_id=owner_id, context_id=context_id, mode=mode)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(
    db: Session, *, owner_id: UUID, context_id: UUID, limit: int = 100, offset: int = 0
) -> list[StudySession]:
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    return list(
        db.scalars(
            select(StudySession)
            .where(StudySession.owner_id == owner_id, StudySession.context_id == context_id)
            .order_by(StudySession.created_at.desc(), StudySession.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )


@dataclass(frozen=True)
class SessionSummary:
    title: str | None
    preview: str | None
    message_count: int
    last_message_at: object | None


_MARKDOWN_RE = re.compile(r"[*_`#>\[\]]+|\(https?://[^)]*\)")


def _plain_snippet(text: str, limit: int) -> str:
    """Collapse markdown/whitespace and trim to a word boundary."""
    flat = " ".join(_MARKDOWN_RE.sub("", text).split())
    if len(flat) <= limit:
        return flat
    cut = flat[:limit].rsplit(" ", 1)[0].rstrip(",.;:-")
    return cut + "…"


def _first_sentence(text: str) -> str:
    flat = " ".join(_MARKDOWN_RE.sub("", text).split())
    match = re.search(r"(.+?[.!?])(\s|$)", flat)
    return match.group(1) if match else flat


def session_summaries(
    db: Session, *, owner_id: UUID, session_ids: list[UUID]
) -> dict[UUID, SessionSummary]:
    """Title (first learner question), preview (gist of the latest tutor reply),
    count and recency per session, derived from stored messages."""
    if not session_ids:
        return {}
    scope = (
        ConversationMessage.owner_id == owner_id,
        ConversationMessage.study_session_id.in_(session_ids),
    )
    stats = {
        sid: (count, last_at)
        for sid, count, last_at in db.execute(
            select(
                ConversationMessage.study_session_id,
                func.count(ConversationMessage.id),
                func.max(ConversationMessage.created_at),
            )
            .where(*scope)
            .group_by(ConversationMessage.study_session_id)
        )
    }

    def edge_messages(role: str, edge) -> dict[UUID, str]:
        positions = (
            select(
                ConversationMessage.study_session_id.label("sid"),
                edge(ConversationMessage.position).label("pos"),
            )
            .where(*scope, ConversationMessage.role == role)
            .group_by(ConversationMessage.study_session_id)
            .subquery()
        )
        rows = db.execute(
            select(ConversationMessage.study_session_id, ConversationMessage.content).join(
                positions,
                (ConversationMessage.study_session_id == positions.c.sid)
                & (ConversationMessage.position == positions.c.pos),
            )
        )
        return {sid: content for sid, content in rows}

    first_questions = edge_messages("user", func.min)
    latest_replies = edge_messages("assistant", func.max)
    summaries: dict[UUID, SessionSummary] = {}
    for sid in session_ids:
        count, last_at = stats.get(sid, (0, None))
        question = first_questions.get(sid)
        reply = latest_replies.get(sid)
        summaries[sid] = SessionSummary(
            title=_plain_snippet(question, 60) if question else None,
            preview=_plain_snippet(_first_sentence(reply), 110) if reply else None,
            message_count=count,
            last_message_at=last_at,
        )
    return summaries


def get_owned_session(
    db: Session,
    *,
    owner_id: UUID,
    session_id: UUID,
    context_id: UUID | None = None,
) -> StudySession:
    query = select(StudySession).where(
        StudySession.id == session_id, StudySession.owner_id == owner_id
    )
    if context_id is not None:
        query = query.where(StudySession.context_id == context_id)
    session = db.scalar(query)
    if session is None:
        raise ValidationError("Study session not found")
    return session



def delete_session(db: Session, *, owner_id: UUID, session_id: UUID) -> bool:
    """Delete a study session and its messages (owner-scoped)."""
    session = get_owned_session(db, owner_id=owner_id, session_id=session_id)
    if session is None:
        return False
    db.query(ConversationMessage).filter(
        ConversationMessage.study_session_id == session.id,
        ConversationMessage.owner_id == owner_id,
    ).delete(synchronize_session=False)
    db.delete(session)
    db.commit()
    return True

def list_messages(
    db: Session, *, owner_id: UUID, session_id: UUID, limit: int = 200,
    before_position: int | None = None,
) -> list[ConversationMessage]:
    query = select(ConversationMessage).where(
        ConversationMessage.study_session_id == session_id,
        ConversationMessage.owner_id == owner_id,
    )
    if before_position is not None:
        query = query.where(ConversationMessage.position < before_position)
    rows = list(db.scalars(query.order_by(
        ConversationMessage.position.desc(), ConversationMessage.created_at.desc()
    ).limit(limit)))
    return list(reversed(rows))


def _next_position(db: Session, *, owner_id: UUID, session_id: UUID) -> int:
    last_position = db.scalar(
        select(func.max(ConversationMessage.position)).where(
            ConversationMessage.study_session_id == session_id,
            ConversationMessage.owner_id == owner_id,
        )
    )
    return (last_position or 0) + 1


def persist_conversation_turn(
    db: Session,
    *,
    owner_id: UUID,
    session: StudySession,
    user_content: str,
    assistant_content: str,
    assistant_refs: list[dict],
    fallback_used: bool | None = None,
    user_message_id: UUID | None = None,
    before_commit: Callable[[], None] | None = None,
) -> None:
    from sqlalchemy.exc import IntegrityError

    for _attempt in range(3):
        user_position = _next_position(db, owner_id=owner_id, session_id=session.id)
        db.add(
            ConversationMessage(
                **({"id": user_message_id} if user_message_id is not None else {}),
                owner_id=owner_id,
                study_session_id=session.id,
                role="user",
                content=user_content,
                position=user_position,
            )
        )
        db.add(
            ConversationMessage(
                owner_id=owner_id,
                study_session_id=session.id,
                role="assistant",
                content=assistant_content,
                source_refs=assistant_refs,
                fallback_used=fallback_used,
                position=user_position + 1,
            )
        )
        try:
            if before_commit is not None:
                before_commit()
            db.commit()
            return
        except IntegrityError:
            db.rollback()
    raise RuntimeError("Could not persist conversation turn after concurrent retries")


@dataclass(frozen=True)
class StudyResult:
    content: str
    sources: list[RetrievedChunk]
    fallback_used: bool


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    magnitude_a = sum(x * x for x in a) ** 0.5
    magnitude_b = sum(y * y for y in b) ** 0.5
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot / (magnitude_a * magnitude_b)


def lexical_score(query_terms: set[str], content: str) -> float:
    terms = content_terms(content)
    return len(query_terms & terms) / max(len(query_terms), 1)


def semantic_scoring_available(provider: object) -> bool:
    """Deterministic provider is test-stable (SHA256 hashing) not semantic.

    Semantic scoring + pgvector HNSW require a cloud embedding provider.
    When this returns False, retrieval falls back to lexical scoring +
    weak-concept boosts only.
    """
    return not isinstance(provider, DeterministicEmbeddingProvider)


def weak_chunk_boosts(db: Session, *, owner_id: UUID, context_id: UUID) -> dict[str, float]:
    rows = db.execute(
        select(ConceptChunk.chunk_id, LearnerConceptState.state)
        .join(LearnerConceptState, LearnerConceptState.concept_id == ConceptChunk.concept_id)
        .join(Concept, Concept.id == ConceptChunk.concept_id)
        .where(
            ConceptChunk.owner_id == owner_id,
            LearnerConceptState.owner_id == owner_id,
            Concept.owner_id == owner_id,
            Concept.context_id == context_id,
        )
    ).all()
    boosts: dict[str, float] = {}
    for chunk_id, state in rows:
        if state in (STATE_NEEDS_REVIEW, STATE_DEVELOPING):
            boosts[str(chunk_id)] = WEAK_BOOST
    return boosts


def _dedupe_chunks(scored: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Drop near-duplicate chunks (same normalized prefix), keeping the
    higher-scored copy so top-5 slots carry distinct material."""
    seen: set[str] = set()
    kept: list[RetrievedChunk] = []
    for item in sorted(scored, key=lambda c: c.score, reverse=True):
        key = " ".join(item.content.lower().split())[:200]
        if key in seen:
            continue
        seen.add(key)
        kept.append(item)
    return kept


async def retrieve_chunks(
    db: Session, *, owner_id: UUID, context_id: UUID, query: str
) -> list[RetrievedChunk]:
    from app.core.config import get_settings

    # General tutoring needs no embeddings when this subject has no ready notes.
    available_chunk = db.scalar(
        select(ResourceChunk.id)
        .join(Resource, Resource.id == ResourceChunk.resource_id)
        .where(
            ResourceChunk.owner_id == owner_id,
            Resource.owner_id == owner_id,
            Resource.context_id == context_id,
            Resource.processing_status == "READY",
        )
        .limit(1)
    )
    if available_chunk is None:
        return []

    boosts = weak_chunk_boosts(db, owner_id=owner_id, context_id=context_id)
    query_terms = {term for term in content_terms(query) if len(term) > 2}
    provider = get_embedding_provider()
    semantic = semantic_scoring_available(provider)
    query_embedding: list[float] | None = None
    if semantic:
        try:
            query_embedding = (await provider.embed([query]))[0]
            expected_dim = get_settings().aria_embedding_dim
            if len(query_embedding) != expected_dim:
                raise ValueError("Unexpected query embedding dimension")
        except Exception:
            # Embeddings are optional: preserve subject-scoped lexical grounding
            # and let a healthy text provider continue tutoring.
            logger.warning("study embeddings unavailable; using lexical retrieval")
            semantic = False
            query_embedding = None

    base = select(ResourceChunk, Resource).join(
        Resource, Resource.id == ResourceChunk.resource_id
    )
    filters = [
        ResourceChunk.owner_id == owner_id,
        Resource.owner_id == owner_id,
        Resource.context_id == context_id,
        Resource.processing_status == "READY",
    ]

    rows: list = []
    bind = db.get_bind()
    if (
        bind is not None
        and bind.dialect.name == "postgresql"
        and semantic
        and query_embedding is not None
    ):
        # pgvector HNSW narrows candidates on Postgres with cloud embeddings;
        # non-embedded READY chunks are still included so no material is
        # silently ignored. Any pgvector failure falls through to a full scan.
        # KNOWN PARITY NOTE: the HNSW top-20 pre-cut happens before weak-concept
        # boosts are applied, so a weak-boosted chunk outside the raw top-20
        # cannot be rescued here (the Python path scores all chunks). The same
        # query may therefore rank slightly differently on Postgres vs SQLite.
        # Acceptable while semantic retrieval is optional; revisit if boosts
        # become a product-critical signal on Postgres deployments.
        try:
            rows = list(
                db.execute(
                    base.where(*filters, ResourceChunk.embedding.is_not(None))
                    .order_by(ResourceChunk.embedding.cosine_distance(query_embedding))  # type: ignore[attr-defined]
                    .limit(20)
                ).all()
            )
            existing_ids = {chunk.id for chunk, _ in rows}
            extra = db.execute(
                base.where(*filters, ResourceChunk.embedding.is_(None))
                .order_by(ResourceChunk.created_at.desc())
                .limit(500)
            ).all()
            rows.extend(
                (chunk, resource) for chunk, resource in extra if chunk.id not in existing_ids
            )
        except Exception:
            rows = []
    if not rows:
        rows = db.execute(
            base.where(*filters).order_by(ResourceChunk.created_at.desc()).limit(500)
        ).all()

    # BM25 IDF weighting replaces naive set overlap: rare matching terms now
    # dominate common ones (see app.services.text.bm25_scores).
    bm25 = bm25_scores(query_terms, [chunk.content for chunk, _ in rows])
    scored: list[RetrievedChunk] = []
    for (chunk, resource), bm in zip(rows, bm25, strict=True):
        if semantic and query_embedding is not None:
            pg_emb = getattr(chunk, "embedding", None)
            emb = pg_emb if pg_emb is not None else chunk.embedding_json or []  # type: ignore[assignment]
            similarity = cosine_similarity(query_embedding, emb)
            score = 0.5 * bm + 0.5 * similarity
        else:
            score = bm
        score *= boosts.get(str(chunk.id), 1.0)
        scored.append(
            RetrievedChunk(
                chunk_id=str(chunk.id),
                resource_id=str(resource.id),
                content=chunk.content,
                source_title=resource.title,
                score=score,
            )
        )
    return _dedupe_chunks(scored)[:5]


async def _answer_small_talk(
    db: Session, *, owner_id: UUID, question: str, sources: list
) -> StudyResult:
    """Greetings need no retrieval context: answer conversationally.

    With a provider, greet via the LLM (fallback_used=False). Without one
    (or on any provider failure), serve a friendly deterministic greeting
    instead of the "no relevant information" dead end.
    """
    provider = get_llm_provider_for_owner(db, owner_id=owner_id)
    if provider is None:
        return StudyResult(
            content=DETERMINISTIC_GREETING, sources=sources, fallback_used=True
        )
    try:
        answer = await provider.generate_text(
            system=(
                "You are ARIA, a friendly AI learning tutor. "
                "Greet the learner briefly and invite them to ask about "
                "their study material."
            ),
            user=question,
            prompt_version="study_greeting:1",
        )
    except Exception:
        logger.exception("study greeting call failed; serving deterministic greeting")
        return StudyResult(
            content=DETERMINISTIC_GREETING, sources=sources, fallback_used=True
        )
    if not answer or not answer.strip():
        return StudyResult(
            content=DETERMINISTIC_GREETING, sources=sources, fallback_used=True
        )
    return StudyResult(content=answer, sources=sources, fallback_used=False)


async def answer_question(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    question: str,
    session_id: UUID | None = None,
) -> StudyResult:
    try:
        sources = await retrieve_chunks(db, owner_id=owner_id, context_id=context_id, query=question)
    except Exception:
        # Retrieval (e.g., embedding endpoint) failed: safe fallback, no leakage.
        logger.exception("study retrieval failed; serving fallback")
        return StudyResult(
            content=(
                "The AI provider is temporarily unavailable. Review the cited excerpts "
                "and try again later."
            ),
            sources=[],
            fallback_used=True,
        )
    provider = get_llm_provider_for_owner(db, owner_id=owner_id)
    context_text, sources = pack_study_context(
        sources, per_chunk=1200 if provider is not None else None
    )

    # When no LLM provider is configured (offline mode / missing key):
    if provider is None:
        if not context_text:
            if SMALL_TALK_RE.match(question.strip()):
                return await _answer_small_talk(
                    db, owner_id=owner_id, question=question, sources=sources
                )
            return StudyResult(
                content=(
                    "I can answer without uploaded notes, but no usable LLM API key "
                    "is configured. Add your Groq API key in Account settings, or ask "
                    "the deployment administrator to configure GROQ_API_KEY. "
                    "If you already saved a key, the administrator should check "
                    "the personal-key encryption configuration."
                ),
                sources=sources,
                fallback_used=True,
            )
        return StudyResult(
            content=(
                "Provider fallback: here are the most relevant excerpts from your material. "
                "Configure GROQ_API_KEY to enable generated explanations.\n\n" + context_text
            ),
            sources=sources,
            fallback_used=True,
        )

    # When LLM provider is active (conversational mode like ChatGPT/Gemini):
    if not context_text and SMALL_TALK_RE.match(question.strip()):
        return await _answer_small_talk(
            db, owner_id=owner_id, question=question, sources=sources
        )

    try:
        package = assemble_context(
            db,
            owner_id=owner_id,
            context_id=context_id,
            session_id=session_id,
            sources=sources,
        )
        system, user = build_prompt(question, package)
        try:
            answer = await provider.generate_text(
                system=system,
                user=user,
                prompt_version=get_prompt("study_answer").label(),
                temperature=0.0,
            )
        except TypeError:
            answer = await provider.generate_text(
                system=system, user=user, prompt_version=get_prompt("study_answer").label()
            )
        if not answer or not answer.strip():
            logger.warning("study llm returned an empty response; serving fallback")
            return StudyResult(
                content=(
                    "The AI provider returned an empty response. "
                    + ("Review the cited excerpts and try again later." if sources else "Please try asking again.")
                ),
                sources=sources,
                fallback_used=True,
            )
        return StudyResult(content=answer, sources=sources, fallback_used=False)
    except Exception:
        # Intentionally generic on the wire: never echo provider errors, keys,
        # or prompts. The full exception goes to server logs only.
        logger.exception("study llm call failed; serving fallback")
        return StudyResult(
            content=(
                "The AI provider is temporarily unavailable. "
                + ("Review the cited excerpts and try again later." if sources else "Please try again later.")
            ),
            sources=sources,
            fallback_used=True,
        )
