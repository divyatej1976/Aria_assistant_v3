import hashlib
import random
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers import LiteLLMGroqProvider
from app.assessment.schema import MCQSet
from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.models import Resource, ResourceChunk
from app.services.concepts import chunk_ids_for_concepts, concept_id_for_chunk


@dataclass(frozen=True)
class GeneratedMCQ:
    prompt: str
    options: list[str]
    correct_option: str
    concept_id: UUID | None


def _sentences(content: str) -> list[str]:
    parts = content.replace("\n", " ").split(".")
    return [part.strip() for part in parts if len(part.strip()) > 20]


def _chunk_id_filter(
    db: Session, *, owner_id: UUID, concept_ids: list[str] | None
) -> set[UUID] | None:
    if not concept_ids:
        return None
    return chunk_ids_for_concepts(
        db, owner_id=owner_id, concept_ids=[UUID(value) for value in concept_ids]
    )


def _load_chunk_sentences(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    chunk_ids: set[UUID] | None = None,
) -> tuple[list[UUID], list[list[str]]]:
    query = (
        select(ResourceChunk, Resource)
        .join(Resource, Resource.id == ResourceChunk.resource_id)
        .where(
            ResourceChunk.owner_id == owner_id,
            Resource.owner_id == owner_id,
            Resource.context_id == context_id,
            Resource.processing_status == "READY",
        )
        .order_by(ResourceChunk.chunk_index)
    )
    if chunk_ids is not None:
        query = query.where(ResourceChunk.id.in_(chunk_ids))
    rows = db.execute(query).all()
    chunk_ids_out = [chunk.id for chunk, _resource in rows]
    sentences = [_sentences(chunk.content) for chunk, _resource in rows]
    return chunk_ids_out, sentences


def _stable_seed(all_sentences: list[str]) -> int:
    digest = hashlib.sha256("|".join(all_sentences).encode()).hexdigest()
    return int(digest[:8], 16)


def _pick_distractors(
    chunk_sentences: list[list[str]],
    all_sentences: list[str],
    correct: str,
    difficulty: str,
    rng: random.Random,
) -> list[str]:
    correct_chunk_index = next(
        index for index, group in enumerate(chunk_sentences) if correct in group
    )
    same_chunk = [
        sentence
        for sentence in chunk_sentences[correct_chunk_index]
        if sentence != correct
    ]
    other_chunks = [
        sentence
        for index, group in enumerate(chunk_sentences)
        if index != correct_chunk_index
        for sentence in group
    ]
    if difficulty == "hard":
        candidates = same_chunk + other_chunks
    elif difficulty == "easy":
        candidates = other_chunks
        if len(dict.fromkeys(candidates)) < 3:
            candidates = candidates + same_chunk
    else:
        candidates = other_chunks + same_chunk
    pool = list(dict.fromkeys(candidates))
    chosen: list[str] = []
    seen = {correct}
    while len(chosen) < 3 and pool:
        candidate = pool[rng.randrange(len(pool))]
        if candidate in seen:
            continue
        chosen.append(candidate)
        seen.add(candidate)
    if len(chosen) < 3:
        raise ValidationError(
            "Not enough distinct sentences in the material to build a quiz"
        )
    return chosen


def generate_mcqs_deterministic(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    count: int,
    difficulty: str,
    concept_ids: list[str] | None = None,
) -> list[GeneratedMCQ]:
    chunk_filter = _chunk_id_filter(db, owner_id=owner_id, concept_ids=concept_ids)
    chunk_ids, chunk_sentences = _load_chunk_sentences(
        db, owner_id=owner_id, context_id=context_id, chunk_ids=chunk_filter
    )
    all_pairs = [
        (chunk_ids[group_index], sentence)
        for group_index, group in enumerate(chunk_sentences)
        for sentence in group
    ]
    all_sentences = [sentence for _, sentence in all_pairs]
    if len(all_sentences) < 4:
        raise ValidationError(
            "Add more study material — at least four sentences are needed to build a quiz"
        )
    rng = random.Random(_stable_seed(all_sentences))
    rng.shuffle(all_pairs)
    questions: list[GeneratedMCQ] = []
    for index in range(count):
        chunk_id, correct = all_pairs[index % len(all_pairs)]
        options = [correct, *_pick_distractors(
            chunk_sentences, all_sentences, correct, difficulty, rng
        )]
        rng.shuffle(options)
        correct_letter = "ABCD"[options.index(correct)]
        concept_id = concept_id_for_chunk(db, owner_id=owner_id, chunk_id=chunk_id)
        questions.append(
            GeneratedMCQ(
                prompt=(
                    "According to the study material, which of the following statements "
                    "is correct?"
                ),
                options=options,
                correct_option=correct_letter,
                concept_id=concept_id,
            )
        )
    return questions


def _material_preview(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    chunk_ids: set[UUID] | None = None,
) -> str:
    query = (
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
    if chunk_ids is not None:
        query = query.where(ResourceChunk.id.in_(chunk_ids))
    rows = db.execute(query).scalars().all()
    return "\n\n".join(f"[{index + 1}] {chunk.content[:400]}" for index, chunk in enumerate(rows))


async def generate_mcqs_structured(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    count: int,
    difficulty: str,
    concept_ids: list[str] | None = None,
) -> list[GeneratedMCQ]:
    chunk_filter = _chunk_id_filter(db, owner_id=owner_id, concept_ids=concept_ids)
    material = _material_preview(
        db, owner_id=owner_id, context_id=context_id, chunk_ids=chunk_filter
    )
    if not material:
        raise ValidationError(
            "Add ready study material before creating an assessment"
        )
    settings = get_settings()
    provider = LiteLLMGroqProvider(api_key=settings.groq_api_key, model=settings.llm_model)
    prompt = (
        "Generate multiple-choice questions grounded only in the supplied study material. "
        "Each question must have exactly four distinct options and a correct_option letter "
        "of A, B, C, or D matching the correct option. Return JSON matching the schema:\n"
        '{"questions": [{"prompt": "...", "options": ["...", "...", "...", "..."], '
        '"correct_option": "A"}]}\n\n'
        f"Difficulty: {difficulty}. Produce {count} questions.\n\nStudy material:\n{material}"
    )
    parsed = await provider.generate_structured(prompt=prompt, schema=MCQSet)
    return [
        GeneratedMCQ(
            prompt=item.prompt,
            options=item.options,
            correct_option=item.correct_option,
            concept_id=None,
        )
        for item in parsed.questions[:count]
    ]
