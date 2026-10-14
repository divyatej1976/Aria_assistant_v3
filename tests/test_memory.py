from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.models import (
    Concept,
    ConversationMessage,
    Learner,
    LearnerConceptState,
    LearnerSession,
)
from app.services.context_assembly import (
    STUDY_SYSTEM_PROMPT,
    ContextPackage,
    build_prompt,
    relevant_learner_states,
)

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
        json={"title": "DBMS", "description": "Memory tests"},
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


def create_assessment(client: TestClient, token: str, context_id: str, count: int = 5) -> str:
    response = client.post(
        "/api/v1/assessments",
        headers=headers(token),
        json={
            "context_id": context_id,
            "format": "mcq",
            "question_count": count,
            "difficulty": "medium",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def submit_all_wrong(client: TestClient, token: str, assessment_id: str) -> None:
    started = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts", headers=headers(token)
    )
    assert started.status_code == 201
    attempt_id = started.json()["attempt_id"]
    questions = started.json()["questions"]
    result = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        headers=headers(token),
        json={"idempotency_key": f"key-{uuid4()}", "answers": {q["id"]: "A" for q in questions}},
    )
    assert result.status_code == 200


def test_preferences_crud_and_isolation(client: TestClient) -> None:
    first = register(client, "pref-a@example.com")
    second = register(client, "pref-b@example.com")

    put = client.put(
        "/api/v1/me/preferences",
        headers=headers(first["access_token"]),
        json={"key": "difficulty", "value": "hard"},
    )
    assert put.status_code == 200
    assert put.json()["value"] == "hard"

    updated = client.put(
        "/api/v1/me/preferences",
        headers=headers(first["access_token"]),
        json={"key": "difficulty", "value": "medium"},
    )
    assert updated.status_code == 200
    assert updated.json()["value"] == "medium"

    listed = client.get("/api/v1/me/preferences", headers=headers(first["access_token"]))
    assert listed.json() == [{"key": "difficulty", "value": "medium"}]

    other = client.get("/api/v1/me/preferences", headers=headers(second["access_token"]))
    assert other.json() == []

    deleted = client.delete(
        "/api/v1/me/preferences/difficulty", headers=headers(first["access_token"])
    )
    assert deleted.status_code == 200
    gone = client.get("/api/v1/me/preferences", headers=headers(first["access_token"]))
    assert gone.json() == []


def test_memory_summary(client: TestClient) -> None:
    session = register(client, "summary@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    client.put(
        "/api/v1/me/preferences",
        headers=headers(token),
        json={"key": "focus_goal", "value": "exams"},
    )
    assessment_id = create_assessment(client, token, context_id, count=5)
    submit_all_wrong(client, token, assessment_id)

    summary = client.get("/api/v1/memory", headers=headers(token))
    assert summary.status_code == 200
    body = summary.json()
    assert any(item["key"] == "focus_goal" for item in body["preferences"])
    assert body["concepts"] > 0
    assert body["weak_concepts"] > 0
    assert body["evidence_count"] > 0
    assert body["message_count"] == 0


def test_delete_conversation_message(client: TestClient) -> None:
    session = register(client, "delete-msg@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    created = client.post(
        "/api/v1/study/sessions", headers=headers(token), json={"context_id": context_id}
    )
    session_id = created.json()["id"]
    client.post(
        f"/api/v1/study/sessions/{session_id}/messages",
        headers=headers(token),
        json={"content": "What is two-phase locking?"},
    )
    messages = client.get(
        f"/api/v1/study/sessions/{session_id}/messages", headers=headers(token)
    ).json()
    assert len(messages) == 2
    target = next(message for message in messages if message["role"] == "user")
    assert target["id"]

    deleted = client.delete(
        f"/api/v1/study/sessions/{session_id}/messages/{target['id']}",
        headers=headers(token),
    )
    assert deleted.status_code == 200
    remaining = client.get(
        f"/api/v1/study/sessions/{session_id}/messages", headers=headers(token)
    ).json()
    assert len(remaining) == 1

    gone = client.delete(
        f"/api/v1/study/sessions/{session_id}/messages/{target['id']}",
        headers=headers(token),
    )
    assert gone.status_code == 404


