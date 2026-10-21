"""Cross-owner reference guards: another learner's IDs must be rejected.

Ownership is enforced in the route/service layer (the DB does not enforce
cross-owner composite FKs), so these API-level tests document that boundary and
prevent regressions where a record references another learner's context or
resource.
"""

from fastapi.testclient import TestClient

MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time. "
    "A precedence graph detects cycles that indicate non-serializable schedules."
)


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-9", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _two_learners(client: TestClient) -> tuple[dict[str, str], str]:
    first = register(client, "owner-a@example.com")
    second = register(client, "owner-b@example.com")
    context = client.post(
        "/api/v1/contexts",
        headers=headers(second["access_token"]),
        json={"title": "B's private context"},
    ).json()
    return first, context["id"]


def test_cannot_reference_another_learners_context(client: TestClient) -> None:
    first, other_context_id = _two_learners(client)
    token = first["access_token"]

    deadline = client.post(
        "/api/v1/planner/deadlines",
        headers=headers(token),
        json={
            "context_id": other_context_id,
            "title": "Sneaky deadline",
            "due_at": "2030-01-01T00:00:00Z",
            "reminder_days_before": 5,
        },
    )
    assert deadline.status_code == 404

    task = client.post(
        "/api/v1/planner/tasks",
        headers=headers(token),
        json={"context_id": other_context_id, "title": "Sneaky task"},
    )
    assert task.status_code == 404

    resource = client.post(
        "/api/v1/resources/text",
        headers=headers(token),
        json={"context_id": other_context_id, "title": "Sneaky resource", "text": MATERIAL},
    )
    assert resource.status_code == 404

    note = client.post(
        "/api/v1/notes",
        headers=headers(token),
        json={"context_id": other_context_id, "title": "Sneaky note", "body": MATERIAL},
    )
    assert note.status_code == 404

    assessment = client.post(
        "/api/v1/assessments",
        headers=headers(token),
        json={
            "context_id": other_context_id,
            "format": "mcq",
            "question_count": 3,
            "difficulty": "medium",
        },
    )
    assert assessment.status_code == 404


def test_deadline_syllabus_resource_must_be_owned(client: TestClient) -> None:
    first = register(client, "deadline-owner@example.com")
    second = register(client, "resource-owner@example.com")
    first_context = client.post(
        "/api/v1/contexts", headers=headers(first["access_token"]), json={"title": "Mine"}
    ).json()
    second_context = client.post(
        "/api/v1/contexts", headers=headers(second["access_token"]), json={"title": "Theirs"}
    ).json()
    other_resource = client.post(
        "/api/v1/resources/text",
        headers=headers(second["access_token"]),
        json={
            "context_id": second_context["id"],
            "title": "Their material",
            "text": MATERIAL,
        },
    ).json()

    response = client.post(
        "/api/v1/planner/deadlines",
        headers=headers(first["access_token"]),
        json={
            "context_id": first_context["id"],
            "title": "Deadline",
            "due_at": "2030-01-01T00:00:00Z",
            "reminder_days_before": 5,
            "syllabus_resource_id": other_resource["id"],
        },
    )
    assert response.status_code == 422
