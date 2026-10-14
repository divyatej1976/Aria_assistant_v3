"""Phase 12.5 AI governance: prompt registry, provider factory, budget."""

import time
from types import SimpleNamespace

import pytest

from app.ai.budget import (
    BudgetExceeded,
    assert_within_budget,
    record_usage,
    reset_budget,
    spend_usd,
)
from app.ai.prompts import get_prompt
from app.ai.providers import LiteLLMGroqProvider


def _settings_with_budget(budget: float):
    class _Settings:
        aria_ai_monthly_budget_usd = budget

    return _Settings()


def test_budgeted_completions_use_reserved_output_limit(monkeypatch):
    import asyncio

    import litellm
    from pydantic import BaseModel

    import app.ai.budget as budget
    import app.ai.providers as providers

    class Result(BaseModel):
        answer: str

    calls = []
    settlements = []
    monkeypatch.setattr(budget, "assert_within_budget", lambda: None)
    monkeypatch.setattr(budget, "assert_learner_within_budget", lambda owner: None)
    monkeypatch.setattr(budget, "learner_budget_usd", lambda: 1)
    monkeypatch.setattr(budget, "reserve_learner_usage", lambda **kw: calls.append(kw))
    monkeypatch.setattr(budget, "settle_learner_usage", lambda **kw: settlements.append(kw))
    monkeypatch.setattr(providers, "completion_reserve_tokens", lambda: 731)
    monkeypatch.setattr(providers.LiteLLMGroqProvider, "_log_call", lambda *a, **kw: (10, 20))

    async def completion(**kw):
        assert kw["max_tokens"] == calls[-1]["completion_tokens"] == 731
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"answer":"ok"}'))])

    monkeypatch.setattr(litellm, "acompletion", completion)
    provider = LiteLLMGroqProvider(api_key="test", model="test", owner_id="learner")
    assert asyncio.run(provider.generate_text(system="system", user="user")) == '{"answer":"ok"}'
    assert asyncio.run(provider.generate_structured(prompt="prompt", schema=Result)).answer == "ok"
    assert len(calls) == len(settlements) == 2
    assert all(item["completion_tokens_delta"] == 20 - 731 for item in settlements)


@pytest.mark.parametrize("structured", [False, True])
def test_malformed_response_retains_reported_usage(monkeypatch, structured):
    import asyncio

    import litellm

    import app.ai.budget as budget

    charges = []
    settlements = []
    monkeypatch.setattr(budget, "assert_within_budget", lambda: None)
    monkeypatch.setattr(budget, "assert_learner_within_budget", lambda owner: None)
    monkeypatch.setattr(budget, "record_usage", lambda **kw: charges.append(kw))
    provider = LiteLLMGroqProvider(api_key="test", model="test", owner_id="learner")
    monkeypatch.setattr(provider, "_reserve_learner", lambda chars: (100, 512))
    monkeypatch.setattr(provider, "_settle_learner", lambda reserved, final: settlements.append(final))

    async def completion(**kw):
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=81, completion_tokens=37), choices=[])

    monkeypatch.setattr(litellm, "acompletion", completion)
    with pytest.raises(IndexError):
        if structured:
            asyncio.run(provider.generate_structured(prompt="prompt", schema=object))
        else:
            asyncio.run(provider.generate_text(system="system", user="user"))
    assert charges == [{"model": "test", "prompt_tokens": 81, "completion_tokens": 37}]
    assert settlements == [(81, 37)]


@pytest.mark.parametrize("invalid", [-1, "25", True, 1.5, float("nan")])
def test_invalid_usage_cannot_reduce_spend(monkeypatch, invalid):
    import app.ai.budget as budget
    from app.ai.providers import estimate_tokens

    charges = []
    monkeypatch.setattr(budget, "record_usage", lambda **kw: charges.append(kw))
    provider = LiteLLMGroqProvider(api_key="test", model="test")
    response = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=invalid, completion_tokens=invalid))
    result = provider._log_call(
        kind="test", started=time.monotonic(), response=response,
        prompt_chars=100, completion_chars=40,
    )
    assert result == (estimate_tokens(100), estimate_tokens(40))
    assert charges == [{"model": "test", "prompt_tokens": result[0], "completion_tokens": result[1]}]


