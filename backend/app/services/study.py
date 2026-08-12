from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers import DeterministicEmbeddingProvider, LiteLLMGroqProvider, RetrievedChunk
from app.core.config import get_settings
from app.db.models import ConceptChunk, LearnerConceptState, Resource, ResourceChunk
from app.services.learner_state import STATE_DEVELOPING, STATE_NEEDS_REVIEW
from app.services.text import content_terms

WEAK_BOOST = 1.3

STUDY_SYSTEM_PROMPT = "Answer only from the supplied study material. If it is insufficient, say so."


def build_study_context(
    sources: list[RetrievedChunk], *, max_chars: int = 4000
) -> str:
    """Render source chunks as data-only context, capped at max_chars.

    Resource text is always treated as untrusted data: it never reaches the
    system instruction.
    """
    parts: list[str] = []
    used = 0
    for source in sources:
        if source.score <= 0:
            continue
        block = f"[{source.source_title}] {source.content}"
        if used + len(block) > max_chars:
            remaining = max_chars - used
            if remaining > 0:
                parts.append(block[:remaining])
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


def build_study_messages(*, question: str, context_text: str) -> tuple[str, str]:
    """Build (system, user) prompt messages.

    The system instruction is a constant; the learner question and the source
    material are placed only in the user message.
    """
    return STUDY_SYSTEM_PROMPT, f"Study material:\n{context_text}\n\nLearner question: {question}"


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
    return not isinstance(provider, DeterministicEmbeddingProvider)


def weak_chunk_boosts(db: Session, *, owner_id: UUID, context_id: UUID) -> dict[str, float]:
    rows = db.execute(
        select(ConceptChunk.chunk_id, LearnerConceptState.state)
        .join(LearnerConceptState, LearnerConceptState.concept_id == ConceptChunk.concept_id)
        .where(
            ConceptChunk.owner_id == owner_id,
            LearnerConceptState.owner_id == owner_id,
        )
    ).all()
    boosts: dict[str, float] = {}
    for chunk_id, state in rows:
        if state in (STATE_NEEDS_REVIEW, STATE_DEVELOPING):
            boosts[str(chunk_id)] = WEAK_BOOST
    return boosts


async def retrieve_chunks(
    db: Session, *, owner_id: UUID, context_id: UUID, query: str
) -> list[RetrievedChunk]:
    rows = db.execute(
        select(ResourceChunk, Resource)
        .join(Resource, Resource.id == ResourceChunk.resource_id)
        .where(
            ResourceChunk.owner_id == owner_id,
            Resource.owner_id == owner_id,
            Resource.context_id == context_id,
            Resource.processing_status == "READY",
        )
    ).all()
    boosts = weak_chunk_boosts(db, owner_id=owner_id, context_id=context_id)
    query_terms = {term for term in content_terms(query) if len(term) > 2}
    provider = DeterministicEmbeddingProvider()
    semantic = semantic_scoring_available(provider)
    query_embedding = (await provider.embed([query]))[0] if semantic else None
    scored: list[RetrievedChunk] = []
    for chunk, resource in rows:
        lexical = lexical_score(query_terms, chunk.content)
        if semantic:
            similarity = cosine_similarity(query_embedding, chunk.embedding_json or [])
            score = 0.5 * lexical + 0.5 * similarity
        else:
            score = lexical
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
    return sorted(scored, key=lambda item: item.score, reverse=True)[:5]


async def answer_question(
    db: Session, *, owner_id: UUID, context_id: UUID, question: str
) -> StudyResult:
    sources = await retrieve_chunks(db, owner_id=owner_id, context_id=context_id, query=question)
    settings = get_settings()
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
    if not settings.groq_api_key:
        return StudyResult(
            content=(
                "Provider fallback: here are the most relevant excerpts from your material. "
                "Configure GROQ_API_KEY to enable generated explanations.\n\n" + context_text
            ),
            sources=sources,
            fallback_used=True,
        )
    try:
        system, user = build_study_messages(question=question, context_text=context_text)
        answer = await LiteLLMGroqProvider(
            api_key=settings.groq_api_key, model=settings.llm_model
        ).generate_text(system=system, user=user)
        return StudyResult(content=answer, sources=sources, fallback_used=False)
    except Exception:
        return StudyResult(
            content=(
                "The AI provider is temporarily unavailable. Review the cited excerpts "
                "and try again later."
            ),
            sources=sources,
            fallback_used=True,
        )
