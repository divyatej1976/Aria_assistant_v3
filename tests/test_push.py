"""Phase 12.3 notifications & push: subscriptions, dispatch, triggers."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.services.notifications import dispatch_notification

MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time. "
    "A precedence graph detects cycles that indicate non-serializable schedules. "
    "Conflict serializability is a subset of view serializability for most schedules. "
    "Deadlock detection requires waiting for a cycle in the resource wait-for graph."
)

SUB = {
    "endpoint": "https://push.example.com/send/abc",
    "p256dh": "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkRxZ8sE2bW0vNxXkG",
    "auth": "pTkY0qR6PJk0f0Cg",
}


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_push_subscribe_list_unsubscribe(client: TestClient) -> None:
    session = register(client, "push@example.com")
    token = session["access_token"]

    created = client.post(
        "/api/v1/push/subscribe", headers=headers(token), json=SUB
    )
    assert created.status_code == 201
    assert created.json()["endpoint"] == SUB["endpoint"]

    listed = client.get("/api/v1/push/subscriptions", headers=headers(token)).json()
    assert len(listed) == 1

    removed = client.post(
        "/api/v1/push/unsubscribe", headers=headers(token), json=SUB
    ).json()
    assert removed["unsubscribed"] is True
    assert client.get("/api/v1/push/subscriptions", headers=headers(token)).json() == []


def test_push_subscriptions_are_isolated_between_learners(client: TestClient) -> None:
    first = register(client, "push-a@example.com")
    client.post("/api/v1/push/subscribe", headers=headers(first["access_token"]), json=SUB)
    second = register(client, "push-b@example.com")
    listed = client.get(
        "/api/v1/push/subscriptions", headers=headers(second["access_token"])
    ).json()
    assert listed == []


def test_dispatch_notification_creates_in_app_and_logs_push(client: TestClient, engine) -> None:
    session = register(client, "dispatch@example.com")
    token = session["access_token"]
    client.post("/api/v1/push/subscribe", headers=headers(token), json=SUB)

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db: Session = factory()
    try:
        result = dispatch_notification(
            db,
            owner_id=UUID(session["learner_id"]),
            ntype="test",
            title="Hello",
            body="A test notification",
        )
    finally:
        db.close()

    assert result["push_logged"] >= 1
    assert result["push_sent"] == 0

    notifications = client.get("/api/v1/notifications", headers=headers(token)).json()
    assert any(item["title"] == "Hello" for item in notifications)

    unread = client.get("/api/v1/notifications/unread-count", headers=headers(token)).json()
    assert unread["unread"] >= 1

    marked = client.post("/api/v1/notifications/read-all", headers=headers(token)).json()
    assert marked["marked"] >= 1
    after = client.get("/api/v1/notifications/unread-count", headers=headers(token)).json()
    assert after["unread"] == 0


def test_workflow_completion_creates_notification(client: TestClient) -> None:
    session = register(client, "wf-notify@example.com")
    token = session["access_token"]
    context = client.post(
        "/api/v1/contexts", headers=headers(token), json={"title": "DBMS"}
    ).json()
    client.post(
        "/api/v1/resources/text",
        headers=headers(token),
        json={"context_id": context["id"], "title": "Locks", "text": MATERIAL},
    )
    started = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers=headers(token),
        json={"payload": {"context_id": context["id"]}},
    )
    assert started.status_code == 201

    notifications = client.get("/api/v1/notifications", headers=headers(token)).json()
    assert any(item["ntype"] == "workflow" for item in notifications)


def test_assessment_submit_creates_notification(client: TestClient) -> None:
    session = register(client, "assess-notify@example.com")
    token = session["access_token"]
    context = client.post(
        "/api/v1/contexts", headers=headers(token), json={"title": "DBMS"}
    ).json()
    client.post(
        "/api/v1/resources/text",
        headers=headers(token),
        json={"context_id": context["id"], "title": "Locks", "text": MATERIAL},
    )
    created = client.post(
        "/api/v1/assessments",
        headers=headers(token),
        json={
            "context_id": context["id"],
            "format": "mcq",
            "question_count": 3,
            "difficulty": "medium",
        },
    ).json()
    started = client.post(
        f"/api/v1/assessments/{created['id']}/attempts", headers=headers(token)
    ).json()
    client.post(
        f"/api/v1/assessments/{created['id']}/attempts/{started['attempt_id']}/submit",
        headers=headers(token),
        json={
            "idempotency_key": "notify-key-0001",
            "answers": {q["id"]: "A" for q in started["questions"]},
        },
    )

    notifications = client.get("/api/v1/notifications", headers=headers(token)).json()
    assert any(item["ntype"] == "assessment_result" for item in notifications)