def test_prompt_registry_returns_versioned_prompt() -> None:
    prompt = get_prompt("concept_extraction")
    assert prompt.key == "concept_extraction"
    assert prompt.version == 1
    assert prompt.label() == "concept_extraction:1"


def test_prompt_render_matches_call_site_shape() -> None:
    assert (
        get_prompt("concept_extraction")
        .render(limit=3, material="M")
        .endswith("\n\nStudy material:\nM")
    )
    note = get_prompt("note_draft").render(material="M")
    assert '"body": "..."' in note
    assert "Material:\nM" in note
    mcq = get_prompt("mcq_generation").render(
        difficulty="medium", count=2, material="M"
    )
    assert "Difficulty: medium" in mcq
    assert "Produce 2 questions" in mcq
    assert '"correct_option": "A"' in mcq


def test_unknown_prompt_raises() -> None:
    import pytest

    with pytest.raises(KeyError):
        get_prompt("does_not_exist")


def test_provider_factory_returns_none_without_key(monkeypatch) -> None:
    import app.ai.registry as registry

    class Settings:
        groq_api_key = None
        llm_model = "llama-3.3-70b-versatile"

    monkeypatch.setattr(registry, "get_settings", lambda: Settings())
    assert registry.get_llm_provider() is None


def test_provider_factory_returns_provider_with_key(monkeypatch) -> None:
    import app.ai.registry as registry

    class Settings:
        groq_api_key = "test-key"
        llm_model = "llama-3.3-70b-versatile"

    monkeypatch.setattr(registry, "get_settings", lambda: Settings())
    provider = registry.get_llm_provider()
    assert isinstance(provider, LiteLLMGroqProvider)
    assert provider.model == "llama-3.3-70b-versatile"


def test_budget_blocks_generation_when_exceeded(monkeypatch) -> None:
    import app.ai.budget as budget

    reset_budget()
    monkeypatch.setattr(budget, "get_settings", lambda: _settings_with_budget(0.001))
    record_usage(model="llama-3.3-70b-versatile", prompt_tokens=1000, completion_tokens=1000)
    assert spend_usd() > 0.001
    try:
        assert_within_budget()
    except BudgetExceeded:
        pass
    else:
        raise AssertionError("expected BudgetExceeded")
    reset_budget()


def test_unlimited_budget_never_blocks(monkeypatch) -> None:
    import app.ai.budget as budget

    reset_budget()
    monkeypatch.setattr(budget, "get_settings", lambda: _settings_with_budget(0.0))
    record_usage(model="llama-3.3-70b-versatile", prompt_tokens=10_000_000, completion_tokens=1)
    assert_within_budget()  # must not raise
    reset_budget()


def _prod_settings(budget: float):
    class _Settings:
        aria_env = "production"
        aria_ai_monthly_budget_usd = budget

    return _Settings()


def test_production_accounting_failure_blocks_generation(monkeypatch) -> None:
    import app.ai.budget as budget

    monkeypatch.setattr(budget, "get_settings", lambda: _prod_settings(0.001))
    monkeypatch.setattr(budget, "_probe_db", lambda table="ai_usage": False)
    budget._accounting_unavailable = True
    try:
        try:
            assert_within_budget()
        except BudgetExceeded:
            pass
        else:
            raise AssertionError("expected BudgetExceeded when accounting is down in production")
    finally:
        budget._accounting_unavailable = False
        budget.reset_budget()


def test_production_accounting_self_heals_when_db_returns(monkeypatch) -> None:
    import app.ai.budget as budget

    monkeypatch.setattr(budget, "get_settings", lambda: _prod_settings(0.001))
    monkeypatch.setattr(budget, "_probe_db", lambda table="ai_usage": True)
    monkeypatch.setattr(budget, "_db_spend", lambda period: 0.0)
    budget._accounting_unavailable = True
    try:
        assert_within_budget()  # probe succeeds -> flag cleared, spend 0 < budget
        assert budget._accounting_unavailable is False
    finally:
        budget.reset_budget()


