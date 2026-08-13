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
    client: TestClient, engine
) -> None:
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
        assert artifact.audio_bytes == b"audio-bytes"
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
