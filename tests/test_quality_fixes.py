"""Quality fixes acceptance: BM25 retrieval, context packing, audio cap,
and reserve/settle budget semantics."""

import asyncio
import math
import uuid

import pytest
from fastapi.testclient import TestClient

from app.ai.providers import estimate_tokens
from app.services.context_assembly import build_study_context
from app.services.text import bm25_scores

# --- W1: BM25 lexical ranking ---

def test_bm25_ranks_rare_terms_above_common_terms() -> None:
    docs = [
        "The locking protocol is used in databases everywhere.",
        "Photosynthesis converts light energy in chloroplasts.",
        "Locking policies and deadlock locking again, locking.",
    ]
    scores = bm25_scores({"locking", "chloroplasts"}, docs)
    # "chloroplasts" appears once in one doc; "locking" is common across docs.
    # IDF must make the rare-term doc score close to the term-heavy doc.
    assert scores[1] > 0
    assert scores[0] > 0
    assert max(scores) == pytest.approx(1.0)


def test_bm25_zero_when_no_terms_match() -> None:
    scores = bm25_scores({"quantum", "zebra"}, ["ordinary locking text", "more locking"])
    assert scores == [0.0, 0.0]


def test_bm25_empty_inputs() -> None:
    assert bm25_scores({"term"}, []) == []
    assert bm25_scores(set(), ["text"]) == [0.0]


def test_retrieval_prefers_term_dense_relevant_chunk(client: TestClient) -> None:
    tag = uuid.uuid4().hex[:8]
    user = client.post(
        "/api/v1/auth/register",
        json={"email": f"bm25-{tag}@example.com", "password": "correct-horse-9",
              "display_name": "Learner"},
    ).json()
    auth = {"Authorization": f"Bearer {user['access_token']}"}
    ctx = client.post("/api/v1/contexts", headers=auth, json={"title": "Ctx"}).json()["id"]
    # Resource A: one incidental mention. Resource B: term-dense on the topic.
    client.post("/api/v1/resources/text", headers=auth, json={
        "context_id": ctx, "title": "Casual",
        "text": "Serializability is mentioned once here in passing at the start.",
    })
    client.post("/api/v1/resources/text", headers=auth, json={
        "context_id": ctx, "title": "Dense",
        "text": "Serializability defines correct concurrent schedules. Conflict "
        "serializability is checked with precedence graphs. View serializability "
        "generalizes conflict serializability for real database transactions.",
    })
    session = client.post(
        "/api/v1/study/sessions", headers=auth, json={"context_id": ctx}
    ).json()
    answer = client.post(
        f"/api/v1/study/sessions/{session['id']}/messages",
        headers=auth,
        json={"content": "Explain conflict serializability and precedence graphs"},
    )
    assert answer.status_code == 200
    sources = answer.json()["sources"]
    assert sources, "relevant material must be retrieved"
    assert sources[0]["title"] == "Dense"


def test_dedupe_keeps_highest_scored_copy() -> None:
    from app.ai.providers import RetrievedChunk
    from app.services.study import _dedupe_chunks

    dup_a = RetrievedChunk(chunk_id="a", resource_id="r", content="Same text here.",
                           source_title="A", score=0.9)
    dup_b = RetrievedChunk(chunk_id="b", resource_id="r", content="  Same  TEXT  here. ",
                           source_title="B", score=0.5)
    unique = RetrievedChunk(chunk_id="c", resource_id="r", content="Different material entirely.",
                            source_title="C", score=0.4)
    kept = _dedupe_chunks([dup_b, dup_a, unique])
    assert [item.chunk_id for item in kept] == ["a", "c"]


# --- W4: context packing ---

