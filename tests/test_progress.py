from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.services.progress import consistency, record_activity

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
        json={"title": "DBMS", "description": "Progress tests"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def add_material(client: TestClient, token: str, context_id: str) -> None:
    response = client.post(
        "/api/v1/resources/text",
        headers=headers(token),
        json={"context_id": context_id, "title": "Locks", "text": MATERIAL},
    )
    assert response.status_code == 201


def test_register_does_not_count_as_activity(client: TestClient) -> None:
    session = register(client, "activity-none@example.com")
    activity = client.get("/api/v1/progress/activity", headers=headers(session["access_token"]))
    assert activity.status_code == 200
    assert activity.json() == []


def test_activity_recorded_and_deduped(client: TestClient) -> None:
    session = register(client, "activity@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    assessment = client.post(
        "/api/v1/assessments",
        headers=headers(token),
        json={
            "context_id": context_id,
            "format": "mcq",
            "question_count": 3,
            "difficulty": "medium",
        },
    )
    assessment_id = assessment.json()["id"]
    started = client.post(f"/api/v1/assessments/{assessment_id}/attempts", headers=headers(token))
    attempt_id = started.json()["attempt_id"]
    questions = started.json()["questions"]
    client.post(
        f"/api/v1/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        headers=headers(token),
        json={"idempotency_key": "key-progress-0001", "answers": {q["id"]: "A" for q in questions}},
    )

    activity = client.get("/api/v1/progress/activity", headers=headers(token))
    types = [item["activity_type"] for item in activity.json()]
    assert types.count("assessment") == 1

    client.post(
        "/api/v1/study/sessions",
        headers=headers(token),
        json={"context_id": context_id},
    )
    session_list = client.get(
        f"/api/v1/study/sessions?context_id={context_id}", headers=headers(token)
    ).json()
    session_id = session_list[0]["id"]
    client.post(
        f"/api/v1/study/sessions/{session_id}/messages",
        headers=headers(token),
        json={"content": "Explain two-phase locking"},
    )
    activity = client.get("/api/v1/progress/activity", headers=headers(token))
    types = [item["activity_type"] for item in activity.json()]
    assert "study" in types


def test_consistency_streaks(client: TestClient, engine, session_factory) -> None:
    session = register(client, "streak@example.com")
    token = session["access_token"]
    create_context(client, token)
    today = date(2026, 8, 13)

    owner_id = uuid4()
    with session_factory() as db:
        for offset in (0, 1, 2, 5, 6, 7):
            record_activity(
                db,
                owner_id=owner_id,
                activity_type="assessment",
                source_id=uuid4(),
                occurred_on=today - timedelta(days=offset),
            )
        result = consistency(db, owner_id=owner_id, today=today)

    assert result["current_streak"] == 3
    assert result["longest_streak"] == 3
    assert result["active_this_week"] == 5
    assert result["today_active"] is True
    heatmap = result["heatmap"]
    assert len(heatmap) == 182
    last = heatmap[-1]
    assert last["date"] == today.isoformat()
    assert last["count"] == 1


def test_badges_earn_on_read(client: TestClient) -> None:
    session = register(client, "badges@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    assessment = client.post(
        "/api/v1/assessments",
        headers=headers(token),
        json={
            "context_id": context_id,
            "format": "mcq",
            "question_count": 3,
            "difficulty": "medium",
        },
    ).json()
    started = client.post(
        f"/api/v1/assessments/{assessment['id']}/attempts", headers=headers(token)
    ).json()
    questions = started["questions"]
    client.post(
        f"/api/v1/assessments/{assessment['id']}/attempts/{started['attempt_id']}/submit",
        headers=headers(token),
        json={"idempotency_key": "key-badges-0001", "answers": {q["id"]: "A" for q in questions}},
    )

    earned = client.get("/api/v1/progress/badges", headers=headers(token))
    assert earned.status_code == 200
    catalog = {item["code"]: item for item in earned.json()}
    assert catalog["first_assessment"]["earned"] is True
    assert catalog["first_assessment"]["earned_at"] is not None
    assert catalog["first_study"]["earned"] is False

    again = client.get("/api/v1/progress/badges", headers=headers(token))
    assert [item["code"] for item in again.json() if item["earned"]] == [
        "first_assessment"
    ]


def test_timezone_preference_changes_local_today(client: TestClient) -> None:
    session = register(client, "tz@example.com")
    token = session["access_token"]
    client.put(
        "/api/v1/me/preferences",
        headers=headers(token),
        json={"key": "timezone", "value": "Asia/Kolkata"},
    )
    consistency_resp = client.get("/api/v1/progress/consistency", headers=headers(token))
    assert consistency_resp.status_code == 200
    assert "heatmap" in consistency_resp.json()


def test_progress_is_isolated(client: TestClient) -> None:
    first = register(client, "progress-a@example.com")
    second = register(client, "progress-b@example.com")
    context_id = create_context(client, first["access_token"])
    add_material(client, first["access_token"], context_id)
    assessment = client.post(
        "/api/v1/assessments",
        headers=headers(first["access_token"]),
        json={
            "context_id": context_id,
            "format": "mcq",
            "question_count": 3,
            "difficulty": "medium",
        },
    ).json()
    started = client.post(
        f"/api/v1/assessments/{assessment['id']}/attempts", headers=headers(first["access_token"])
    ).json()
    client.post(
        f"/api/v1/assessments/{assessment['id']}/attempts/{started['attempt_id']}/submit",
        headers=headers(first["access_token"]),
        json={"idempotency_key": "key-iso-0001", "answers": {}},
    )
    second_activity = client.get(
        "/api/v1/progress/activity", headers=headers(second["access_token"])
    )
    assert second_activity.json() == []
    second_consistency = client.get(
        "/api/v1/progress/consistency", headers=headers(second["access_token"])
    ).json()
    assert second_consistency["current_streak"] == 0
