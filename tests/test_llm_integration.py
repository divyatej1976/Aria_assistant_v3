"""Step 1 acceptance: global Groq provider integration and failure/fallback.

Covers the frozen Step 1 gates:
- Valid Groq response -> fallback_used=False
- Missing key -> deterministic fallback
- Provider timeout/error -> safe fallback, no key or prompt leakage
- Malformed (empty) provider response -> safe fallback
- Budget exceeded -> provider is not called
"""

import uuid

from fastapi.testclient import TestClient

from app.ai.budget import BudgetExceeded, reset_budget


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup_material(client: TestClient, token: str) -> str:
    ctx = client.post(
        "/api/v1/contexts",
        headers=_headers(token),
        json={"title": "Physics", "description": "Study material"},
    )
    assert ctx.status_code == 201
    context_id = ctx.json()["id"]
    res = client.post(
        "/api/v1/resources/text",
        headers=_headers(token),
        json={
            "context_id": context_id,
            "title": "Newton",
            "text": "Newton's first law states that an object at rest stays at rest unless "
            "acted upon by a net external force. Inertia describes this resistance.",
        },
    )
    assert res.status_code == 201
    session = client.post(
        "/api/v1/study/sessions",
        headers=_headers(token),
        json={"context_id": context_id},
    )
    assert session.status_code == 201
    return session.json()["id"]


class _OkProvider:
    async def generate_text(self, *, system: str, user: str, prompt_version=None) -> str:
        return "Grounded answer about inertia from your material."

    async def generate_structured(self, *, prompt: str, schema: type, prompt_version=None):
        raise NotImplementedError


class _FailingProvider:
    async def generate_text(self, *, system: str, user: str, prompt_version=None) -> str:
        raise TimeoutError("groq simulated timeout with secret=gsk-super-secret-key")

    async def generate_structured(self, *, prompt: str, schema: type, prompt_version=None):
        raise TimeoutError("timeout")


class _EmptyProvider:
    async def generate_text(self, *, system: str, user: str, prompt_version=None) -> str:
        return "   "

    async def generate_structured(self, *, prompt: str, schema: type, prompt_version=None):
        return None


class _SpyProvider(_OkProvider):
    def __init__(self) -> None:
        self.calls = 0

    async def generate_text(self, *, system: str, user: str, prompt_version=None) -> str:
        self.calls += 1
        return await super().generate_text(system=system, user=user)


def _ask(client: TestClient, token: str, session_id: str) -> dict:
    response = client.post(
        f"/api/v1/study/sessions/{session_id}/messages",
        headers=_headers(token),
        json={"content": "What does Newton's first law say about rest?"},
    )
    assert response.status_code == 200
    return response.json()


def _ask_content(client: TestClient, token: str, session_id: str, content: str) -> dict:
    response = client.post(
        f"/api/v1/study/sessions/{session_id}/messages",
        headers=_headers(token),
        json={"content": content},
    )
    assert response.status_code == 200
    return response.json()


def test_greeting_without_provider_uses_friendly_deterministic_reply(
    client: TestClient, monkeypatch
) -> None:
    import app.services.study as study

    data = _register(client, f"step1-greet-{uuid.uuid4().hex[:8]}@example.com")
    session_id = _setup_material(client, data["access_token"])
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: None)
    body = _ask_content(client, data["access_token"], session_id, "Hi there!")
    assert body["fallback_used"] is True
    assert "could not find enough relevant information" not in body["content"]
    assert "ARIA" in body["content"]


def test_greeting_with_provider_answers_conversationally(
    client: TestClient, monkeypatch
) -> None:
    import app.services.study as study

    data = _register(client, f"step1-greetlive-{uuid.uuid4().hex[:8]}@example.com")
    session_id = _setup_material(client, data["access_token"])
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: _OkProvider())
    body = _ask_content(client, data["access_token"], session_id, "hello!")
    assert body["fallback_used"] is False
    assert "could not find enough relevant information" not in body["content"]
    assert body["content"].strip() != ""


def test_greeting_with_failing_provider_still_greets_safely(
    client: TestClient, monkeypatch
) -> None:
    import app.services.study as study

    data = _register(client, f"step1-greetfail-{uuid.uuid4().hex[:8]}@example.com")
    session_id = _setup_material(client, data["access_token"])
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: _FailingProvider())
    body = _ask_content(client, data["access_token"], session_id, "hey")
    assert body["fallback_used"] is True
    assert "could not find enough relevant information" not in body["content"]
    assert "gsk-super-secret" not in body["content"]


