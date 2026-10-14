import asyncio
from types import SimpleNamespace

from app.assessment.schema import ConceptSet
from app.services.concepts import (
    CONCEPT_MATERIAL_CHAR_LIMIT,
    CONCEPT_PROMPT_CHAR_LIMIT,
    _concept_material,
    extract_concepts_structured,
)


def test_large_subject_prompt_is_bounded_before_provider_call(monkeypatch):
    calls = []

    class Provider:
        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            return ConceptSet(concepts=["Photosynthesis"])

    monkeypatch.setattr("app.ai.registry.get_llm_provider", lambda: Provider())
    chunks = [SimpleNamespace(content="chloroplast " * 100) for _ in range(1000)]
    material = _concept_material(chunks)
    assert len(material) <= CONCEPT_MATERIAL_CHAR_LIMIT
    assert "[1000]" not in material
    result = asyncio.run(extract_concepts_structured(chunks))
    assert result == ["photosynthesis"]
    assert len(calls) == 1
    assert len(calls[0]["prompt"]) <= CONCEPT_PROMPT_CHAR_LIMIT


def test_material_budget_counts_headers_and_separators(monkeypatch):
    monkeypatch.setattr("app.services.concepts.CONCEPT_MATERIAL_CHAR_LIMIT", 12)
    assert _concept_material([SimpleNamespace(content="abc"), SimpleNamespace(content="defgh")]) == "[1] abc"
    assert _concept_material([SimpleNamespace(content="  "), SimpleNamespace(content="abcdefghi")]) == "[2] abcdefgh"


def test_oversized_template_never_reaches_provider(monkeypatch):
    import pytest

    class Provider:
        async def generate_structured(self, **kwargs):
            raise AssertionError("Oversized prompts must not call the provider")

    monkeypatch.setattr("app.ai.registry.get_llm_provider", lambda: Provider())
    monkeypatch.setattr("app.services.concepts.get_prompt", lambda name: SimpleNamespace(
        render=lambda **kwargs: "x" * (CONCEPT_PROMPT_CHAR_LIMIT + 1)))
    with pytest.raises(ValueError, match="budget"):
        asyncio.run(extract_concepts_structured([SimpleNamespace(content="abc")]))


def test_deterministic_concept_ties_are_alphabetical():
    from types import SimpleNamespace

    from app.services import concepts

    chunks = [SimpleNamespace(content="zebra. maple. apple.")]
    assert concepts.extract_concepts_deterministic(chunks) == ["apple", "maple", "zebra"]
    assert concepts.extract_concepts_deterministic(chunks, limit=2) == ["apple", "maple"]
    assert concepts.extract_concepts_deterministic([SimpleNamespace(content="apple; zebra; maple")]) == ["apple", "maple", "zebra"]


def test_deterministic_concepts_are_key_phrases_not_filler_words():
    """Regression: the fallback used to return the alphabetically-first single
    words ("args", "base", "between", "block") because every token tied."""
    from types import SimpleNamespace

    from app.services import concepts

    material = [
        SimpleNamespace(content=(
            "A function is a reusable block of code. Default arguments provide fallback "
            "values. Recursion is when a function calls itself; every recursive function "
            "needs a base case to stop. Strict two-phase locking holds exclusive locks.")),
        SimpleNamespace(content=(
            "A tuple is an ordered, immutable sequence. A dictionary maps keys to values. "
            "List comprehensions build lists from iterables. A function returns a value.")),
    ]
    names = concepts.extract_concepts_deterministic(material, limit=12)
    assert names[0] == "function"  # mentioned most, across both chunks
    for expected in ("base case", "default arguments", "list comprehensions", "two-phase locking"):
        assert any(expected in name for name in names), expected
    # Connective verbs and bare generic words never stand alone as a concept
    # (though a generic word may sit inside a longer phrase, e.g. "fallback
    # values"), and the output is deterministic.
    standalone_junk = {"between", "values", "value", "needs", "calls", "holds", "provide", "stop"}
    assert not standalone_junk & set(names)
    assert names == concepts.extract_concepts_deterministic(material, limit=12)


def test_concept_cache_persists_and_invalidates_material_and_limit(session_factory, monkeypatch):
    from dataclasses import replace
    from uuid import uuid4

    from sqlalchemy import delete

    from app.ai.prompts import get_prompt
    from app.db.models import Concept, ConceptChunk, LearningContext, Resource, ResourceChunk
    from app.services.concepts import sync_concepts

    calls = []
    class Provider:
        model = "test-model"
        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            return ConceptSet(concepts=["apple"])
    monkeypatch.setattr("app.services.concepts.get_llm_provider_for_owner", lambda *args, **kwargs: Provider())
    owner = uuid4()
    with session_factory() as db:
        context = LearningContext(owner_id=owner, title="Cache")
        db.add(context)
        db.flush()
        resource = Resource(owner_id=owner, context_id=context.id, title="Text", resource_type="TEXT", processing_status="READY")
        db.add(resource)
        db.flush()
        chunk = ResourceChunk(owner_id=owner, resource_id=resource.id, content="apple maple zebra", chunk_index=0)
        db.add(chunk)
        db.commit()
        context_id, chunk_id = context.id, chunk.id
        first = asyncio.run(sync_concepts(db, owner_id=owner, context_id=context_id))
        first_ids = [concept.id for concept in first]
    with session_factory() as db:
        repeated = asyncio.run(sync_concepts(db, owner_id=owner, context_id=context_id))
        assert [concept.id for concept in repeated] == first_ids
        assert len(calls) == 1
        db.get(ResourceChunk, chunk_id).content = "apple maple zebra changed"
        db.commit()
        asyncio.run(sync_concepts(db, owner_id=owner, context_id=context_id))
        assert len(calls) == 2
        asyncio.run(sync_concepts(db, owner_id=owner, context_id=context_id, limit=3))
        assert len(calls) == 3
        Provider.model = "changed-model"
        asyncio.run(sync_concepts(db, owner_id=owner, context_id=context_id, limit=3))
        assert len(calls) == 4
        updated_prompt = replace(get_prompt("concept_extraction"), version=2)
        monkeypatch.setattr("app.services.concepts.get_prompt", lambda name: updated_prompt)
        asyncio.run(sync_concepts(db, owner_id=owner, context_id=context_id, limit=3))
        assert len(calls) == 5
        db.execute(delete(ConceptChunk).where(ConceptChunk.concept_id.in_(first_ids)))
        db.execute(delete(Concept).where(Concept.id.in_(first_ids)))
        db.commit()
        repaired = asyncio.run(sync_concepts(db, owner_id=owner, context_id=context_id, limit=3))
        assert len(calls) == 6
        assert [concept.id for concept in repaired] != first_ids
        asyncio.run(sync_concepts(db, owner_id=owner, context_id=context_id, limit=3))
        assert len(calls) == 6