def test_development_accounting_failure_never_blocks(monkeypatch) -> None:
    import app.ai.budget as budget

    monkeypatch.setattr(budget, "get_settings", lambda: _settings_with_budget(0.001))
    monkeypatch.setattr(budget, "_probe_db", lambda: False)
    monkeypatch.setattr(budget, "_db_spend", lambda period: 0.0)
    budget._accounting_unavailable = True  # even if set, dev must not fail closed
    try:
        assert_within_budget()  # must not raise
    finally:
        budget._accounting_unavailable = False
        budget.reset_budget()


def test_reset_budget_clears_accounting_failure(monkeypatch) -> None:
    import app.ai.budget as budget

    monkeypatch.setattr(budget, "get_settings", lambda: _prod_settings(0.001))
    budget._mark_db_failure()
    assert budget._accounting_unavailable is True
    reset_budget()
    assert budget._accounting_unavailable is False
    monkeypatch.setattr(budget, "get_settings", lambda: _settings_with_budget(0.0))
    budget._mark_db_failure()  # dev never sets the flag
    assert budget._accounting_unavailable is False


def test_budget_spend_records(engine) -> None:
    reset_budget()
    record_usage(model="llama-3.3-70b-versatile", prompt_tokens=1000, completion_tokens=0)
    assert spend_usd() > 0
    if engine.dialect.name == "postgresql":
        from sqlalchemy import select

        from app.db.models import AiUsage
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            row = db.scalar(select(AiUsage))
            assert row is not None
            assert row.spend_usd > 0
        finally:
            db.close()
    reset_budget()


def test_budget_accumulates_without_lost_updates(engine) -> None:
    from app.ai.budget import estimate_cost_usd

    reset_budget()
    calls = 5
    for _ in range(calls):
        record_usage(
            model="llama-3.3-70b-versatile", prompt_tokens=1000, completion_tokens=0
        )
    expected = calls * estimate_cost_usd(
        model="llama-3.3-70b-versatile", prompt_tokens=1000, completion_tokens=0
    )
    assert abs(spend_usd() - expected) < 1e-9
    if engine.dialect.name == "postgresql":
        from sqlalchemy import select

        from app.db.models import AiUsage
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            row = db.scalar(select(AiUsage))
            assert row is not None
            assert abs(row.spend_usd - expected) < 1e-9
        finally:
            db.close()
    reset_budget()


def test_log_call_records_prompt_version_metric() -> None:
    from app.core.metrics import ai_calls_total

    reset_budget()
    provider = LiteLLMGroqProvider(api_key="k", model="llama-3.3-70b-versatile")
    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5)
    )
    provider._log_call(
        kind="generate_structured",
        started=time.monotonic() - 0.05,
        response=response,
        prompt_version="mcq_generation:1",
    )
    value = ai_calls_total.labels(
        kind="generate_structured",
        model="llama-3.3-70b-versatile",
        prompt_version="mcq_generation:1",
    )
    assert value._value.get() >= 1
    assert spend_usd() > 0
    reset_budget()


def test_missing_usage_metadata_is_estimated_never_skipped(monkeypatch) -> None:
    """A response without usage metadata must still record spend — globally via
    the post-call estimate, and per-learner via the pre-call reservation — so
    budgets can never be bypassed by a metadata-less response."""
    import uuid

    import app.ai.budget as budget
    from app.ai.providers import LiteLLMGroqProvider, estimate_tokens

    # Ceiling + 25% margin heuristic (documented, not a guaranteed upper bound).
    assert estimate_tokens(0) == 1
    assert estimate_tokens(4) == 2
    assert estimate_tokens(400) == 125
    assert estimate_tokens(200) == 63

    reset_budget()
    budget.reset_learner_budget()
    owner_id = uuid.uuid4()
    provider = LiteLLMGroqProvider(
        api_key="k", model="llama-3.3-70b-versatile", owner_id=owner_id
    )

    class _Msg:
        content = "x" * 200

    class _Choice:
        message = _Msg()

    class _Response:
        usage = None  # LiteLLM returned no usage block
        choices = [_Choice()]

    async def _fake_completion(*args, **kwargs):
        return _Response()

    import litellm

    monkeypatch.setattr(litellm, "acompletion", _fake_completion)
    before_global = spend_usd()
    asyncio_run = __import__("asyncio").run
    answer = asyncio_run(provider.generate_text(system="s" * 400, user="u" * 100))
    assert answer == "x" * 200
    # Global: post-call estimate recorded.
    assert spend_usd() > before_global
    # Learner: pre-call reservation guarantees nonzero accounted spend.
    assert budget.learner_spend_usd(owner_id) > 0
    reset_budget()
    budget.reset_learner_budget()


