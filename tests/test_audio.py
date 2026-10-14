from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import LearningContext, Note
from app.services.audio import generate_audio

MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time. "
    "A precedence graph detects cycles that indicate non-serializable schedules. "
    "Conflict serializability is a subset of view serializability for most schedules. "
    "Deadlock detection requires waiting for a cycle in the resource wait-for graph."
)


def _context(db, owner_id):
    context = LearningContext(owner_id=owner_id, title="Audio test subject")
    db.add(context)
    db.flush()
    return context.id


def test_postgres_simultaneous_audio_claim_synthesizes_once(engine, session_factory, tmp_audio_storage):
    from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
    from threading import Barrier, Event, Lock

    from app.db.models import AudioArtifact

    if engine.dialect.name != "postgresql":
        pytest.skip("Requires independent PostgreSQL connections")
    owner, source = uuid4(), uuid4()
    with session_factory() as db:
        db.add(Note(id=source, owner_id=owner, context_id=_context(db, owner), title="Note", body=MATERIAL))
        db.add(AudioArtifact(owner_id=owner, source_id=source, source_type="NOTE", text=MATERIAL, status="PENDING"))
        db.commit()
    start, finish, lock = Barrier(2), Event(), Lock()
    calls = []

    class BlockingTTS(FakeTTS):
        def generate(self, *, text):
            with lock:
                calls.append(text)
            if not finish.wait(timeout=15):
                raise RuntimeError("Test did not release synthesis")
            return super().generate(text=text)

    def claim():
        with session_factory() as db:
            start.wait(timeout=10)
            artifact = generate_audio(db, owner_id=owner, source_type="NOTE", source_id=source,
                                      provider=BlockingTTS(), recovery=True)
            return artifact.status

    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(claim) for _ in range(2)]
        try:
            completed, _ = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
            assert len(completed) == 1
            assert next(iter(completed)).result() == "PROCESSING"
            assert len(calls) == 1
        finally:
            finish.set()
        assert sorted(future.result(timeout=10) for future in futures) == ["PROCESSING", "READY"]
    assert len(calls) == 1
    with session_factory() as db:
        from sqlalchemy import select

        artifacts = list(db.scalars(select(AudioArtifact)))
        assert len(artifacts) == 1
        assert artifacts[0].status == "READY"
        assert artifacts[0].generation_attempts == 1
    assert len(list(tmp_audio_storage.rglob("*.mp3"))) == 1


class FakeTTS:
    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        return b"FAKEAUDIO", "audio/mpeg", 10


class FailingTTS:
    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        raise RuntimeError("tts down")


@pytest.fixture()
def tmp_audio_storage(monkeypatch, tmp_path):
    """Isolate byte storage per test; never touch the repo working tree."""
    from app.services.audio_storage import LocalAudioStorage

    root = tmp_path / "audiofiles"
    monkeypatch.setattr(
        "app.services.audio.get_audio_storage", lambda: LocalAudioStorage(root)
    )
    return root


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


def test_audio_generation_service(engine, session_factory, tmp_audio_storage) -> None:
    with session_factory() as db:
        owner_id = uuid4()
        note = Note(
            id=uuid4(), owner_id=owner_id, context_id=_context(db, owner_id), title="N", body=MATERIAL
        )
        db.add(note)
        db.commit()

        artifact = generate_audio(
            db, owner_id=owner_id, source_type="NOTE", source_id=note.id, provider=FakeTTS()
        )
        assert artifact.status == "READY"
        # Bytes live in storage now, not the row: keeps tables and backups lean.
        assert artifact.storage_key
        assert artifact.audio_bytes is None
        assert artifact.content_type == "audio/mpeg"
        assert artifact.duration_seconds == 10
        stored = tmp_audio_storage / artifact.storage_key
        assert stored.is_file()
        assert stored.read_bytes() == b"FAKEAUDIO"

        failed = generate_audio(
            db, owner_id=owner_id, source_type="NOTE", source_id=note.id, provider=FailingTTS()
        )
        assert failed.status == "FAILED"
        assert failed.error_detail == "Audio generation failed. Please retry or check audio setup."

        retried = generate_audio(
            db, owner_id=owner_id, source_type="NOTE", source_id=note.id, provider=FakeTTS()
        )
        assert retried.status == "READY"
        assert retried.storage_key
        assert retried.audio_bytes is None


