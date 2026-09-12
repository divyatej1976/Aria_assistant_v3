"""Step 3 acceptance: simple read-aloud via existing TTS abstraction.

Frozen scope: note/resource raw text -> TTS -> audio_artifacts + progress.
Explicitly NOT Groq-scripted dialogue (Step 3b, deferred).
"""

import uuid

from fastapi.testclient import TestClient


class FakeTTS:
    def __init__(self) -> None:
        self.last_text: str | None = None

    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        self.last_text = text
        return b"FAKEAUDIO", "audio/mpeg", 10


class FailingTTS:
    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        raise RuntimeError("tts down")


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _context(client: TestClient, token: str) -> str:
    res = client.post(
        "/api/v1/contexts", headers=_headers(token), json={"title": "Audio ctx"}
    )
    assert res.status_code == 201
    return res.json()["id"]


def test_resource_to_audio_generate_and_play(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: FakeTTS())
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"step3-res-{tag}@example.com")
    ctx = _context(client, user["access_token"])
    created = client.post(
        "/api/v1/resources/text",
        headers=_headers(user["access_token"]),
        json={
            "context_id": ctx,
            "title": "Tides",
            "text": "Ocean tides follow lunar gravitational pull cycles every day.",
        },
    )
    assert created.status_code == 201
    resource_id = created.json()["id"]

    generated = client.post(
        f"/api/v1/audio/resources/{resource_id}/generate",
        headers=_headers(user["access_token"]),
    )
    assert generated.status_code == 201
    body = generated.json()
    assert body["status"] == "READY"
    assert body["source_type"] == "RESOURCE"
    assert "lunar gravitational" in body["text"]

    played = client.get(
        f"/api/v1/audio/{body['id']}/play", headers=_headers(user["access_token"])
    )
    assert played.status_code == 200
    assert played.content == b"FAKEAUDIO"


def test_failed_audio_play_returns_409(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: FailingTTS())
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"step3-fail-{tag}@example.com")
    ctx = _context(client, user["access_token"])
    note = client.post(
        "/api/v1/notes",
        headers=_headers(user["access_token"]),
        json={"context_id": ctx, "title": "N", "body": "Some note body here."},
    ).json()
    generated = client.post(
        f"/api/v1/audio/notes/{note['id']}/generate",
        headers=_headers(user["access_token"]),
    )
    assert generated.status_code == 201
    assert generated.json()["status"] == "FAILED"
    play = client.get(
        f"/api/v1/audio/{generated.json()['id']}/play",
        headers=_headers(user["access_token"]),
    )
    assert play.status_code == 409


def test_step3_uses_raw_text_no_llm(client: TestClient, monkeypatch) -> None:
    """Step 3 must not invoke the LLM; TTS receives raw source text verbatim."""
    import app.services.audio as audio
    import app.services.study as study

    fake = FakeTTS()
    monkeypatch.setattr(audio, "get_tts_provider", lambda: fake)

    def _boom():
        raise AssertionError("Step 3 must not call the LLM provider")

    monkeypatch.setattr(study, "get_llm_provider", _boom)
    monkeypatch.setattr("app.services.notes.get_llm_provider", _boom, raising=False)
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"step3-nollm-{tag}@example.com")
    ctx = _context(client, user["access_token"])
    body_text = "Raw read-aloud body text for verification purposes."
    note = client.post(
        "/api/v1/notes",
        headers=_headers(user["access_token"]),
        json={"context_id": ctx, "title": "N", "body": body_text},
    ).json()
    generated = client.post(
        f"/api/v1/audio/notes/{note['id']}/generate",
        headers=_headers(user["access_token"]),
    )
    assert generated.status_code == 201
    assert fake.last_text == body_text


def test_resource_delete_cascades_audio(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: FakeTTS())
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"step3-cascade-{tag}@example.com")
    ctx = _context(client, user["access_token"])
    created = client.post(
        "/api/v1/resources/text",
        headers=_headers(user["access_token"]),
        json={"context_id": ctx, "title": "Temp", "text": "Temporary material here."},
    ).json()
    artifact = client.post(
        f"/api/v1/audio/resources/{created['id']}/generate",
        headers=_headers(user["access_token"]),
    ).json()
    deleted = client.delete(
        f"/api/v1/resources/{created['id']}", headers=_headers(user["access_token"])
    )
    assert deleted.status_code == 200
    gone = client.get(
        f"/api/v1/audio/{artifact['id']}", headers=_headers(user["access_token"])
    )
    assert gone.status_code == 404


def test_tts_provider_selection(monkeypatch) -> None:
    import app.services.audio as audio
    from app.ai.providers import ChainedTTSProvider, LocalTTSProvider

    class _Settings:
        groq_api_key = None
        aria_tts_provider = "local"
        aria_tts_api_key = "sk-anything"
        aria_tts_model = "tts-model"
        aria_tts_voice = "voice"

    monkeypatch.setattr(audio, "get_settings", lambda: _Settings())
    assert type(audio.get_tts_provider()).__name__ == "LocalTTSProvider"

    _Settings.aria_tts_provider = "cloud"
    _Settings.aria_tts_api_key = None
    assert type(audio.get_tts_provider()).__name__ == "LocalTTSProvider"

    _Settings.aria_tts_api_key = "sk-key"
    assert type(audio.get_tts_provider()).__name__ == "CloudTTSProvider"

    _Settings.aria_tts_provider = "auto"
    _Settings.aria_tts_api_key = None
    provider = audio.get_tts_provider()
    assert isinstance(provider, ChainedTTSProvider)
    assert [type(p) for p in provider.providers] == [LocalTTSProvider]