@pytest.mark.parametrize("structured", [False, True])
@pytest.mark.parametrize("cancelled", [False, True])
def test_unknown_transport_or_cancellation_keeps_provisional_reservation(monkeypatch, structured, cancelled):
    import asyncio

    import litellm
    from pydantic import BaseModel

    import app.ai.budget as budget

    reservations, settlements = [], []
    global_reservations, global_adjustments = [], []
    monkeypatch.setattr(budget, "monthly_budget_usd", lambda: 1)
    monkeypatch.setattr(budget, "reserve_usage", lambda **kwargs: global_reservations.append(kwargs))
    monkeypatch.setattr(budget, "record_usage", lambda **kwargs: global_adjustments.append(kwargs))
    monkeypatch.setattr(budget, "assert_within_budget", lambda: None)
    monkeypatch.setattr(budget, "assert_learner_within_budget", lambda owner: None)
    monkeypatch.setattr(budget, "learner_budget_usd", lambda: 1)
    monkeypatch.setattr(budget, "reserve_learner_usage", lambda **kwargs: reservations.append(kwargs))
    monkeypatch.setattr(budget, "settle_learner_usage", lambda **kwargs: settlements.append(kwargs))
    async def completion(**kwargs):
        if cancelled:
            raise asyncio.CancelledError()
        raise TimeoutError("No response; provider billing is unknown")
    monkeypatch.setattr(litellm, "acompletion", completion)
    provider = LiteLLMGroqProvider(api_key="test", model="test", owner_id="learner")
    class Result(BaseModel):
        answer: str
    with pytest.raises(asyncio.CancelledError if cancelled else TimeoutError):
        asyncio.run(provider.generate_structured(prompt="prompt", schema=Result) if structured
                    else provider.generate_text(system="system", user="question"))
    assert len(reservations) == 1
    assert reservations[0]["prompt_tokens"] > 0
    assert reservations[0]["completion_tokens"] > 0
    assert settlements == []
    assert len(global_reservations) == 1
    assert global_reservations[0]["completion_tokens"] > 0
    assert global_adjustments == []


def test_learner_reservation_refuses_cost_exceeding_remaining_budget(session_factory, monkeypatch):
    from uuid import uuid4

    import app.ai.budget as budget
    import app.db.session as sessions

    cost = budget.estimate_cost_usd(model="llama-3.3-70b-versatile", prompt_tokens=100, completion_tokens=0)
    monkeypatch.setattr(budget, "get_settings", lambda: SimpleNamespace(aria_llm_per_user_budget_usd=cost * 1.5, aria_env="development"))
    monkeypatch.setattr(sessions, "SessionLocal", session_factory)
    owner = uuid4()
    budget.reserve_learner_usage(owner_id=owner, model="llama-3.3-70b-versatile", prompt_tokens=100, completion_tokens=0)
    with pytest.raises(BudgetExceeded, match="Insufficient"):
        budget.reserve_learner_usage(owner_id=owner, model="llama-3.3-70b-versatile", prompt_tokens=100, completion_tokens=0)
    assert budget.learner_spend_usd(owner) == pytest.approx(cost)


def test_postgres_simultaneous_learner_reservations_have_one_winner(engine, session_factory, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from uuid import uuid4

    import app.ai.budget as budget
    import app.db.session as sessions

    if engine.dialect.name != "postgresql":
        pytest.skip("Independent PostgreSQL connections required")
    cost = budget.estimate_cost_usd(model="llama-3.3-70b-versatile", prompt_tokens=100, completion_tokens=0)
    monkeypatch.setattr(budget, "get_settings", lambda: SimpleNamespace(aria_llm_per_user_budget_usd=cost * 1.5, aria_env="development"))
    monkeypatch.setattr(sessions, "SessionLocal", session_factory)
    owner, gate = uuid4(), Barrier(2)
    def reserve():
        gate.wait(timeout=5)
        try:
            budget.reserve_learner_usage(owner_id=owner, model="llama-3.3-70b-versatile", prompt_tokens=100, completion_tokens=0)
            return "admitted"
        except BudgetExceeded:
            return "blocked"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(reserve) for _ in range(2)]
        assert sorted(future.result(timeout=10) for future in futures) == ["admitted", "blocked"]
    assert budget.learner_spend_usd(owner) == pytest.approx(cost)


