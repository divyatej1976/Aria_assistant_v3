import hashlib
import json
import re
from collections import Counter
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.prompts import get_prompt
from app.ai.registry import get_llm_provider_for_owner
from app.assessment.schema import ConceptSet
from app.core.errors import ValidationError
from app.db.models import Concept, ConceptChunk, Resource, ResourceChunk
from app.services.contexts import get_owned_context
from app.services.text import STOPWORDS, tokenize

CONCEPT_MATERIAL_CHAR_LIMIT = 12_000
CONCEPT_PROMPT_CHAR_LIMIT = 16_000


def _concept_material(chunks: list[ResourceChunk]) -> str:
    excerpts = []
    used = 0
    for index, chunk in enumerate(chunks):
        text = chunk.content[:400].strip()
        if not text:
            continue
        prefix = f"[{index + 1}] "
        separator = 2 if excerpts else 0
        remaining = CONCEPT_MATERIAL_CHAR_LIMIT - used - separator - len(prefix)
        if remaining <= 0:
            break
        excerpt = prefix + text[:remaining]
        excerpts.append(excerpt)
        used += separator + len(excerpt)
    return "\n\n".join(excerpts)


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
            .order_by(ResourceChunk.resource_id, ResourceChunk.chunk_index, ResourceChunk.id)
            .execution_options(populate_existing=True)
        )
    )


# Words that break a candidate phrase: function words plus the verbs and
# fillers that glue study prose together ("A tuple *is* an ordered sequence
# *written with* parentheses"). Splitting on them leaves the noun phrases.
_PHRASE_BREAKS = STOPWORDS | {
    "also", "all", "any", "both", "each", "every", "other", "more", "most", "some", "such",
    "only", "same", "own", "one", "two", "three", "first", "second", "last", "many", "much",
    "their", "they", "them", "you", "your", "we", "our", "us", "he", "she", "his", "her",
    "if", "else", "there", "here", "where", "between", "within", "without", "across", "after",
    "before", "during", "through", "up", "down", "out", "off", "again", "once", "per", "via",
    "like", "inside", "outside", "often", "usually", "always", "never", "early", "next",
    "visible", "true", "false", "written", "taken", "known", "made", "given", "done", "gone",
    "form", "forms", "map", "maps", "pair", "pairs", "document", "documents",
}
# Connective verbs in study prose. Each expands to its -s/-ed/-ing forms;
# verbs that double as common nouns ("lock", "set", "list") are left out.
_CONNECTIVE_VERBS = (
    "absorb", "add", "allow", "apply", "assign", "avoid", "become", "belong", "build", "call", "change",
    "check", "choose", "collect", "combine", "compare", "compute", "consider", "contain",
    "convert", "create", "decide", "define", "depend", "describe", "determine", "differ",
    "enable", "ensure", "evaluate", "execute", "exit", "explain", "express", "extend", "find", "fix",
    "follow", "generate", "get", "give", "guarantee", "group", "handle", "happen", "help",
    "hold", "identify", "implement", "improve", "include", "increase", "indicate", "involve",
    "iterate", "keep", "lead", "let", "live", "look", "make", "match", "mean", "measure",
    "modify", "move", "need", "occur", "pass", "perform", "point", "preserve", "prevent",
    "produce", "provide", "read", "receive", "reduce", "refer", "relate", "release", "remain", "remove",
    "repeat", "replace", "represent", "require", "return", "run", "save", "say", "see", "seem",
    "select", "send", "share", "show", "skip", "solve", "specify", "split", "start", "stay",
    "stop", "store", "support", "take", "tell", "tend", "try", "turn", "update", "use", "vary",
    "wait", "want", "work", "write", "yield",
)


def _verb_forms(base: str) -> set[str]:
    stem = base[:-1] if base.endswith("e") else base
    third = base + ("es" if base.endswith(("s", "sh", "ch", "x")) else "s")
    if base.endswith("y") and base[-2:-1] not in "aeiou":
        third, past = base[:-1] + "ies", base[:-1] + "ied"
    else:
        past = base + "d" if base.endswith("e") else base + "ed"
    return {base, third, past, stem + "ing"}