def test_audio_storage_failure_falls_back_to_db_bytes(
    engine, session_factory, tmp_audio_storage, monkeypatch
) -> None:
    """Storage outage must degrade to in-DB bytes, never fail generation."""

    class BrokenStorage:
        def save(self, **kwargs):
            raise OSError("disk gone")

        def load(self, key: str):
            return None

        def delete(self, key: str) -> None:
            pass

    monkeypatch.setattr(
        "app.services.audio.get_audio_storage", lambda: BrokenStorage()
    )
    with session_factory() as db:
        owner_id = uuid4()
        note = Note(
            id=uuid4(), owner_id=owner_id, context_id=_context(db, owner_id), title="N", body=MATERIAL
        )
        db.add(note)
        db.commit()
        artifact = generate_audio(
            db, owner_id=owner_id, source_type="NOTE", source_id=note.id, provider=FakeTTS()
        )
        assert artifact.status == "READY"
        assert artifact.storage_key is None
        assert artifact.audio_bytes == b"FAKEAUDIO"


def test_audio_from_text_saves_source_reuses_episode_and_isolates_owner(client, monkeypatch, tmp_audio_storage):
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: FakeTTS())
    token = register(client, "direct-audio@example.com")["access_token"]
    other = register(client, "other-direct-audio@example.com")["access_token"]
    cid = create_context(client, token)
    payload = {"context_id": cid, "title": "Direct episode", "text": MATERIAL}
    response = client.post("/api/v1/audio/text/generate", json=payload, headers=headers(token))
    assert response.status_code == 201, response.text
    artifact = response.json()
    assert artifact["status"] == "READY"
    assert artifact["text"] == MATERIAL
    retry = client.post("/api/v1/audio/text/generate", json=payload, headers=headers(token))
    assert retry.json()["id"] == artifact["id"]
    listed = client.get(f"/api/v1/audio?context_id={cid}", headers=headers(token)).json()
    assert len(listed) == 1 and listed[0]["title"] == "Direct episode"
    resources = client.get(f"/api/v1/resources?context_id={cid}", headers=headers(token)).json()
    assert len(resources) == 1
    assert client.post("/api/v1/audio/text/generate", json=payload, headers=headers(other)).status_code == 404
    assert client.get(f"/api/v1/audio/{artifact['id']}/play", headers=headers(other)).status_code == 404
    for text in ["   ", "x" * 20001]:
        assert client.post("/api/v1/audio/text/generate", json={**payload, "text": text}, headers=headers(token)).status_code == 422


def test_audio_from_chat_uses_ordered_owned_messages(client, monkeypatch, tmp_audio_storage, session_factory):
    from uuid import UUID

    from app.db.models import ConversationMessage, StudySession
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: FakeTTS())
    auth = register(client, "chat-audio@example.com")
    token = auth["access_token"]
    cid = create_context(client, token)
    owner = UUID(client.get("/api/v1/auth/me", headers=headers(token)).json()["id"])
    with session_factory() as db:
        session = StudySession(owner_id=owner, context_id=UUID(cid))
        db.add(session)
        db.flush()
        sid = str(session.id)
        db.add_all([ConversationMessage(owner_id=owner, study_session_id=session.id, role="assistant", content="A transaction is a unit of work.", position=1),
                    ConversationMessage(owner_id=owner, study_session_id=session.id, role="user", content="What is a transaction?", position=0)])
        db.commit()
    path = f"/api/v1/audio/sessions/{sid}/generate"
    response = client.post(path, headers=headers(token))
    assert response.status_code == 201, response.text
    assert response.json()["text"] == "You: What is a transaction?\n\nARIA: A transaction is a unit of work."
    assert client.post(path, headers=headers(token)).json()["id"] == response.json()["id"]
    other = register(client, "other-chat-audio@example.com")["access_token"]
    assert client.post(path, headers=headers(other)).status_code == 404
    with session_factory() as db:
        empty = StudySession(owner_id=owner, context_id=UUID(cid))
        db.add(empty)
        db.commit()
        empty_id = empty.id
    assert client.post(f"/api/v1/audio/sessions/{empty_id}/generate", headers=headers(token)).status_code == 422