def test_failed_concept_provider_is_not_cached(session_factory, monkeypatch):
    from uuid import uuid4

    from app.db.models import LearningContext, Resource, ResourceChunk
    from app.services.concepts import sync_concepts

    calls = []
    class Provider:
        model = "test-model"
        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            raise RuntimeError("Unavailable")
    monkeypatch.setattr("app.services.concepts.get_llm_provider_for_owner", lambda *args, **kwargs: Provider())
    owner = uuid4()
    with session_factory() as db:
        context = LearningContext(owner_id=owner, title="Retry")
        db.add(context)
        db.flush()
        resource = Resource(owner_id=owner, context_id=context.id, title="Text", resource_type="TEXT", processing_status="READY")
        db.add(resource)
        db.flush()
        db.add(ResourceChunk(owner_id=owner, resource_id=resource.id, content="apple maple zebra", chunk_index=0))
        db.commit()
        assert asyncio.run(sync_concepts(db, owner_id=owner, context_id=context.id))
        assert asyncio.run(sync_concepts(db, owner_id=owner, context_id=context.id))
        assert len(calls) == 2
        assert context.concept_sync_fingerprint is None


def test_concept_cache_reads_external_material_change_in_reused_session(session_factory, monkeypatch):
    from uuid import uuid4

    from app.db.models import LearningContext, Resource, ResourceChunk
    from app.services.concepts import sync_concepts

    calls = []
    class Provider:
        model = "test-model"
        async def generate_structured(self, **kwargs):
            calls.append(kwargs["prompt"])
            return ConceptSet(concepts=["apple" if "apple" in kwargs["prompt"] else "maple"])
    monkeypatch.setattr("app.services.concepts.get_llm_provider_for_owner", lambda *args, **kwargs: Provider())
    owner = uuid4()
    with session_factory() as db:
        context = LearningContext(owner_id=owner, title="External changes")
        db.add(context)
        db.flush()
        resource = Resource(owner_id=owner, context_id=context.id, title="Text", resource_type="TEXT", processing_status="READY")
        db.add(resource)
        db.flush()
        chunk = ResourceChunk(owner_id=owner, resource_id=resource.id, content="apple", chunk_index=0)
        db.add(chunk)
        db.commit()
        assert [item.name for item in asyncio.run(sync_concepts(db, owner_id=owner, context_id=context.id))] == ["apple"]
        with session_factory() as writer:
            writer.get(ResourceChunk, chunk.id).content = "maple"
            writer.commit()
        assert [item.name for item in asyncio.run(sync_concepts(db, owner_id=owner, context_id=context.id))] == ["maple"]
        assert len(calls) == 2
        assert "maple" in calls[-1]


def test_material_change_during_provider_does_not_publish_stale_concepts(session_factory, monkeypatch):
    from uuid import uuid4

    import pytest
    from sqlalchemy import select

    from app.core.errors import ValidationError
    from app.db.models import Concept, LearningContext, Resource, ResourceChunk
    from app.services.concepts import sync_concepts

    owner = uuid4()
    with session_factory() as db:
        context = LearningContext(owner_id=owner, title="In-flight changes")
        db.add(context)
        db.flush()
        resource = Resource(owner_id=owner, context_id=context.id, title="Text", resource_type="TEXT", processing_status="READY")
        db.add(resource)
        db.flush()
        chunk = ResourceChunk(owner_id=owner, resource_id=resource.id, content="apple", chunk_index=0)
        db.add(chunk)
        db.commit()
        chunk_id = chunk.id
        class Provider:
            model = "test-model"
            async def generate_structured(self, **kwargs):
                with session_factory() as writer:
                    writer.get(ResourceChunk, chunk_id).content = "maple"
                    writer.commit()
                return ConceptSet(concepts=["apple"])
        monkeypatch.setattr("app.services.concepts.get_llm_provider_for_owner", lambda *args, **kwargs: Provider())
        with pytest.raises(ValidationError, match="material changed"):
            asyncio.run(sync_concepts(db, owner_id=owner, context_id=context.id))
        assert db.scalars(select(Concept).where(Concept.context_id == context.id)).all() == []
        assert context.concept_sync_fingerprint is None
        assert db.get(ResourceChunk, chunk_id).content == "maple"