def test_valid_provider_returns_grounded_answer(client: TestClient, monkeypatch) -> None:
    import app.services.study as study

    data = _register(client, f"step1-ok-{uuid.uuid4().hex[:8]}@example.com")
    session_id = _setup_material(client, data["access_token"])
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: _OkProvider())
    body = _ask(client, data["access_token"], session_id)
    assert body["fallback_used"] is False
    assert "inertia" in body["content"].lower()
    assert body["sources"]


def test_missing_key_uses_deterministic_fallback(client: TestClient, monkeypatch) -> None:
    import app.services.study as study

    data = _register(client, f"step1-missing-{uuid.uuid4().hex[:8]}@example.com")
    session_id = _setup_material(client, data["access_token"])
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: None)
    body = _ask(client, data["access_token"], session_id)
    assert body["fallback_used"] is True
    assert "Provider fallback" in body["content"]


def test_provider_error_falls_back_without_leaking_key(client: TestClient, monkeypatch) -> None:
    import app.services.study as study

    data = _register(client, f"step1-err-{uuid.uuid4().hex[:8]}@example.com")
    session_id = _setup_material(client, data["access_token"])
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: _FailingProvider())
    body = _ask(client, data["access_token"], session_id)
    assert body["fallback_used"] is True
    assert "temporarily unavailable" in body["content"]
    assert "gsk-super-secret" not in body["content"]
    assert "secret" not in body["content"].lower()


def test_malformed_empty_response_falls_back(client: TestClient, monkeypatch) -> None:
    import app.services.study as study

    data = _register(client, f"step1-empty-{uuid.uuid4().hex[:8]}@example.com")
    session_id = _setup_material(client, data["access_token"])
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: _EmptyProvider())
    body = _ask(client, data["access_token"], session_id)
    assert body["fallback_used"] is True
    assert body["content"].strip() != ""


def test_budget_exceeded_provider_is_not_called(client: TestClient, monkeypatch) -> None:
    import app.ai.providers as providers_module
    import app.services.study as study

    data = _register(client, f"step1-budget-{uuid.uuid4().hex[:8]}@example.com")
    session_id = _setup_material(client, data["access_token"])
    spy = _SpyProvider()
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: spy)

    async def _blocked(*args, **kwargs):
        raise BudgetExceeded("Monthly AI budget has been reached")

    monkeypatch.setattr(providers_module, "acompletion", None, raising=False)
    # Force budget gate inside a thin wrapper: patch assert_within_budget used by real provider
    # path by making generate_text raise BudgetExceeded before any network call.
    async def _raising_generate_text(*, system: str, user: str, prompt_version=None) -> str:
        from app.ai.budget import assert_within_budget

        assert_within_budget()
        spy.calls += 1
        return "should not reach here"

    class _BudgetProvider:
        generate_structured = _EmptyProvider.generate_structured
        generate_text = staticmethod(_raising_generate_text)

    import app.ai.budget as budget

    reset_budget()
    monkeypatch.setattr(budget, "get_settings", lambda: type("S", (), {"aria_ai_monthly_budget_usd": 0.0000001})())
    budget.record_usage(model="llama-3.3-70b-versatile", prompt_tokens=100000, completion_tokens=100000)
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: _BudgetProvider())
    body = _ask(client, data["access_token"], session_id)
    assert body["fallback_used"] is True
    assert "temporarily unavailable" in body["content"]
    assert spy.calls == 0
    reset_budget()


def test_no_frontend_or_api_surface_exposes_groq_key() -> None:
    import pathlib

    repo = pathlib.Path(__file__).resolve().parents[1]
    for base in (repo / "frontend", repo / "frontend-v2"):
        if not base.exists():
            continue
        hits = []
        for pattern in ("*.ts", "*.tsx"):
            for p in base.rglob(pattern):
                if "node_modules" in p.parts or ".next" in p.parts:
                    continue
                try:
                    text = p.read_text(errors="ignore")
                except OSError:
                    continue
                if "groq_api_key" in text.lower():
                    hits.append(p)
        assert hits == [], f"frontend must never reference groq_api_key: {hits[:3]}"
    # Settings hides the key from repr/logs.
    from app.core.config import Settings

    assert Settings.model_fields["groq_api_key"].repr is False