def test_learner_reservation_accounting_failure_blocks_production(monkeypatch):
    from uuid import uuid4

    import app.ai.budget as budget

    monkeypatch.setattr(budget, "get_settings", lambda: SimpleNamespace(aria_llm_per_user_budget_usd=1, aria_env="production"))
    monkeypatch.setattr(budget, "_learner_reserve_cost", lambda *args: None)
    owner = uuid4()
    with pytest.raises(BudgetExceeded, match="accounting is unavailable"):
        budget.reserve_learner_usage(owner_id=owner, model="test", prompt_tokens=10, completion_tokens=10)
    assert (str(owner), budget._period()) not in budget._learner_fallback_spend


@pytest.mark.parametrize("invalid", [-1, True, 1.5, "1"])
def test_learner_reservation_rejects_invalid_token_values(monkeypatch, invalid):
    import app.ai.budget as budget

    monkeypatch.setattr(budget, "_learner_reserve_cost", lambda *args: pytest.fail("Invalid tokens reached admission"))
    with pytest.raises(ValueError, match="nonnegative integers"):
        budget.reserve_learner_usage(owner_id="test", model="test", prompt_tokens=invalid, completion_tokens=10)


@pytest.mark.parametrize("structured", [False, True])
def test_global_reserved_completion_is_reconciled_without_double_charge(monkeypatch, structured):
    import asyncio

    import litellm
    from pydantic import BaseModel

    import app.ai.budget as budget

    reservations, adjustments = [], []
    monkeypatch.setattr(budget, "monthly_budget_usd", lambda: 1)
    monkeypatch.setattr(budget, "assert_within_budget", lambda: None)
    monkeypatch.setattr(budget, "reserve_usage", lambda **kwargs: reservations.append(kwargs))
    monkeypatch.setattr(budget, "record_usage", lambda **kwargs: adjustments.append(kwargs))
    async def completion(**kwargs):
        assert kwargs["max_tokens"] == reservations[0]["completion_tokens"]
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20), choices=[SimpleNamespace(message=SimpleNamespace(content='{"answer":"ok"}'))])
    monkeypatch.setattr(litellm, "acompletion", completion)
    provider = LiteLLMGroqProvider(api_key="test", model="test")
    class Result(BaseModel):
        answer: str
    asyncio.run(provider.generate_structured(prompt="prompt", schema=Result) if structured
                else provider.generate_text(system="system", user="question"))
    assert len(reservations) == len(adjustments) == 1
    assert adjustments[0]["prompt_tokens"] == 10 - reservations[0]["prompt_tokens"]
    assert adjustments[0]["completion_tokens"] == 20 - reservations[0]["completion_tokens"]


def test_learner_admission_failure_refunds_global_before_dispatch(monkeypatch):
    import app.ai.budget as budget

    reservations, adjustments = [], []
    monkeypatch.setattr(budget, "monthly_budget_usd", lambda: 1)
    monkeypatch.setattr(budget, "reserve_usage", lambda **kwargs: reservations.append(kwargs))
    monkeypatch.setattr(budget, "record_usage", lambda **kwargs: adjustments.append(kwargs))
    provider = LiteLLMGroqProvider(api_key="test", model="test")
    def refuse(chars):
        raise BudgetExceeded("Learner admission refused")
    monkeypatch.setattr(provider, "_reserve_learner", refuse)
    with pytest.raises(BudgetExceeded):
        provider._reserve_budgets(100)
    assert len(reservations) == len(adjustments) == 1
    assert adjustments[0]["prompt_tokens"] == -reservations[0]["prompt_tokens"]
    assert adjustments[0]["completion_tokens"] == -reservations[0]["completion_tokens"]


