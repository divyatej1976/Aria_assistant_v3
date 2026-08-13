from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Note
from app.services.audio import generate_audio

MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time. "
    "A precedence graph detects cycles that indicate non-serializable schedules. "
    "Conflict serializability is a subset of view serializability for most schedules. "
    "Deadlock detection requires waiting for a cycle in the resource wait-for graph."
)


class FakeTTS:
    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        return b"FAKEAUDIO", "audio/mpeg", 10


class FailingTTS:
    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        raise RuntimeError("tts down")


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_context(client: TestClient, token: str) -> str:
    response = client.post(
        "/api/v1/contexts",
        headers=headers(token),
        json={"title": "DBMS", "description": "Audio tests"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_note(client: TestClient, token: str, context_id: str) -> str:
    response = client.post(
        "/api/v1/notes",
        headers=headers(token),
        json={"context_id": context_id, "title": "Locks note", "body": MATERIAL},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_audio_generation_service() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as db:
        owner_id = uuid4()
        note = Note(
            id=uuid4(), owner_id=owner_id, context_id=uuid4(), title="N", body=MATERIAL
        )
        db.add(note)
        db.commit()

        artifact = generate_audio(
            db, owner_id=owner_id, source_type="NOTE", source_id=note.id, provider=FakeTTS()
        )
        assert artifact.status == "READY"
        assert artifact.audio_bytes == b"FAKEAUDIO"
        assert artifact.content_type == "audio/mpeg"
        assert artifact.duration_seconds == 10

        failed = generate_audio(
            db, owner_id=owner_id, source_type="NOTE", source_id=note.id, provider=FailingTTS()
        )
        assert failed.status == "FAILED"
        assert failed.error_detail == "tts down"

        retried = generate_audio(
            db, owner_id=owner_id, source_type="NOTE", source_id=note.id, provider=FakeTTS()
        )
        assert retried.status == "READY"
        assert retried.audio_bytes == b"FAKEAUDIO"
    engine.dispose()


def test_audio_generate_and_play(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: FakeTTS())
    session = register(client, "audio@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    note_id = create_note(client, token, context_id)

    generated = client.post(
        f"/api/v1/audio/notes/{note_id}/generate", headers=headers(token)
    )
    assert generated.status_code == 201
    artifact = generated.json()
    assert artifact["status"] == "READY"
    assert artifact["duration_seconds"] == 10

    played = client.get(f"/api/v1/audio/{artifact['id']}/play", headers=headers(token))
    assert played.status_code == 200
    assert played.content == b"FAKEAUDIO"
    assert played.headers["content-type"].startswith("audio/mpeg")


def test_audio_isolation(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: FakeTTS())
    first = register(client, "audio-a@example.com")
    second = register(client, "audio-b@example.com")
    context_id = create_context(client, first["access_token"])
    note_id = create_note(client, first["access_token"], context_id)
    artifact = client.post(
        f"/api/v1/audio/notes/{note_id}/generate", headers=headers(first["access_token"])
    ).json()

    play = client.get(
        f"/api/v1/audio/{artifact['id']}/play", headers=headers(second["access_token"])
    )
    assert play.status_code == 404
    deleted = client.delete(
        f"/api/v1/audio/{artifact['id']}", headers=headers(second["access_token"])
    )
    assert deleted.status_code == 404


def test_audio_progress(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: FakeTTS())
    session = register(client, "audio-progress@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    note_id = create_note(client, token, context_id)
    artifact = client.post(
        f"/api/v1/audio/notes/{note_id}/generate", headers=headers(token)
    ).json()

    saved = client.put(
        f"/api/v1/audio/{artifact['id']}/progress",
        headers=headers(token),
        json={"position_seconds": 42, "completed": True},
    )
    assert saved.status_code == 200
    assert saved.json()["position_seconds"] == 42
    assert saved.json()["completed"] is True

    fetched = client.get(
        f"/api/v1/audio/{artifact['id']}/progress", headers=headers(token)
    )
    assert fetched.json()["position_seconds"] == 42


def test_audio_review_records_activity(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: FakeTTS())
    session = register(client, "audio-review@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    note_id = create_note(client, token, context_id)
    artifact = client.post(
        f"/api/v1/audio/notes/{note_id}/generate", headers=headers(token)
    ).json()

    reviewed = client.post(
        f"/api/v1/audio/{artifact['id']}/review", headers=headers(token)
    )
    assert reviewed.status_code == 200

    activity = client.get("/api/v1/progress/activity", headers=headers(token)).json()
    assert any(item["activity_type"] == "revision" for item in activity)
    consistency = client.get("/api/v1/progress/consistency", headers=headers(token)).json()
    assert consistency["today_active"] is True


def test_transcribe_requires_configuration(client: TestClient) -> None:
    session = register(client, "stt@example.com")
    response = client.post(
        "/api/v1/audio/transcribe",
        headers=headers(session["access_token"]),
        files={"file": ("voice.webm", b"\x1aE\xdf\xa3voice", "audio/webm")},
    )
    assert response.status_code == 422
    assert "not configured" in response.json()["detail"]


def test_source_delete_cascades_audio(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: FakeTTS())
    session = register(client, "audio-cascade@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    note_id = create_note(client, token, context_id)
    artifact = client.post(
        f"/api/v1/audio/notes/{note_id}/generate", headers=headers(token)
    ).json()

    deleted = client.delete(f"/api/v1/notes/{note_id}", headers=headers(token))
    assert deleted.status_code == 200

    gone = client.get(
        f"/api/v1/audio/{artifact['id']}", headers=headers(token)
    )
    assert gone.status_code == 404
