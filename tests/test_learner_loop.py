from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.models import (
    Concept,
    ConceptChunk,
    Evidence,
    LearnerConceptState,
    Resource,
    ResourceChunk,
)
from app.services.evidence import SIGNAL_CORRECT, SIGNAL_INCORRECT
from app.services.learner_state import (
    STATE_DEVELOPING,
    STATE_NEEDS_REVIEW,
    STATE_SUPPORTED,
    STATE_UNTESTED,
    compute_state,
    recompute_learner_states,
)
from app.services.study import weak_chunk_boosts

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


def test_state_recomputation_reads_remain_constant_for_large_subject(client, session_factory, engine):
    from uuid import UUID

    from sqlalchemy import event

    session = register(client, "state-batching@example.com")
    owner = UUID(session["learner_id"])
    context = UUID(create_context(client, session["access_token"]))
    with session_factory() as db:
        db.add_all([Concept(owner_id=owner, context_id=context, name=f"Concept {i}") for i in range(100)])
        db.commit()
        reads = []

        def count(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                reads.append(statement)

        event.listen(engine, "before_cursor_execute", count)
        try:
            states = recompute_learner_states(db, owner_id=owner, context_id=context)
            assert len(reads) == 4
            assert len(states) == 100
            assert all(state.state == STATE_UNTESTED for state in states)
            reads.clear()
            again = recompute_learner_states(db, owner_id=owner, context_id=context)
            assert len(reads) == 4
            assert {state.id for state in again} == {state.id for state in states}
        finally:
            event.remove(engine, "before_cursor_execute", count)


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_context(client: TestClient, token: str) -> str:
    response = client.post(
        "/api/v1/contexts",
        headers=headers(token),
        json={"title": "DBMS", "description": "Transactions"},
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


def submit_empty(client: TestClient, token: str, assessment_id: str) -> None:
    started = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts", headers=headers(token)
    )
    assert started.status_code == 201
    attempt_id = started.json()["attempt_id"]
    result = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        headers=headers(token),
        json={"idempotency_key": f"key-{uuid4()}", "answers": {}},
    )
    assert result.status_code == 200


def test_compute_state_transitions() -> None:
    assert compute_state([]) == (STATE_UNTESTED, 0)
    assert compute_state([SIGNAL_CORRECT])[0] == STATE_DEVELOPING
    assert compute_state([SIGNAL_CORRECT, SIGNAL_CORRECT])[0] == STATE_SUPPORTED
    assert compute_state([SIGNAL_INCORRECT, SIGNAL_CORRECT, SIGNAL_CORRECT])[0] == STATE_SUPPORTED
    assert compute_state([SIGNAL_CORRECT, SIGNAL_INCORRECT])[0] == STATE_NEEDS_REVIEW
    result = compute_state([SIGNAL_CORRECT, SIGNAL_CORRECT, SIGNAL_INCORRECT])
    assert result[0] == STATE_NEEDS_REVIEW


def test_concept_sync_discovers_concepts(client: TestClient) -> None:
    session = register(client, "concepts@example.com")
    context_id = create_context(client, session["access_token"])
    add_material(client, session["access_token"], context_id)
    synced = client.post(
        f"/api/v1/contexts/{context_id}/concepts/sync", headers=headers(session["access_token"])
    )
    assert synced.status_code == 200
    names = [item["name"] for item in synced.json()]
    assert names
    listed = client.get(
        f"/api/v1/contexts/{context_id}/concepts", headers=headers(session["access_token"])
    )
    assert {item["name"] for item in listed.json()} == set(names)
    normalized = MATERIAL.lower()
    for name in names:
        assert name in normalized


def test_assessment_questions_link_to_concepts(client: TestClient) -> None:
    session = register(client, "link@example.com")
    context_id = create_context(client, session["access_token"])
    add_material(client, session["access_token"], context_id)
    assessment_id = create_assessment(client, session["access_token"], context_id)
    detail = client.get(
        f"/api/v1/assessments/{assessment_id}", headers=headers(session["access_token"])
    )
    assert detail.status_code == 200
    questions = detail.json()["questions"]
    assert questions
    assert any(question["concept_id"] for question in questions)