_PHRASE_BREAKS |= {form for verb in _CONNECTIVE_VERBS for form in _verb_forms(verb)}
# Never a concept on its own, though fine inside a longer phrase.
_GENERIC = {
    "value", "values", "item", "items", "thing", "things", "way", "ways", "part", "parts",
    "name", "names", "example", "examples", "number", "kind", "type", "types", "case", "cases",
    "level", "step", "steps", "time", "times", "idea", "ideas", "lot", "learning",
    "code", "data", "information", "result", "results", "fact", "facts",
}
_FRAGMENT_SPLIT = re.compile(r"[.,;:!?()\[\]{}\"'`\n\r\t]+")
_WORD = re.compile(r"[a-z][a-z0-9_]*(?:-[a-z0-9]+)*")
_MAX_PHRASE_WORDS = 3


def _candidate_phrases(text: str) -> list[tuple[str, ...]]:
    phrases: list[tuple[str, ...]] = []
    for fragment in _FRAGMENT_SPLIT.split(text.lower()):
        current: list[str] = []
        for word in _WORD.findall(fragment):
            if word in _PHRASE_BREAKS:
                if current:
                    phrases.append(tuple(current))
                current = []
            else:
                current.append(word)
        if current:
            phrases.append(tuple(current))
    usable = []
    for words in phrases:
        if len(words) > _MAX_PHRASE_WORDS:
            continue  # run-on fragments are clauses, not concepts
        if len(words) == 1 and (len(words[0]) < 4 or words[0] in _GENERIC):
            continue
        usable.append(words)
    return usable


def extract_concepts_deterministic(
    chunks: list[ResourceChunk], *, limit: int = 10
) -> list[str]:
    """Key-phrase extraction used when no LLM is available.

    Candidates are the noun-phrase-like runs left after splitting on
    punctuation, function words and connective verbs. A phrase scores by how
    often it occurs, how many chunks mention it, and its length (multi-word
    terms such as "list comprehensions" are more specific than "list").
    Ties break alphabetically so results are deterministic.
    """
    phrase_counts: Counter[tuple[str, ...]] = Counter()
    phrase_chunks: Counter[tuple[str, ...]] = Counter()
    for chunk in chunks:
        found = _candidate_phrases(chunk.content)
        phrase_counts.update(found)
        phrase_chunks.update(set(found))
    scored: list[tuple[float, str]] = []
    for words, count in phrase_counts.items():
        specificity = 1 + 0.6 * (len(words) - 1)
        score = (count + phrase_chunks[words]) * specificity
        scored.append((score, " ".join(words)))
    scored.sort(key=lambda item: (-item[0], item[1]))
    chosen: list[str] = []
    seen_stems: set[tuple[str, ...]] = set()
    for _, phrase in scored:
        stem = tuple(word.rstrip("s") for word in phrase.split())
        if stem in seen_stems:
            continue  # "loop" vs "loops": keep the stronger form only
        seen_stems.add(stem)
        chosen.append(phrase)
        if len(chosen) == limit:
            break
    return chosen


async def extract_concepts_structured(
    chunks: list[ResourceChunk],
    *,
    limit: int = 10,
    db=None,
    owner_id=None,
) -> list[str]:
    material = _concept_material(chunks)
    if db is not None and owner_id is not None:
        provider = get_llm_provider_for_owner(db, owner_id=owner_id)
    else:
        from app.ai.registry import get_llm_provider

        provider = get_llm_provider()
    if provider is None:
        raise RuntimeError("LLM provider is not configured")
    prompt_version = get_prompt("concept_extraction")
    prompt = prompt_version.render(limit=limit, material=material)
    if len(prompt) > CONCEPT_PROMPT_CHAR_LIMIT:
        raise ValueError("Concept extraction prompt exceeds its budget")
    parsed = await provider.generate_structured(
        prompt=prompt, schema=ConceptSet, prompt_version=prompt_version.label()
    )
    return parsed.concepts[:limit]


