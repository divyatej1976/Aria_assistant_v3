import uuid

import pytest
from fastapi.testclient import TestClient

from app.services.response_style import resolve_style


@pytest.mark.parametrize(
    ("question", "depth"),
    [
        ("hey quick one, what's a tuple?", "quick"),
        ("what is a list?", "quick"),
        ("Explain decorators in detail with examples", "deep"),
        ("walk me through how the garbage collector frees memory", "deep"),
        ("How do Python generators differ from returning a list of values?", "balanced"),
    ],
)
def test_auto_depth_follows_the_question(question: str, depth: str) -> None:
    assert resolve_style(question).depth == depth


def test_explicit_depth_wins_over_tone() -> None:
    assert resolve_style("hey what's a tuple?", "deep").depth == "deep"
    assert resolve_style("Explain decorators in detail", "quick").depth == "quick"


@pytest.mark.parametrize(
    ("question", "tone"),
    [
        ("I don't get closures at all", "confused"),
        ("can you explain it simpler", "confused"),
        ("hey what's a dict", "casual"),
        ("Describe the difference between a process and a thread.", "neutral"),
    ],
)
def test_tone_detection(question: str, tone: str) -> None:
    assert resolve_style(question).tone == tone


def test_instruction_reflects_depth_tone_and_screen() -> None:
    text = resolve_style("I'm confused about recursion", "quick", "compact").instruction()
    assert text.startswith("Response style:")
    assert "2-4 short lines" in text
    assert "simpler words" in text
    assert "small screen" in text


class _CapturingProvider:
    def __init__(self) -> None:
        self.user = ""

    async def generate_text(self, *, system: str, user: str, prompt_version=None, temperature=0.0) -> str:
        self.user = user
        return "A tuple is an immutable sequence."

    async def generate_structured(self, *, prompt: str, schema: type, prompt_version=None):
        raise NotImplementedError


def test_depth_reaches_the_prompt_and_is_saved(client: TestClient, monkeypatch) -> None:
    import app.services.study as study

    auth = client.post(
        "/api/v1/auth/register",
        json={"email": f"depth-{uuid.uuid4().hex[:8]}@example.com", "password": "correct-horse",
              "display_name": "Depth Tester"},
    ).json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    ctx = client.post("/api/v1/contexts", headers=headers, json={"title": "Python"}).json()
    session = client.post("/api/v1/study/sessions", headers=headers, json={"context_id": ctx["id"]}).json()
    provider = _CapturingProvider()
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: provider)

    res = client.post(
        f"/api/v1/study/sessions/{session['id']}/messages",
        headers=headers,
        json={"content": "Tell me about tuples and when to use them", "depth": "deep",
              "screen": "compact", "request_id": str(uuid.uuid4())},
    )
    assert res.status_code == 200
    assert res.json()["depth"] == "deep"
    assert "Response style:" in provider.user
    assert "step-by-step" in provider.user
    assert "small screen" in provider.user

    messages = client.get(f"/api/v1/study/sessions/{session['id']}/messages", headers=headers).json()
    assert [m["depth"] for m in messages] == [None, "deep"]
