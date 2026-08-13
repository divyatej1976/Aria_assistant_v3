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
        json={"title": "DBMS", "description": "Orchestration tests"},
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


def submit_assessment(client: TestClient, token: str, context_id: str) -> None:
    created = client.post(
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
        f"/api/v1/assessments/{created['id']}/attempts", headers=headers(token)
    ).json()
    questions = started["questions"]
    client.post(
        f"/api/v1/assessments/{created['id']}/attempts/{started['attempt_id']}/submit",
        headers=headers(token),
        json={"idempotency_key": "orch-key-0001", "answers": {q["id"]: "A" for q in questions}},
    )


def test_generate_notes_workflow_completes(client: TestClient) -> None:
    session = register(client, "orch-notes@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)

    started = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers=headers(token),
        json={"payload": {"context_id": context_id}},
    )
    assert started.status_code == 201
    assert started.json()["status"] == "COMPLETED"
    assert started.json()["approval"] is None

    notes = client.get(
        f"/api/v1/notes?context_id={context_id}", headers=headers(token)
    ).json()
    assert len(notes) == 1


def test_learning_cycle_workflow_runs_three_steps(client: TestClient) -> None:
    session = register(client, "orch-cycle@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)

    started = client.post(
        "/api/v1/orchestration/workflows/learning_cycle",
        headers=headers(token),
        json={"payload": {"context_id": context_id, "question": "What is two-phase locking?"}},
    )
    assert started.status_code == 201
    workflow_id = started.json()["workflow_id"]
    assert started.json()["status"] == "COMPLETED"

    tasks = client.get(
        f"/api/v1/orchestration/workflows/{workflow_id}/tasks", headers=headers(token)
    ).json()
    assert [task["agent"] for task in tasks] == ["study", "assessment", "learner_model"]
    assert all(task["status"] == "SUCCEEDED" for task in tasks)


def test_exam_prep_workflow_completes(client: TestClient) -> None:
    session = register(client, "orch-prep@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    client.post(
        "/api/v1/planner/deadlines",
        headers=headers(token),
        json={
            "context_id": context_id,
            "title": "DBMS End Sem",
            "due_at": "2026-12-01T00:00:00Z",
            "reminder_days_before": 5,
        },
    )
    started = client.post(
        "/api/v1/orchestration/workflows/exam_prep",
        headers=headers(token),
        json={"payload": {"context_id": context_id}},
    )
    assert started.status_code == 201
    assert started.json()["status"] == "COMPLETED"


def test_data_reset_requires_approval(client: TestClient) -> None:
    session = register(client, "orch-reset@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    client.post(
        "/api/v1/notes",
        headers=headers(token),
        json={"context_id": context_id, "title": "Keep me", "body": MATERIAL},
    )

    started = client.post(
        "/api/v1/orchestration/workflows/data_reset",
        headers=headers(token),
        json={"payload": {}},
    )
    assert started.status_code == 201
    body = started.json()
    assert body["status"] == "WAITING_APPROVAL"
    approval = body["approval"]
    assert approval is not None
    assert approval["status"] == "PENDING"

    approvals = client.get("/api/v1/orchestration/approvals", headers=headers(token)).json()
    assert len(approvals) == 1

    # Reject path keeps the note.
    rejected = client.post(
        f"/api/v1/orchestration/approvals/{approval['id']}/reject", headers=headers(token)
    )
    assert rejected.json()["status"] == "REJECTED"
    notes = client.get(
        f"/api/v1/notes?context_id={context_id}", headers=headers(token)
    ).json()
    assert len(notes) == 1

    # Approve path deletes everything.
    started = client.post(
        "/api/v1/orchestration/workflows/data_reset",
        headers=headers(token),
        json={"payload": {}},
    ).json()
    approved = client.post(
        f"/api/v1/orchestration/approvals/{started['approval']['id']}/approve",
        headers=headers(token),
    )
    assert approved.json()["status"] == "COMPLETED"

    relogin = client.post(
        "/api/v1/auth/login",
        json={"email": "orch-reset@example.com", "password": "correct-horse"},
    ).json()
    contexts = client.get(
        "/api/v1/contexts", headers=headers(relogin["access_token"])
    ).json()
    assert contexts == []


def test_evidence_invalidate_requires_approval(client: TestClient) -> None:
    session = register(client, "orch-evidence@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    submit_assessment(client, token, context_id)
    evidence = client.get(
        f"/api/v1/contexts/{context_id}/evidence", headers=headers(token)
    ).json()
    assert evidence
    evidence_id = evidence[0]["id"]

    started = client.post(
        "/api/v1/orchestration/workflows/evidence_invalidate",
        headers=headers(token),
        json={"payload": {"context_id": context_id, "evidence_id": evidence_id}},
    )
    assert started.json()["status"] == "WAITING_APPROVAL"

    approved = client.post(
        f"/api/v1/orchestration/approvals/{started.json()['approval']['id']}/approve",
        headers=headers(token),
    )
    assert approved.json()["status"] == "COMPLETED"

    evidence = client.get(
        f"/api/v1/contexts/{context_id}/evidence", headers=headers(token)
    ).json()
    target = next(item for item in evidence if item["id"] == evidence_id)
    assert target["valid"] is False


def test_audit_trail_records_owner_and_request_id(client: TestClient) -> None:
    session = register(client, "orch-audit@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers=headers(token),
        json={"payload": {"context_id": context_id}},
    )
    audit = client.get("/api/v1/orchestration/audit", headers=headers(token)).json()
    assert audit
    assert any(item["agent"] == "notes" and item["action"] == "succeeded" for item in audit)
    assert all(item["request_id"] for item in audit)


def test_orchestration_is_isolated(client: TestClient) -> None:
    first = register(client, "orch-iso-a@example.com")
    second = register(client, "orch-iso-b@example.com")
    context_id = create_context(client, first["access_token"])
    add_material(client, first["access_token"], context_id)
    client.post(
        "/api/v1/orchestration/workflows/data_reset",
        headers=headers(first["access_token"]),
        json={"payload": {}},
    )

    second_approvals = client.get(
        "/api/v1/orchestration/approvals", headers=headers(second["access_token"])
    ).json()
    assert second_approvals == []
    second_workflows = client.get(
        "/api/v1/orchestration/workflows", headers=headers(second["access_token"])
    ).json()
    assert second_workflows == []

    first_approval = client.get(
        "/api/v1/orchestration/approvals", headers=headers(first["access_token"])
    ).json()[0]
    forged = client.post(
        f"/api/v1/orchestration/approvals/{first_approval['id']}/approve",
        headers=headers(second["access_token"]),
    )
    assert forged.status_code == 422