def test_audio_generate_and_play(client: TestClient, monkeypatch, tmp_audio_storage) -> None:
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


def test_audio_isolation(client: TestClient, monkeypatch, tmp_audio_storage) -> None:
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


def test_audio_progress(client: TestClient, monkeypatch, tmp_audio_storage) -> None:
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


def test_audio_review_records_activity(client: TestClient, monkeypatch, tmp_audio_storage) -> None:
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


def test_transcribe_provider_failure_is_safe_in_http_and_logs(client, monkeypatch, caplog):
    from app.core.logging import configure_logging

    configure_logging()

    def fail(**kwargs):
        raise RuntimeError("confidential voice transcript gsk_private_provider_token")

    monkeypatch.setattr("app.api.routes.audio.transcribe_audio", fail)
    session = register(client, "stt-private-failure@example.com")
    response = client.post(
        "/api/v1/audio/transcribe",
        headers=headers(session["access_token"]),
        files={"file": ("voice.webm", b"voice", "audio/webm")},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Speech-to-text provider rejected the audio"}
    assert "confidential voice transcript" not in caplog.text
    assert "gsk_private_provider_token" not in caplog.text
    assert "error_type=RuntimeError" in caplog.text


def test_source_delete_cascades_audio(client: TestClient, monkeypatch, tmp_audio_storage) -> None:
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


def test_play_serves_storage_bytes_and_delete_removes_file(
    client: TestClient, monkeypatch, tmp_audio_storage
) -> None:
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: FakeTTS())
    session = register(client, "audio-store@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    note_id = create_note(client, token, context_id)
    artifact = client.post(
        f"/api/v1/audio/notes/{note_id}/generate", headers=headers(token)
    ).json()
    assert artifact["status"] == "READY"

    stored_files = list((tmp_audio_storage / session["learner_id"]).glob("*.mp3"))
    assert len(stored_files) == 1
    stored = stored_files[0]
    assert stored.is_file()

    played = client.get(f"/api/v1/audio/{artifact['id']}/play", headers=headers(token))
    assert played.status_code == 200
    assert played.content == b"FAKEAUDIO"

    deleted = client.delete(f"/api/v1/audio/{artifact['id']}", headers=headers(token))
    assert deleted.status_code == 200
    assert not stored.exists()


def test_play_falls_back_to_legacy_db_bytes(client: TestClient) -> None:
    """Rows written before file storage (audio_bytes, no storage_key) play on."""
    from uuid import UUID

    from app.db.dependencies import get_db
    from app.db.models import AudioArtifact
    from app.main import app

    session = register(client, "audio-legacy@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    note_id = create_note(client, token, context_id)

    db = next(app.dependency_overrides[get_db]())
    try:
        artifact = AudioArtifact(
            owner_id=UUID(session["learner_id"]),
            source_type="NOTE",
            source_id=UUID(note_id),
            text=MATERIAL,
            status="READY",
            audio_bytes=b"LEGACYBYTES",
            content_type="audio/mpeg",
            storage_key=None,
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
        artifact_id = str(artifact.id)
    finally:
        db.close()

    played = client.get(f"/api/v1/audio/{artifact_id}/play", headers=headers(token))
    assert played.status_code == 200
    assert played.content == b"LEGACYBYTES"


@pytest.mark.parametrize("recover", [False, True])
def test_active_audio_claim_excludes_foreground_and_queue(
    engine, session_factory, tmp_audio_storage, recover,
):
    from app.services.audio import process_audio_queue

    owner_id, source_id = uuid4(), uuid4()
    with session_factory() as db:
        db.add(Note(id=source_id, owner_id=owner_id, context_id=_context(db, owner_id), title="N", body=MATERIAL))
        db.commit()

        class NoDuplicateTTS:
            def generate(self, *, text):
                raise AssertionError("Active generation must not be duplicated")

        class DelayedTTS(FakeTTS):
            def generate(self, *, text):
                with session_factory() as worker:
                    if recover:
                        assert process_audio_queue(worker, provider=NoDuplicateTTS()) == 0
                    else:
                        overlapping = generate_audio(worker, owner_id=owner_id, source_type="NOTE",
                                                     source_id=source_id, provider=NoDuplicateTTS())
                        assert overlapping.status == "PROCESSING"
                return super().generate(text=text)

        artifact = generate_audio(db, owner_id=owner_id, source_type="NOTE",
                                  source_id=source_id, provider=DelayedTTS())
        assert artifact.status == "READY"
        assert artifact.generation_attempts == 1
        assert artifact.generation_token is None


def test_stale_worker_cannot_overwrite_recovered_audio(engine, session_factory, tmp_audio_storage):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select, update

    from app.db.models import AudioArtifact
    from app.services.audio import load_audio_bytes, process_audio_queue

    owner_id, source_id = uuid4(), uuid4()
    with session_factory() as db:
        db.add(Note(id=source_id, owner_id=owner_id, context_id=_context(db, owner_id), title="N", body=MATERIAL))
        db.commit()

        class SupersededTTS:
            def generate(self, *, text):
                with session_factory() as worker:
                    worker.execute(update(AudioArtifact).where(AudioArtifact.source_id == source_id)
                                   .values(lease_until=datetime.now(UTC) - timedelta(seconds=1)))
                    worker.commit()
                    assert process_audio_queue(worker, provider=FakeTTS()) == 1
                return b"STALE AUDIO", "audio/mpeg", 99

        artifact = generate_audio(db, owner_id=owner_id, source_type="NOTE",
                                  source_id=source_id, provider=SupersededTTS())
        assert artifact.status == "READY"
        assert artifact.duration_seconds == 10
        assert load_audio_bytes(artifact) == b"FAKEAUDIO"
        assert len(list(tmp_audio_storage.rglob("*.mp3"))) == 1
        assert len(list(db.scalars(select(AudioArtifact)))) == 1


def test_audio_crash_recovery_is_bounded(engine, session_factory, tmp_audio_storage):
    from app.db.models import AudioArtifact
    from app.services.audio import process_audio_queue

    with session_factory() as db:
        owner_id, source_id = uuid4(), uuid4()
        db.add(Note(id=source_id, owner_id=owner_id, context_id=_context(db, owner_id), title="N", body=MATERIAL))
        artifact = AudioArtifact(owner_id=owner_id, source_id=source_id, source_type="NOTE",
                                 text=MATERIAL, status="PROCESSING", generation_attempts=3)
        db.add(artifact)
        db.commit()
        assert process_audio_queue(db, provider=FakeTTS()) == 1
        db.refresh(artifact)
        assert artifact.status == "FAILED"
        assert "retry manually" in artifact.error_detail
        retried = generate_audio(db, owner_id=owner_id, source_type="NOTE", source_id=source_id,
                                 provider=FakeTTS())
        assert retried.status == "READY"
        assert retried.generation_attempts == 1



def test_audio_heartbeat_keeps_slow_work_out_of_recovery(
    engine, session_factory, tmp_audio_storage, monkeypatch,
):
    from datetime import UTC, datetime
    from threading import Event

    from sqlalchemy import select

    from app.db.models import AudioArtifact
    from app.services.audio import process_audio_queue

    monkeypatch.setattr("app.services.audio.LEASE_SECONDS", 0.4)
    owner_id, source_id = uuid4(), uuid4()
    with session_factory() as db:
        db.add(Note(id=source_id, owner_id=owner_id, context_id=_context(db, owner_id), title="N", body=MATERIAL))
        db.commit()

        class SlowTTS(FakeTTS):
            def generate(self, *, text):
                Event().wait(0.6)
                with session_factory() as worker:
                    lease = worker.scalar(select(AudioArtifact.lease_until))
                    if lease.tzinfo is None:
                        lease = lease.replace(tzinfo=UTC)
                    assert lease > datetime.now(UTC)
                    assert process_audio_queue(worker, provider=FakeTTS()) == 0
                return super().generate(text=text)

        artifact = generate_audio(db, owner_id=owner_id, source_type="NOTE",
                                  source_id=source_id, provider=SlowTTS())
        assert artifact.status == "READY"
