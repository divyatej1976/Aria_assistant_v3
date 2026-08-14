"""Phase 12.5 AI governance: prompt registry, provider factory, budget."""

import time
from types import SimpleNamespace

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
