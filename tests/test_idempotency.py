"""Phase 12.7 generalized idempotency: workflow replay via Idempotency-Key."""

from fastapi.testclient import TestClient

MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time. "
    "A precedence graph detects cycles that indicate non-serializable schedules."
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


def _learner(client: TestClient, email: str) -> tuple[str, str]:
    session = register(client, email)
    context = client.post(
        "/api/v1/contexts", headers=headers(session["access_token"]), json={"title": "DBMS"}
    ).json()
    client.post(
        "/api/v1/resources/text",
        headers=headers(session["access_token"]),
        json={"context_id": context["id"], "title": "Locks", "text": MATERIAL},
    )
    return session["access_token"], context["id"]


def test_workflow_with_idempotency_key_replays_stored_response(client: TestClient) -> None:
    token, context_id = _learner(client, "idem@example.com")
    headers_with_key = {
        **headers(token),
        "Idempotency-Key": "wf-gen-notes-1",
    }

    first = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers=headers_with_key,
        json={"payload": {"context_id": context_id}},
    )
    assert first.status_code == 201
    first_body = first.json()
    assert first_body["status"] == "COMPLETED"

    second = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers=headers_with_key,
        json={"payload": {"context_id": context_id}},
    )
    assert second.status_code == 201
    assert second.json() == first_body

    workflows = client.get("/api/v1/orchestration/workflows", headers=headers(token)).json()
    assert len(workflows) == 1


def test_workflow_without_idempotency_key_runs_twice(client: TestClient) -> None:
    token, context_id = _learner(client, "twice@example.com")
    for _ in range(2):
        response = client.post(
            "/api/v1/orchestration/workflows/generate_notes",
            headers=headers(token),
            json={"payload": {"context_id": context_id}},
        )
        assert response.status_code == 201

    workflows = client.get("/api/v1/orchestration/workflows", headers=headers(token)).json()
    assert len(workflows) == 2


def test_idempotency_key_is_scoped_per_learner(client: TestClient) -> None:
    first = register(client, "idem-a@example.com")
    second = register(client, "idem-b@example.com")
    key = {"Idempotency-Key": "shared-key"}

    first_started = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers={**headers(first["access_token"]), **key},
        json={"payload": {}},
    )
    # No context for this learner -> the payload is accepted but the workflow
    # fails; what matters here is that the key is recorded for learner A only.
    assert first_started.status_code == 201

    second_started = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers={**headers(second["access_token"]), **key},
        json={"payload": {}},
    )
    assert second_started.status_code == 201
    assert second_started.json()["workflow_id"] != first_started.json()["workflow_id"]
