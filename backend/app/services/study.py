import logging
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
    build_study_context,
    build_study_messages,  # noqa: F401  (re-exported for tests/consumers)
)
from app.services.contexts import get_owned_context
from app.services.learner_state import STATE_DEVELOPING, STATE_NEEDS_REVIEW
from app.services.text import bm25_scores, content_terms

logger = logging.getLogger(__name__)

WEAK_BOOST = 1.3


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
    db: Session, *, owner_id: UUID, context_id: UUID
) -> list[StudySession]:
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    return list(
        db.scalars(
            select(StudySession)
            .where(StudySession.owner_id == owner_id, StudySession.context_id == context_id)
            .order_by(StudySession.created_at)
        )
    )


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
    db: Session, *, owner_id: UUID, session_id: UUID
) -> list[ConversationMessage]:
    return list(
        db.scalars(
            select(ConversationMessage)
            .where(
                ConversationMessage.study_session_id == session_id,
                ConversationMessage.owner_id == owner_id,
            )
            .order_by(ConversationMessage.position, ConversationMessage.created_at)
        )
    )


def _next_position(db: Session, *, owner_id: UUID, session_id: UUID) -> int:
    message_count = db.scalar(
        select(func.count(ConversationMessage.id)).where(
            ConversationMessage.study_session_id == session_id,
            ConversationMessage.owner_id == owner_id,
        )
    )
    return (message_count or 0) + 1


def persist_conversation_turn(
    db: Session,
    *,
    owner_id: UUID,
    session: StudySession,
    user_content: str,
    assistant_content: str,
    assistant_refs: list[dict],
) -> None:
    from sqlalchemy.exc import IntegrityError

    for _attempt in range(3):
        user_position = _next_position(db, owner_id=owner_id, session_id=session.id)
        db.add(
            ConversationMessage(
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
                position=user_position + 1,
            )
        )
        try:
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

    boosts = weak_chunk_boosts(db, owner_id=owner_id, context_id=context_id)
    query_terms = {term for term in content_terms(query) if len(term) > 2}
    provider = get_embedding_provider()
    semantic = semantic_scoring_available(provider)
    query_embedding: list[float] | None = None
    if semantic:
        query_embedding = (await provider.embed([query]))[0]
        expected_dim = get_settings().aria_embedding_dim
        if len(query_embedding) != expected_dim:
            msg = f"Query embedding dimension {len(query_embedding)} != expected {expected_dim}"
            raise ValueError(msg)

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
            ).all()
            rows.extend(
                (chunk, resource) for chunk, resource in extra if chunk.id not in existing_ids
            )
        except Exception:
            rows = []
    if not rows:
        rows = db.execute(base.where(*filters)).all()

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
    context_text = build_study_context(sources)
    if not context_text:
        return StudyResult(
            content=(
                "I could not find enough relevant information in the selected material "
                "to answer that reliably."
            ),
            sources=sources,
            fallback_used=True,
        )
    if get_llm_provider_for_owner(db, owner_id=owner_id) is None:
        return StudyResult(
            content=(
                "Provider fallback: here are the most relevant excerpts from your material. "
                "Configure GROQ_API_KEY to enable generated explanations.\n\n" + context_text
            ),
            sources=sources,
            fallback_used=True,
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
        provider = get_llm_provider_for_owner(db, owner_id=owner_id)
        if provider is None:
            return StudyResult(
                content=(
                    "Provider fallback: here are the most relevant excerpts from your material. "
                    "Configure GROQ_API_KEY to enable generated explanations.\n\n" + context_text
                ),
                sources=sources,
                fallback_used=True,
            )
        answer = await provider.generate_text(
            system=system, user=user, prompt_version=get_prompt("study_answer").label()
        )
        if not answer or not answer.strip():
            logger.warning("study llm returned an empty response; serving fallback")
            return StudyResult(
                content=(
                    "The AI provider returned an empty response. Review the cited excerpts "
                    "and try again later."
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
                "The AI provider is temporarily unavailable. Review the cited excerpts "
                "and try again later."
            ),
            sources=sources,
            fallback_used=True,
        )
