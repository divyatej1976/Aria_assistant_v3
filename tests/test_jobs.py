"""Phase 12.2 background worker tests: aggregate reminders and audio queue."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import AudioArtifact
from app.services.audio import process_audio_queue
from app.services.notifications import check_reminders_for_all

MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time."
)


class FakeTTS:
    def generate(self, *, text: str):
        return b"audio-bytes", "audio/mpeg", 1


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _session(engine) -> Session:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return factory()


def test_check_reminders_for_all_aggregates_across_learners(
    client: TestClient, engine
) -> None:
    first = register(client, "job-a@example.com")
    second = register(client, "job-b@example.com")

    for token in (first["access_token"], second["access_token"]):
        context = client.post(
            "/api/v1/contexts",
            headers=headers(token),
            json={"title": "DBMS", "description": "Reminder test"},
        ).json()
        client.post(
            "/api/v1/planner/deadlines",
            headers=headers(token),
            json={
                "context_id": context["id"],
                "title": "DBMS End Sem",
                "due_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
                "reminder_days_before": 5,
            },
        )

    session = _session(engine)
    try:
        result = check_reminders_for_all(session)
    finally:
        session.close()

    assert set(result) == {
        "notifications_created",
        "emails_delivered",
        "emails_logged",
        "emails_failed",
    }
    assert result["notifications_created"] >= 2


def test_process_audio_queue_generates_pending_artifacts(
    client: TestClient, engine, monkeypatch, tmp_path
) -> None:
    from app.services.audio_storage import LocalAudioStorage

    monkeypatch.setattr(
        "app.services.audio.get_audio_storage",
        lambda: LocalAudioStorage(tmp_path / "audiofiles"),
    )
    session_data = register(client, "job-audio@example.com")
    token = session_data["access_token"]
    context = client.post(
        "/api/v1/contexts",
        headers=headers(token),
        json={"title": "DBMS", "description": "Audio queue test"},
    ).json()
    note = client.post(
        "/api/v1/notes",
        headers=headers(token),
        json={"context_id": context["id"], "title": "Locks", "body": MATERIAL},
    ).json()

    session = _session(engine)
    try:
        session.add(
            AudioArtifact(
                owner_id=UUID(session_data["learner_id"]),
                source_type="NOTE",
                source_id=UUID(note["id"]),
                text=MATERIAL,
                status="PROCESSING",
            )
        )
        session.commit()

        processed = process_audio_queue(session, provider=FakeTTS())
        assert processed == 1

        artifact = session.query(AudioArtifact).first()
        assert artifact.status == "READY"
        assert artifact.storage_key
        assert artifact.audio_bytes is None
    finally:
        session.close()


def test_scheduler_noop_when_disabled(monkeypatch) -> None:
    from app.jobs.scheduler import scheduler_instance, start_scheduler

    class Settings:
        aria_scheduler_enabled = False
        aria_reminder_check_interval_minutes = 60
        aria_audio_queue_interval_seconds = 30

    monkeypatch.setattr("app.jobs.scheduler.get_settings", lambda: Settings())
    start_scheduler()
    assert scheduler_instance().running is False


def test_advisory_lock_guards_against_replicas(engine) -> None:
    from app.jobs.scheduler import _release_advisory_lock, _try_advisory_lock

    first = engine.connect()
    second = engine.connect()
    key = 4242
    try:
        assert _try_advisory_lock(first, key) is True
        held_by_second = _try_advisory_lock(second, key)
        if engine.dialect.name == "postgresql":
            assert held_by_second is False
        else:
            assert held_by_second is True  # SQLite: single-instance fallback
    finally:
        _release_advisory_lock(first, key)
        _release_advisory_lock(second, key)
        first.close()
        second.close()


def test_run_locked_skips_when_lock_held(engine) -> None:
    from app.jobs.scheduler import _release_advisory_lock, _run_locked, _try_advisory_lock

    key = 4243
    holder = engine.connect()
    try:
        assert _try_advisory_lock(holder, key) is True
        calls: list[str] = []

        def work() -> None:
            calls.append("ran")

        if engine.dialect.name == "postgresql":
            assert _run_locked(engine, key=key, work=work) is False
            assert calls == []
        else:
            # SQLite cannot hold a real advisory lock; the job always runs.
            assert _run_locked(engine, key=key, work=work) is True
            assert calls == ["ran"]
    finally:
        _release_advisory_lock(holder, key)
        holder.close()


def test_advisory_lock_postgres_failure_is_not_bypassed(engine, monkeypatch) -> None:
    import pytest

    from app.jobs.scheduler import _try_advisory_lock

    if engine.dialect.name != "postgresql":
        return  # SQLite is always-acquired by design (single instance)

    connection = engine.connect()

    def boom(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(connection, "execute", boom)
    try:
        # A real DB failure must propagate (fail closed) rather than silently
        # treating the lock as acquired and running the job on every replica.
        with pytest.raises(RuntimeError):
            _try_advisory_lock(connection, 4244)
    finally:
        connection.close()