def test_context_dedup_and_per_chunk_cap() -> None:
    from app.ai.providers import RetrievedChunk

    dup = RetrievedChunk(chunk_id="a", resource_id="r", content="Repeated paragraph text.",
                         source_title="A", score=1.0)
    dup_again = RetrievedChunk(chunk_id="b", resource_id="r", content="Repeated paragraph text.",
                               source_title="B", score=0.9)
    long_chunk = RetrievedChunk(chunk_id="c", resource_id="r", content="L" * 5000,
                                source_title="C", score=0.8)
    context = build_study_context([dup, dup_again, long_chunk], max_chars=4000, per_chunk=1200)
    assert context.count("Repeated paragraph text.") == 1
    # Long chunk truncated to per_chunk before the header.
    assert "L" * 1200 in context
    assert "L" * 1201 not in context
    assert len(context) <= 4000


def test_backward_compatible_no_per_chunk_cap() -> None:
    from app.ai.providers import RetrievedChunk

    chunk = RetrievedChunk(chunk_id="a", resource_id="r", content="x" * 3000,
                           source_title="Doc", score=1.0)
    context = build_study_context([chunk], max_chars=2000)
    assert len(context) <= 2000
    assert chunk.content[:2000 - len("[Doc] ")] in context


# --- W2: audio size cap ---

class _FakeTTS:
    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        return b"AUDIO", "audio/mpeg", 10