def test_postgres_simultaneous_global_reservations_have_one_winner(engine, session_factory, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    import app.ai.budget as budget
    import app.db.session as sessions

    if engine.dialect.name != "postgresql":
        pytest.skip("Independent PostgreSQL connections required")
    cost = budget.estimate_cost_usd(model="test", prompt_tokens=100, completion_tokens=0)
    monkeypatch.setattr(budget, "get_settings", lambda: SimpleNamespace(aria_ai_monthly_budget_usd=cost * 1.5, aria_env="development"))
    monkeypatch.setattr(budget, "_fallback_spend_by_period", {})
    monkeypatch.setattr(sessions, "SessionLocal", session_factory)
    gate = Barrier(2)
    def reserve():
        gate.wait(timeout=5)
        try:
            budget.reserve_usage(model="test", prompt_tokens=100, completion_tokens=0)
            return "admitted"
        except BudgetExceeded:
            return "blocked"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(reserve) for _ in range(2)]
        assert sorted(future.result(timeout=10) for future in futures) == ["admitted", "blocked"]
    assert budget.spend_usd() == pytest.approx(cost)

@pytest.mark.parametrize("structured", [False, True])
def test_completion_settles_original_month_after_rollover(session_factory, monkeypatch, structured):
    import asyncio
    from uuid import uuid4

    import litellm
    from pydantic import BaseModel
    from sqlalchemy import select

    import app.ai.budget as budget
    import app.db.session as sessions
    from app.db.models import AiUsage, LearnerAiUsage

    current = ["2026-10"]
    owner = uuid4()
    monkeypatch.setattr(budget, "_period", lambda: current[0])
    monkeypatch.setattr(budget, "_fallback_spend_by_period", {})
    monkeypatch.setattr(budget, "_learner_fallback_spend", {})
    monkeypatch.setattr(budget, "get_settings", lambda: SimpleNamespace(
        aria_ai_monthly_budget_usd=1, aria_llm_per_user_budget_usd=1, aria_env="development"))
    monkeypatch.setattr(sessions, "SessionLocal", session_factory)
    model = "llama-3.3-70b-versatile"

    async def completion(**kwargs):
        current[0] = "2026-11"
        # Unrelated spend in the new month must survive the old request's refund.
        budget.record_usage(model=model, prompt_tokens=100, completion_tokens=100)
        budget.record_learner_usage(owner_id=owner, model=model, prompt_tokens=100, completion_tokens=100)
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20),
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"answer":"ok"}'))])

    monkeypatch.setattr(litellm, "acompletion", completion)
    class Result(BaseModel):
        answer: str
    provider = LiteLLMGroqProvider(api_key="test", model=model, owner_id=owner)
    asyncio.run(provider.generate_structured(prompt="prompt", schema=Result) if structured
                else provider.generate_text(system="system", user="question"))
    expected = {
        "2026-10": budget.estimate_cost_usd(model=model, prompt_tokens=10, completion_tokens=20),
        "2026-11": budget.estimate_cost_usd(model=model, prompt_tokens=100, completion_tokens=100),
    }
    with session_factory() as db:
        assert {row.period: row.spend_usd for row in db.scalars(select(AiUsage))} == pytest.approx(expected)
        assert {row.period: row.spend_usd for row in db.scalars(select(LearnerAiUsage).where(
            LearnerAiUsage.owner_id == owner))} == pytest.approx(expected)


def test_global_fallback_reservation_and_refund_stay_in_original_month(monkeypatch):
    import app.ai.budget as budget
    import app.db.session as sessions

    current = ["2026-10"]
    monkeypatch.setattr(budget, "_period", lambda: current[0])
    monkeypatch.setattr(budget, "_fallback_spend_by_period", {})
    monkeypatch.setattr(budget, "get_settings", lambda: SimpleNamespace(
        aria_ai_monthly_budget_usd=1, aria_env="development"))
    def unavailable():
        raise RuntimeError("database unavailable")
    monkeypatch.setattr(sessions, "SessionLocal", unavailable)
    provider = LiteLLMGroqProvider(api_key="test", model="llama-3.3-70b-versatile")
    reserved, _ = provider._reserve_budgets(400)
    current[0] = "2026-11"
    budget.record_usage(model=provider.model, prompt_tokens=100, completion_tokens=100)
    expected_new = budget.spend_usd()
    provider._settle_global(reserved, (0, 0))
    assert budget.spend_usd() == pytest.approx(expected_new)
    current[0] = "2026-10"
    assert budget.spend_usd() == pytest.approx(0)