def test_submit_produces_evidence_and_adaptation(client: TestClient) -> None:
    session = register(client, "loop@example.com")
    context_id = create_context(client, session["access_token"])
    add_material(client, session["access_token"], context_id)
    assessment_id = create_assessment(client, session["access_token"], context_id)
    submit_empty(client, session["access_token"], assessment_id)

    evidence = client.get(
        f"/api/v1/contexts/{context_id}/evidence", headers=headers(session["access_token"])
    )
    assert evidence.status_code == 200
    assert all(item["valid"] for item in evidence.json())
    assert any(item["signal"] == "INCORRECT" for item in evidence.json())

    summary = client.get(
        f"/api/v1/contexts/{context_id}/adaptation", headers=headers(session["access_token"])
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["states"]
    assert any(item["state"] == STATE_NEEDS_REVIEW for item in body["states"])
    types = {item["decision_type"] for item in body["decisions"]}
    assert "FOCUS_STUDY" in types
    assert "RETEST_TARGETED" in types


def test_invalidate_evidence_recomputes_state(client: TestClient) -> None:
    session = register(client, "challenge@example.com")
    context_id = create_context(client, session["access_token"])
    add_material(client, session["access_token"], context_id)
    assessment_id = create_assessment(client, session["access_token"], context_id)
    submit_empty(client, session["access_token"], assessment_id)

    evidence = client.get(
        f"/api/v1/contexts/{context_id}/evidence", headers=headers(session["access_token"])
    ).json()
    target = next(item for item in evidence if item["signal"] == "INCORRECT")
    concept_evidence = [item for item in evidence if item["concept_id"] == target["concept_id"]]
    summary = None
    for item in concept_evidence:
        invalidated = client.post(
            f"/api/v1/contexts/{context_id}/evidence/{item['id']}/invalidate",
            headers=headers(session["access_token"]),
        )
        assert invalidated.status_code == 200
        summary = invalidated.json()
    concept_state = next(
        item for item in summary["states"] if item["concept_id"] == target["concept_id"]
    )
    assert concept_state["state"] == STATE_UNTESTED


def test_targeted_assessment_uses_weak_concepts(client: TestClient) -> None:
    session = register(client, "targeted@example.com")
    context_id = create_context(client, session["access_token"])
    add_material(client, session["access_token"], context_id)
    assessment_id = create_assessment(client, session["access_token"], context_id)
    submit_empty(client, session["access_token"], assessment_id)
    summary = client.get(
        f"/api/v1/contexts/{context_id}/adaptation", headers=headers(session["access_token"])
    ).json()
    weak_ids = [
        item["concept_id"] for item in summary["states"] if item["state"] == STATE_NEEDS_REVIEW
    ]
    assert weak_ids
    created = client.post(
        "/api/v1/assessments",
        headers=headers(session["access_token"]),
        json={
            "context_id": context_id,
            "format": "mcq",
            "question_count": 3,
            "difficulty": "medium",
            "mode": "TARGETED",
            "concept_ids": weak_ids,
        },
    )
    assert created.status_code == 201
    assert created.json()["mode"] == "TARGETED"
    assert created.json()["questions"]


def test_adaptation_is_isolated(client: TestClient) -> None:
    first = register(client, "iso-first@example.com")
    second = register(client, "iso-second@example.com")
    first_context = create_context(client, first["access_token"])
    second_context = create_context(client, second["access_token"])
    add_material(client, first["access_token"], first_context)
    client.post(
        f"/api/v1/contexts/{first_context}/concepts/sync", headers=headers(first["access_token"])
    )
    assert (
        client.get(
            f"/api/v1/contexts/{first_context}/adaptation",
            headers=headers(second["access_token"]),
        ).status_code
        == 404
    )
    second_summary = client.get(
        f"/api/v1/contexts/{second_context}/adaptation", headers=headers(second["access_token"])
    )
    assert second_summary.status_code == 200
    assert second_summary.json()["states"] == []


def test_recompute_state_service(engine, session_factory) -> None:
    with session_factory() as db:
        owner_id = uuid4()
        context_id = uuid4()
        from app.db.models import Assessment, AssessmentAttempt, Evaluation, LearningContext

        db.add(LearningContext(id=context_id, owner_id=owner_id, title="State test"))
        db.flush()
        assessment = Assessment(owner_id=owner_id, context_id=context_id)
        db.add(assessment)
        db.flush()

        def evaluation_id():
            attempt = AssessmentAttempt(owner_id=owner_id, assessment_id=assessment.id, idempotency_key=str(uuid4()))
            db.add(attempt)
            db.flush()
            evaluation = Evaluation(owner_id=owner_id, attempt_id=attempt.id)
            db.add(evaluation)
            db.flush()
            return evaluation.id

        concept = Concept(owner_id=owner_id, context_id=context_id, name="locking")
        db.add(concept)
        db.flush()
        for signal in (SIGNAL_CORRECT, SIGNAL_CORRECT):
            db.add(
                Evidence(
                    owner_id=owner_id,
                    concept_id=concept.id,
                    evaluation_id=evaluation_id(),
                    signal=signal,
                    provenance={"attempt_id": str(uuid4()), "evaluation_id": str(uuid4())},
                )
            )
        db.commit()
        states = recompute_learner_states(db, owner_id=owner_id, context_id=context_id)
        assert states[0].state == STATE_SUPPORTED
        assert states[0].confidence >= 50

        db.add(
            Evidence(
                owner_id=owner_id,
                concept_id=concept.id,
                evaluation_id=evaluation_id(),
                signal=SIGNAL_INCORRECT,
                provenance={"attempt_id": str(uuid4()), "evaluation_id": str(uuid4())},
            )
        )
        db.commit()
        states = recompute_learner_states(db, owner_id=owner_id, context_id=context_id)
        assert states[0].state == STATE_NEEDS_REVIEW


def test_weak_chunk_boosts_only_weak_concepts(engine, session_factory) -> None:
    with session_factory() as db:
        owner_id = uuid4()
        context_id = uuid4()
        resource = Resource(
            id=uuid4(),
            owner_id=owner_id,
            context_id=context_id,
            title="t",
            resource_type="TEXT",
            processing_status="READY",
        )
        db.add(resource)
        db.flush()
        weak_chunk = ResourceChunk(
            owner_id=owner_id, resource_id=resource.id, content="weak material", chunk_index=0
        )
        strong_chunk = ResourceChunk(
            owner_id=owner_id, resource_id=resource.id, content="strong material", chunk_index=1
        )
        db.add_all([weak_chunk, strong_chunk])
        db.flush()
        weak_concept = Concept(owner_id=owner_id, context_id=context_id, name="weak")
        strong_concept = Concept(owner_id=owner_id, context_id=context_id, name="strong")
        db.add_all([weak_concept, strong_concept])
        db.flush()
        db.add_all(
            [
                ConceptChunk(owner_id=owner_id, concept_id=weak_concept.id, chunk_id=weak_chunk.id),
                ConceptChunk(
                    owner_id=owner_id, concept_id=strong_concept.id, chunk_id=strong_chunk.id
                ),
                LearnerConceptState(
                    owner_id=owner_id,
                    concept_id=weak_concept.id,
                    state=STATE_NEEDS_REVIEW,
                    confidence=10,
                    reason="weak",
                ),
                LearnerConceptState(
                    owner_id=owner_id,
                    concept_id=strong_concept.id,
                    state=STATE_SUPPORTED,
                    confidence=90,
                    reason="strong",
                ),
            ]
        )
        db.commit()
        boosts = weak_chunk_boosts(db, owner_id=owner_id, context_id=context_id)
    assert boosts[str(weak_chunk.id)] == 1.3
    assert str(strong_chunk.id) not in boosts
