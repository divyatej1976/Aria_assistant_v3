from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time. "
    "A precedence graph detects cycles that indicate non-serializable schedules. "
    "Conflict serializability is a subset of view serializability for most schedules. "
    "Deadlock detection requires waiting for a cycle in the resource wait-for graph."
)


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
        json={"title": "DBMS", "description": "Planner tests"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def add_material(client: TestClient, token: str, context_id: str) -> str:
    response = client.post(
        "/api/v1/resources/text",
        headers=headers(token),
        json={"context_id": context_id, "title": "Locks", "text": MATERIAL},
    )
    assert response.status_code == 201
    return response.json()["id"]


def now() -> datetime:
    return datetime.now(UTC)


def create_deadline(
    client: TestClient, token: str, context_id: str, *, days: int = 5
) -> dict:
    response = client.post(
        "/api/v1/planner/deadlines",
        headers=headers(token),
        json={
            "context_id": context_id,
            "title": "DBMS End Sem",
            "due_at": (now() + timedelta(days=days)).isoformat(),
            "reminder_days_before": 5,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_deadline_crud_and_isolation(client: TestClient) -> None:
    first = register(client, "plan-a@example.com")
    second = register(client, "plan-b@example.com")
    context_id = create_context(client, first["access_token"])
    deadline = create_deadline(client, first["access_token"], context_id, days=10)
    deadline_id = deadline["id"]

    listed = client.get(
        f"/api/v1/planner/deadlines?context_id={context_id}",
        headers=headers(first["access_token"]),
    )
    assert len(listed.json()) == 1

    isolated = client.get(
        f"/api/v1/planner/deadlines?context_id={context_id}",
        headers=headers(second["access_token"]),
    )
    assert isolated.status_code == 404

    completed = client.post(
        f"/api/v1/planner/deadlines/{deadline_id}/complete",
        headers=headers(first["access_token"]),
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "DONE"

    deleted = client.delete(
        f"/api/v1/planner/deadlines/{deadline_id}",
        headers=headers(first["access_token"]),
    )
    assert deleted.status_code == 200


def test_planned_task_complete_records_activity(client: TestClient) -> None:
    session = register(client, "plan-task@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    created = client.post(
        "/api/v1/planner/tasks",
        headers=headers(token),
        json={"context_id": context_id, "title": "Revise locks note"},
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    completed = client.post(
        f"/api/v1/planner/tasks/{task_id}/complete", headers=headers(token)
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "DONE"

    activity = client.get("/api/v1/progress/activity", headers=headers(token))
    assert any(item["activity_type"] == "planned_task" for item in activity.json())

    badges = client.get("/api/v1/progress/badges", headers=headers(token)).json()
    catalog = {item["code"]: item for item in badges}
    assert catalog["first_planned_task"]["earned"] is True


def test_upcoming_and_missed(client: TestClient) -> None:
    session = register(client, "plan-upcoming@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    create_deadline(client, token, context_id, days=3)

    upcoming = client.get("/api/v1/planner/upcoming?days=14", headers=headers(token))
    assert len(upcoming.json()) == 1
    assert upcoming.json()[0]["title"] == "DBMS End Sem"

    client.post(
        "/api/v1/planner/tasks",
        headers=headers(token),
        json={
            "context_id": context_id,
            "title": "Overdue task",
            "due_at": (now() - timedelta(days=1)).isoformat(),
        },
    )
    missed = client.get("/api/v1/planner/missed", headers=headers(token))
    assert [task["title"] for task in missed.json()] == ["Overdue task"]


def test_exam_reminder_created_and_deduped(client: TestClient) -> None:
    session = register(client, "plan-reminder@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    create_deadline(client, token, context_id, days=5)

    first = client.post("/api/v1/planner/reminders/check", headers=headers(token))
    assert first.status_code == 200
    assert first.json()["notifications_created"] == 1
    assert first.json()["emails_sent"] == 1  # no SMTP -> log provider "sends" to the log

    notifications = client.get("/api/v1/notifications", headers=headers(token)).json()
    reminder = notifications[0]
    assert reminder["ntype"] == "deadline"
    assert "DBMS End Sem in 5 days" in reminder["title"]
    assert "Syllabus so far" in reminder["body"]
    assert "concepts supported" in reminder["body"]

    second = client.post("/api/v1/planner/reminders/check", headers=headers(token))
    assert second.json()["notifications_created"] == 0


def test_digest_sent_once_per_day(client: TestClient) -> None:
    session = register(client, "plan-digest@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    client.post(
        "/api/v1/planner/tasks",
        headers=headers(token),
        json={
            "context_id": context_id,
            "title": "Overdue chapter",
            "due_at": (now() - timedelta(days=2)).isoformat(),
        },
    )

    first = client.post("/api/v1/planner/reminders/check", headers=headers(token))
    assert first.json()["notifications_created"] == 1
    notifications = client.get("/api/v1/notifications", headers=headers(token)).json()
    assert any(item["ntype"] == "digest" for item in notifications)
    digest = next(item for item in notifications if item["ntype"] == "digest")
    assert "Missed planned work" in digest["body"]

    second = client.post("/api/v1/planner/reminders/check", headers=headers(token))
    assert second.json()["notifications_created"] == 0


def test_email_preference_disables_sending(client: TestClient) -> None:
    session = register(client, "plan-nomail@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    create_deadline(client, token, context_id, days=5)
    client.put(
        "/api/v1/me/preferences",
        headers=headers(token),
        json={"key": "email_reminders", "value": "off"},
    )

    result = client.post("/api/v1/planner/reminders/check", headers=headers(token)).json()
    assert result["notifications_created"] == 1
    assert result["emails_sent"] == 0


def test_notifications_read(client: TestClient) -> None:
    session = register(client, "plan-read@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    create_deadline(client, token, context_id, days=5)
    client.post("/api/v1/planner/reminders/check", headers=headers(token))

    unread = client.get("/api/v1/notifications/unread-count", headers=headers(token))
    assert unread.json()["unread"] == 1

    notifications = client.get("/api/v1/notifications", headers=headers(token)).json()
    read = client.post(
        f"/api/v1/notifications/{notifications[0]['id']}/read", headers=headers(token)
    )
    assert read.status_code == 200

    unread = client.get("/api/v1/notifications/unread-count", headers=headers(token))
    assert unread.json()["unread"] == 0