def test_delete_message_is_scoped_to_its_session(client: TestClient) -> None:
    session = register(client, "cross-session@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)

    first = client.post(
        "/api/v1/study/sessions", headers=headers(token), json={"context_id": context_id}
    ).json()
    second = client.post(
        "/api/v1/study/sessions", headers=headers(token), json={"context_id": context_id}
    ).json()

    client.post(
        f"/api/v1/study/sessions/{first['id']}/messages",
        headers=headers(token),
        json={"content": "A message in the first session"},
    )
    first_messages = client.get(
        f"/api/v1/study/sessions/{first['id']}/messages", headers=headers(token)
    ).json()
    target = next(message for message in first_messages if message["role"] == "user")

    blocked = client.delete(
        f"/api/v1/study/sessions/{second['id']}/messages/{target['id']}",
        headers=headers(token),
    )
    assert blocked.status_code == 404

    still_there = client.get(
        f"/api/v1/study/sessions/{first['id']}/messages", headers=headers(token)
    ).json()
    assert any(message["id"] == target["id"] for message in still_there)


def test_prerequisite_crud_and_isolation(client: TestClient) -> None:
    first = register(client, "prereq-a@example.com")
    second = register(client, "prereq-b@example.com")
    context_id = create_context(client, first["access_token"])
    add_material(client, first["access_token"], context_id)
    client.post(
        f"/api/v1/contexts/{context_id}/concepts/sync",
        headers=headers(first["access_token"]),
    )
    concepts = client.get(
        f"/api/v1/contexts/{context_id}/concepts", headers=headers(first["access_token"])
    ).json()
    assert len(concepts) >= 2
    base, prereq = concepts[0]["id"], concepts[1]["id"]

    added = client.post(
        f"/api/v1/contexts/{context_id}/concepts/{base}/prerequisites",
        headers=headers(first["access_token"]),
        json={"prerequisite_concept_id": prereq},
    )
    assert added.status_code == 201
    assert any(item["prerequisite_concept_id"] == prereq for item in added.json())

    self_link = client.post(
        f"/api/v1/contexts/{context_id}/concepts/{base}/prerequisites",
        headers=headers(first["access_token"]),
        json={"prerequisite_concept_id": base},
    )
    assert self_link.status_code == 422

    other_access = client.post(
        f"/api/v1/contexts/{context_id}/concepts/{base}/prerequisites",
        headers=headers(second["access_token"]),
        json={"prerequisite_concept_id": prereq},
    )
    assert other_access.status_code == 404

    removed = client.delete(
        f"/api/v1/contexts/{context_id}/concepts/{base}/prerequisites/{prereq}",
        headers=headers(first["access_token"]),
    )
    assert removed.status_code == 200
    listed = client.get(
        f"/api/v1/contexts/{context_id}/concepts/{base}/prerequisites",
        headers=headers(first["access_token"]),
    )
    assert listed.json() == []


def test_misconception_signal_with_weak_prerequisite(client: TestClient) -> None:
    session = register(client, "misconception@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    second_material = (
        "Deadlock detection waits for cycles in the resource allocation graph. "
        "A wait-for graph reduces the allocation graph to processes and resources. "
        "Timeouts and deadlock prevention avoid the cost of detection. "
        "Resource preemption can recover from a detected deadlock state."
    )
    second = client.post(
        "/api/v1/resources/text",
        headers=headers(token),
        json={"context_id": context_id, "title": "Deadlocks", "text": second_material},
    )
    assert second.status_code == 201
    assessment_id = create_assessment(client, token, context_id, count=5)
    submit_all_wrong(client, token, assessment_id)

    summary = client.get(
        f"/api/v1/contexts/{context_id}/adaptation", headers=headers(token)
    ).json()
    weak = [state for state in summary["states"] if state["state"] == "NEEDS_REVIEW"]
    assert len(weak) >= 2
    base, prereq = weak[0]["concept_id"], weak[1]["concept_id"]
    client.post(
        f"/api/v1/contexts/{context_id}/concepts/{base}/prerequisites",
        headers=headers(token),
        json={"prerequisite_concept_id": prereq},
    )

    submit_all_wrong(client, token, assessment_id)
    updated = client.get(
        f"/api/v1/contexts/{context_id}/adaptation", headers=headers(token)
    ).json()
    focus = next(
        decision
        for decision in updated["decisions"]
        if decision["decision_type"] == "FOCUS_STUDY" and decision["concept_id"] == base
    )
    assert "weak prerequisite" in focus["reason"]


def test_context_assembly_units(engine, session_factory) -> None:
    with session_factory() as db:
        owner_id = uuid4()
        db.add(Learner(id=owner_id, owner_id=owner_id, email="assembly@example.com"))
        db.flush()
        session_id = uuid4()
        db.add(LearnerSession(id=session_id, owner_id=owner_id))
        db.flush()
        db.add_all(
            [
                ConversationMessage(
                    owner_id=owner_id,
                    study_session_id=session_id,
                    role="user",
                    content="First question",
                    position=1,
                ),
                ConversationMessage(
                    owner_id=owner_id,
                    study_session_id=session_id,
                    role="assistant",
                    content="First answer",
                    position=2,
                ),
                ConversationMessage(
                    owner_id=owner_id,
                    study_session_id=session_id,
                    role="user",
                    content="Follow-up",
                    position=3,
                ),
            ]
        )
        concept = Concept(owner_id=owner_id, context_id=uuid4(), name="locking")
        db.add(concept)
        db.flush()
        db.add(
            LearnerConceptState(
                owner_id=owner_id,
                concept_id=concept.id,
                state="NEEDS_REVIEW",
                confidence=20,
                reason="review",
            )
        )
        db.add(
            LearnerConceptState(
                owner_id=owner_id,
                concept_id=uuid4(),
                state="UNTESTED",
                confidence=0,
                reason="none",
            )
        )
        db.commit()

        from app.services.context_assembly import recent_messages

        history = recent_messages(db, owner_id=owner_id, session_id=session_id)
        assert [message["content"] for message in history] == [
            "First question",
            "First answer",
            "Follow-up",
        ]
        states = relevant_learner_states(db, owner_id=owner_id, context_id=concept.context_id)
        assert states == [{"concept_name": "locking", "state": "NEEDS_REVIEW"}]

        package = ContextPackage(
            recent_messages=history,
            relevant_states=states,
            recent_evidence=[{"concept_name": "locking", "signal": "INCORRECT"}],
            retrieved_chunks=[],
        )
        system, user = build_prompt("Why does locking matter?", package)
        assert system == STUDY_SYSTEM_PROMPT
        assert "Conversation so far:" in user
        assert "Learner state: locking (Needs Review)" in user
        assert "Follow-up" in user
        assert "Why does locking matter?" in user
