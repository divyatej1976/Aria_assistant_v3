from collections import Counter
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.providers import LiteLLMGroqProvider
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
    settings = get_settings()
    provider = LiteLLMGroqProvider(api_key=settings.groq_api_key, model=settings.llm_model)
    prompt = (
        "Extract the most important learning concepts from the supplied study material. "
        'Return JSON matching the schema: {"concepts": ["concept one", "concept two"]}. '
        f"Produce up to {limit} concepts.\n\nStudy material:\n{material}"
    )
    parsed = await provider.generate_structured(prompt=prompt, schema=ConceptSet)
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
    row = db.execute(
        select(ConceptChunk.concept_id)
        .where(ConceptChunk.owner_id == owner_id, ConceptChunk.chunk_id == chunk_id)
        .order_by(ConceptChunk.concept_id)
        .limit(1)
    ).first()
    return row[0] if row else None
