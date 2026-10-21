"""Replies stream as they are written, then are saved exactly like a normal reply."""

import json
from uuid import UUID, uuid4

from sqlalchemy import select
from tests.test_resources_study import create_context, headers, register

from app.db.models import ConversationMessage
from app.services.study import StudyResult


def setup_chat(client, email):
    token = register(client, email)["access_token"]
    context = create_context(client, token)
    session = client.post("/api/v1/study/sessions", headers=headers(token), json={"context_id": context}).json()["id"]
    return token, session


def read_events(response) -> list[dict]:
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_reply_streams_in_pieces_then_is_saved(client, session_factory, monkeypatch):
    async def answer(*args, on_delta=None, **kwargs):
        for piece in ["### Foreign keys\n", "A foreign key ", "points at another table's key."]:
            on_delta(piece)
        return StudyResult("### Foreign keys\nA foreign key points at another table's key.", [], False)
    monkeypatch.setattr("app.services.study_requests.answer_question", answer)
    token, session = setup_chat(client, "stream@example.com")
    body = {"content": "What is a foreign key?", "request_id": str(uuid4())}

    response = client.post(f"/api/v1/study/sessions/{session}/messages/stream", headers=headers(token), json=body)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    events = read_events(response)
    assert [e["text"] for e in events if e["type"] == "delta"] == [
        "### Foreign keys\n", "A foreign key ", "points at another table's key."]
    assert events[-1]["type"] == "done"
    assert events[-1]["message"]["content"].startswith("### Foreign keys")
    with session_factory() as db:
        saved = list(db.scalars(select(ConversationMessage).where(
            ConversationMessage.study_session_id == UUID(session)).order_by(ConversationMessage.position)))
        assert [m.role for m in saved] == ["user", "assistant"]
    # A retry of the same request replays the saved reply instead of answering again.
    replay = read_events(client.post(f"/api/v1/study/sessions/{session}/messages/stream", headers=headers(token), json=body))
    assert replay[-1]["type"] == "done" and replay[-1]["message"]["content"] == events[-1]["message"]["content"]


def test_stopped_stream_ends_with_an_error_event_and_saves_nothing(client, session_factory, monkeypatch):
    token, session = setup_chat(client, "stream-stop@example.com")
    request_id = str(uuid4())

    async def answer(*args, on_delta=None, **kwargs):
        on_delta("Partial ")
        from app.services.study_requests import stop_reply
        stop_reply(session_id=UUID(session), request_id=UUID(request_id))
        return StudyResult("Partial answer", [], False)
    monkeypatch.setattr("app.services.study_requests.answer_question", answer)

    events = read_events(client.post(f"/api/v1/study/sessions/{session}/messages/stream", headers=headers(token),
                                     json={"content": "Explain joins", "request_id": request_id}))

    assert events[-1] == {"type": "error", "status": 409, "detail": "Stopped. Nothing was saved."}
    with session_factory() as db:
        assert list(db.scalars(select(ConversationMessage).where(
            ConversationMessage.study_session_id == UUID(session)))) == []


def test_streaming_needs_a_request_id_and_an_owned_chat(client):
    token, session = setup_chat(client, "stream-rules@example.com")
    url = f"/api/v1/study/sessions/{session}/messages/stream"
    assert client.post(url, headers=headers(token), json={"content": "hi"}).status_code == 422
    stranger = register(client, "stream-stranger@example.com")["access_token"]
    assert client.post(url, headers=headers(stranger), json={"content": "hi", "request_id": str(uuid4())}).status_code == 404


def test_provider_streams_pieces_and_returns_the_full_text(monkeypatch):
    import asyncio

    import litellm

    from app.ai.providers import LiteLLMGroqProvider

    real = litellm.acompletion

    async def mocked(**kwargs):
        return await real(**kwargs, mock_response="Indexes speed up lookups by keeping keys sorted.")
    monkeypatch.setattr(litellm, "acompletion", mocked)
    pieces: list[str] = []
    provider = LiteLLMGroqProvider(api_key="test", model="gemini-2.5-flash", route="gemini")
    monkeypatch.setattr(provider, "_begin", lambda prompt_chars: (None, None))
    monkeypatch.setattr(provider, "_settle", lambda *args: None)
    monkeypatch.setattr(provider, "_log_call", lambda **kwargs: (0, 0))

    text = asyncio.run(provider.generate_text(system="s", user="u", on_delta=pieces.append))

    assert text == "Indexes speed up lookups by keeping keys sorted."
    assert len(pieces) > 1 and "".join(pieces) == text  # arrived in several pieces