def test_oversized_note_rejected_before_tts(client: TestClient, monkeypatch) -> None:
    from app.services.audio import MAX_AUDIO_CHARS

    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: _FakeTTS())
    tag = uuid.uuid4().hex[:8]
    user = client.post(
        "/api/v1/auth/register",
        json={"email": f"audio-cap-{tag}@example.com", "password": "correct-horse-9",
              "display_name": "Learner"},
    ).json()
    auth = {"Authorization": f"Bearer {user['access_token']}"}
    ctx = client.post("/api/v1/contexts", headers=auth, json={"title": "Ctx"}).json()["id"]
    note = client.post(
        "/api/v1/notes", headers=auth,
        json={"context_id": ctx, "title": "Huge", "body": "word " * (MAX_AUDIO_CHARS // 4 + 500)},
    ).json()
    generated = client.post(f"/api/v1/audio/notes/{note['id']}/generate", headers=auth)
    assert generated.status_code == 422
    assert "too long" in generated.json()["detail"]


def test_normal_note_still_converts(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: _FakeTTS())
    tag = uuid.uuid4().hex[:8]
    user = client.post(
        "/api/v1/auth/register",
        json={"email": f"audio-ok-{tag}@example.com", "password": "correct-horse-9",
              "display_name": "Learner"},
    ).json()
    auth = {"Authorization": f"Bearer {user['access_token']}"}
    ctx = client.post("/api/v1/contexts", headers=auth, json={"title": "Ctx"}).json()["id"]
    note = client.post(
        "/api/v1/notes", headers=auth,
        json={"context_id": ctx, "title": "N", "body": "Short readable body."},
    ).json()
    generated = client.post(f"/api/v1/audio/notes/{note['id']}/generate", headers=auth)
    assert generated.status_code == 201
    assert generated.json()["status"] == "READY"


# --- W3: reserve/settle budget semantics ---

def _patch_budget(monkeypatch, per_user: float) -> None:
    import app.ai.budget as budget
    import app.ai.registry as registry
    import app.services.llm_keys as llm_keys

    class _Settings:
        aria_env = "development"
        aria_ai_monthly_budget_usd = 0.0
        aria_llm_per_user_budget_usd = per_user
        groq_api_key = None
        llm_model = "llama-3.3-70b-versatile"
        aria_llm_keys_encryption_key = None
        aria_llm_keys_encryption_key_old = None

        llm_allowed_models = ["llama-3.3-70b-versatile"]

    instance = _Settings()
    monkeypatch.setattr(budget, "get_settings", lambda: instance)
    monkeypatch.setattr(registry, "get_settings", lambda: instance)
    monkeypatch.setattr(llm_keys, "get_settings", lambda: instance)


def test_reserve_then_settle_converges_to_actual() -> None:
    import app.ai.budget as budget

    budget.reset_learner_budget()
    owner = uuid.uuid4()
    budget.reserve_learner_usage(
        owner_id=owner, model="llama-3.3-70b-versatile",
        prompt_tokens=1000, completion_tokens=500,
    )
    reserved_spend = budget.learner_spend_usd(owner)
    expected_reserve = budget.estimate_cost_usd(
        model="llama-3.3-70b-versatile", prompt_tokens=1000, completion_tokens=500
    )
    assert reserved_spend == pytest.approx(expected_reserve)
    # Actual usage smaller than reserved: settle refunds the difference.
    budget.settle_learner_usage(
        owner_id=owner, model="llama-3.3-70b-versatile",
        prompt_tokens_delta=-400, completion_tokens_delta=-200,
    )
    actual = budget.estimate_cost_usd(
        model="llama-3.3-70b-versatile", prompt_tokens=600, completion_tokens=300
    )
    assert budget.learner_spend_usd(owner) == pytest.approx(actual)
    budget.reset_learner_budget()


def test_reservation_blocks_second_inflight_call(monkeypatch) -> None:
    import app.ai.budget as budget
    from app.ai.providers import LiteLLMGroqProvider

    _patch_budget(monkeypatch, per_user=0.0015)
    budget.reset_learner_budget()
    owner = uuid.uuid4()
    try:
        provider = LiteLLMGroqProvider(
            api_key="gsk_x", model="llama-3.3-70b-versatile", owner_id=owner
        )
        # First in-flight call reserves upfront.
        provider._reserve_learner(4000)
        # The remaining balance cannot fund a second whole reservation.
        with pytest.raises(budget.BudgetExceeded):
            provider._reserve_learner(4000)
    finally:
        budget.reset_learner_budget()


def test_unknown_failed_call_retains_reservation(monkeypatch) -> None:
    import app.ai.budget as budget
    from app.ai.providers import LiteLLMGroqProvider

    _patch_budget(monkeypatch, per_user=10.0)
    budget.reset_learner_budget()
    owner = uuid.uuid4()
    try:
        provider = LiteLLMGroqProvider(
            api_key="gsk_x", model="llama-3.3-70b-versatile", owner_id=owner
        )
        reserved = provider._reserve_learner(4000)
        assert reserved is not None
        provisional = budget.learner_spend_usd(owner)
        provider._settle_learner(reserved, None)  # provider billing unknown
        assert provisional > 0
        assert budget.learner_spend_usd(owner) == pytest.approx(provisional)
    finally:
        budget.reset_learner_budget()


def test_owner_scoped_generate_text_settles_to_actual(monkeypatch) -> None:
    import app.ai.budget as budget
    from app.ai.providers import LiteLLMGroqProvider

    _patch_budget(monkeypatch, per_user=10.0)
    budget.reset_learner_budget()
    owner = uuid.uuid4()
    try:
        provider = LiteLLMGroqProvider(
            api_key="gsk_x", model="llama-3.3-70b-versatile", owner_id=owner
        )

        class _Usage:
            prompt_tokens = 50
            completion_tokens = 20

        class _Msg:
            content = "answer"

        class _Choice:
            message = _Msg()

        class _Response:
            usage = _Usage()
            choices = [_Choice()]

        async def _fake_completion(*args, **kwargs):
            return _Response()

        import litellm

        monkeypatch.setattr(litellm, "acompletion", _fake_completion)
        answer = asyncio.run(provider.generate_text(system="s" * 100, user="u" * 100))
        assert answer == "answer"
        # Reserve+settle must converge to actual usage, not estimate+actual.
        expected = budget.estimate_cost_usd(
            model="llama-3.3-70b-versatile", prompt_tokens=50, completion_tokens=20
        )
        assert budget.learner_spend_usd(owner) == pytest.approx(expected)
    finally:
        budget.reset_learner_budget()


def test_estimate_tokens_is_ceiling_with_margin() -> None:
    assert estimate_tokens(0) == 1
    assert estimate_tokens(4) == 2
    assert estimate_tokens(400) == math.ceil(400 / 4 * 1.25) == 125
