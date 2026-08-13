from collections import Counter
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.prompts import get_prompt
from app.ai.registry import get_llm_provider
from app.assessment.schema import ConceptSet
from app.core.config import get_settings
from app.db.models import Concept, ConceptChunk, Resource, ResourceChunk
from app.services.text import tokenize


def context_chunks(db: Session, *, owner_id: UUID, context_id: UUID) -> list[ResourceChunk]:
    return list(
        db.scalars(
            select(ResourceChunk)
            .join(Resource, Resource.id == ResourceChunk.resource_id)
            .where(
                ResourceChunk.owner_id == owner_id,
                Resource.owner_id == owner_id,
                Resource.context_id == context_id,
                Resource.processing_status == "READY",
            )
            .order_by(ResourceChunk.chunk_index)
        )
    )


def extract_concepts_deterministic(
    chunks: list[ResourceChunk], *, limit: int = 10
) -> list[str]:
    token_counts: Counter[str] = Counter()
    chunk_presence: Counter[str] = Counter()
    for chunk in chunks:
        tokens = set(tokenize(chunk.content))
        for token in tokens:
            chunk_presence[token] += 1
        for token in tokens:
            token_counts[token] += 1
    scored: list[tuple[int, str]] = []
    for token, count in token_counts.items():
        if len(token) < 4:
            continue
        scored.append((count * (1 + chunk_presence[token]), token))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [token for _, token in scored[:limit]]


async def extract_concepts_structured(
    chunks: list[ResourceChunk], *, limit: int = 10
) -> list[str]:
    material = "\n\n".join(
        f"[{index + 1}] {chunk.content[:400]}" for index, chunk in enumerate(chunks)
    )
    provider = get_llm_provider()
    if provider is None:
        raise RuntimeError("LLM provider is not configured")
    prompt_version = get_prompt("concept_extraction")
    prompt = prompt_version.render(limit=limit, material=material)
    parsed = await provider.generate_structured(
        prompt=prompt, schema=ConceptSet, prompt_version=prompt_version.label()
    )
    return parsed.concepts[:limit]


async def sync_concepts(
    db: Session, *, owner_id: UUID, context_id: UUID, limit: int = 10
) -> list[Concept]:
    chunks = context_chunks(db, owner_id=owner_id, context_id=context_id)
    if not chunks:
        return []
    settings = get_settings()
    if settings.groq_api_key:
        try:
            names = await extract_concepts_structured(chunks, limit=limit)
        except Exception:
            names = extract_concepts_deterministic(chunks, limit=limit)
    else:
        names = extract_concepts_deterministic(chunks, limit=limit)
    concepts: list[Concept] = []
    for name in names:
        concept = db.scalar(
            select(Concept).where(
                Concept.owner_id == owner_id,
                Concept.context_id == context_id,
                Concept.name == name,
            )
        )
        if concept is None:
            concept = Concept(owner_id=owner_id, context_id=context_id, name=name)
            db.add(concept)
            db.flush()
        concepts.append(concept)
    chunk_ids = [chunk.id for chunk in chunks]
    db.execute(
        delete(ConceptChunk).where(
            ConceptChunk.owner_id == owner_id, ConceptChunk.chunk_id.in_(chunk_ids)
        )
    )
    for chunk in chunks:
        chunk_terms = set(tokenize(chunk.content))
        for concept in concepts:
            concept_terms = set(tokenize(concept.name))
            if concept_terms and concept_terms <= chunk_terms:
                db.add(
                    ConceptChunk(owner_id=owner_id, concept_id=concept.id, chunk_id=chunk.id)
                )
    db.commit()
    return concepts


def list_concepts(db: Session, *, owner_id: UUID, context_id: UUID) -> list[Concept]:
    return list(
        db.scalars(
            select(Concept)
            .where(Concept.owner_id == owner_id, Concept.context_id == context_id)
            .order_by(Concept.name)
        )
    )


def chunk_ids_for_concepts(
    db: Session, *, owner_id: UUID, concept_ids: list[UUID]
) -> set[UUID]:
    if not concept_ids:
        return set()
    rows = db.execute(
        select(ConceptChunk.chunk_id).where(
            ConceptChunk.owner_id == owner_id,
            ConceptChunk.concept_id.in_(concept_ids),
        )
    )
    return {row[0] for row in rows}


def concept_id_for_chunk(db: Session, *, owner_id: UUID, chunk_id: UUID) -> UUID | None:
    """Return the concept best represented by a chunk.

    The best concept is the one whose name occurs most often in the chunk
    content (deterministic), falling back to alphabetical order.
    """
    chunk = db.get(ResourceChunk, chunk_id)
    if chunk is None:
        return None
    rows = db.execute(
        select(Concept, ConceptChunk.concept_id)
        .join(ConceptChunk, ConceptChunk.concept_id == Concept.id)
        .where(ConceptChunk.owner_id == owner_id, ConceptChunk.chunk_id == chunk_id)
        .order_by(Concept.name)
    ).all()
    content_lower = chunk.content.lower()
    best: tuple[int, str, UUID] | None = None
    for concept, _relation_id in rows:
        frequency = content_lower.count(concept.name.lower())
        if best is None or (frequency, concept.name) > (best[0], best[1]):
            best = (frequency, concept.name, concept.id)
    return best[2] if best else None