async def sync_concepts(
    db: Session, *, owner_id: UUID, context_id: UUID, limit: int = 10
) -> list[Concept]:
    context = get_owned_context(db, owner_id=owner_id, context_id=context_id)
    chunks = context_chunks(db, owner_id=owner_id, context_id=context_id)
    if not chunks:
        return []
    source_version = [(str(chunk.id), chunk.content) for chunk in chunks]
    provider = get_llm_provider_for_owner(db, owner_id=owner_id)
    prompt = get_prompt("concept_extraction")
    signature = hashlib.sha256(json.dumps({
        "algorithm": 1, "limit": limit,
        "prompt": prompt.render(limit=limit, material=_concept_material(chunks)),
        "prompt_version": prompt.label(),
        "provider": type(provider).__qualname__ if provider is not None else "deterministic",
        "model": getattr(provider, "model", None),
        "chunks": [(str(chunk.id), chunk.content) for chunk in chunks],
    }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    cached = context.concept_sync_names
    if (context.concept_sync_fingerprint == signature and isinstance(cached, list)
            and all(isinstance(name, str) for name in cached)):
        cached_rows = {concept.name: concept for concept in db.scalars(select(Concept).where(
            Concept.owner_id == owner_id, Concept.context_id == context_id, Concept.name.in_(cached),
        ))}
        if all(name in cached_rows for name in cached):
            return [cached_rows[name] for name in cached]
    cacheable = True
    if provider is not None:
        try:
            names = await extract_concepts_structured(
                chunks, limit=limit, db=db, owner_id=owner_id
            )
        except Exception:
            cacheable = False
            names = extract_concepts_deterministic(chunks, limit=limit)
    else:
        names = extract_concepts_deterministic(chunks, limit=limit)
    current_chunks = context_chunks(db, owner_id=owner_id, context_id=context_id)
    if [(str(chunk.id), chunk.content) for chunk in current_chunks] != source_version:
        raise ValidationError("Study material changed during concept extraction. Please retry.")
    names = list(dict.fromkeys(names))
    existing = {concept.name: concept for concept in db.scalars(
        select(Concept).where(
            Concept.owner_id == owner_id, Concept.context_id == context_id,
            Concept.name.in_(names),
        )
    )}
    concepts: list[Concept] = []
    for name in names:
        concept = existing.get(name)
        if concept is None:
            concept = Concept(owner_id=owner_id, context_id=context_id, name=name)
            db.add(concept)
        concepts.append(concept)
    db.flush()
    chunk_ids = [chunk.id for chunk in chunks]
    db.execute(
        delete(ConceptChunk).where(
            ConceptChunk.owner_id == owner_id, ConceptChunk.chunk_id.in_(chunk_ids)
        )
    )
    concept_terms_by_id = {concept.id: set(tokenize(concept.name)) for concept in concepts}
    for chunk in chunks:
        chunk_terms = set(tokenize(chunk.content))
        for concept in concepts:
            concept_terms = concept_terms_by_id[concept.id]
            if concept_terms and concept_terms <= chunk_terms:
                db.add(
                    ConceptChunk(owner_id=owner_id, concept_id=concept.id, chunk_id=chunk.id)
                )
    context.concept_sync_fingerprint = signature if cacheable else None
    context.concept_sync_names = names if cacheable else None
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


def concept_id_for_chunk(
    db: Session,
    *,
    owner_id: UUID,
    chunk_id: UUID,
    concept_ids: list[UUID | str] | None = None,
) -> UUID | None:
    """Return the concept best represented by a chunk.

    The best concept is the one whose name occurs most often in the chunk
    content, with a deterministic name tie breaker. When concept_ids is supplied,
    only linked concepts in that requested scope can receive the evidence.
    """
    chunk = db.scalar(
        select(ResourceChunk).where(
            ResourceChunk.id == chunk_id, ResourceChunk.owner_id == owner_id
        )
    )
    if chunk is None:
        return None
    query = (
        select(Concept, ConceptChunk.concept_id)
        .join(ConceptChunk, ConceptChunk.concept_id == Concept.id)
        .where(ConceptChunk.owner_id == owner_id, ConceptChunk.chunk_id == chunk_id)
        .order_by(Concept.name)
    )
    if concept_ids:
        query = query.where(Concept.id.in_([UUID(str(value)) for value in concept_ids]))
    rows = db.execute(query).all()
    content_lower = chunk.content.lower()
    best: tuple[int, str, UUID] | None = None
    for concept, _relation_id in rows:
        frequency = content_lower.count(concept.name.lower())
        if best is None or (frequency, concept.name) > (best[0], best[1]):
            best = (frequency, concept.name, concept.id)
    return best[2] if best else None
