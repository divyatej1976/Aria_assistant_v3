import re
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.assessment.mcq import generate_mcqs_deterministic
from app.assessment.schema import MCQItem, MCQSet
from app.db.base import Base
from app.db.models import Resource, ResourceChunk

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
        json={"title": "DBMS", "description": "Transactions"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def add_material(client: TestClient, token: str, context_id: str, text: str = MATERIAL) -> None:
    response = client.post(
        "/api/v1/resources/text",
        headers=headers(token),
        json={"context_id": context_id, "title": "Locks", "text": text},
    )
    assert response.status_code == 201


def create_assessment(
    client: TestClient, token: str, context_id: str, count: int = 3, difficulty: str = "medium"
) -> object:
    return client.post(
        "/api/v1/assessments",
        headers=headers(token),
        json={
            "context_id": context_id,
            "format": "mcq",
            "question_count": count,
            "difficulty": difficulty,
            "mode": "BASELINE",
        },
    )


def start_attempt(client: TestClient, token: str, assessment_id: str) -> object:
    return client.post(
        f"/api/v1/assessments/{assessment_id}/attempts", headers=headers(token)
    )


def submit(
    client: TestClient,
    token: str,
    assessment_id: str,
    attempt_id: str,
    key: str,
    answers: dict[str, str] | None = None,
) -> object:
    return client.post(
        f"/api/v1/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        headers=headers(token),
        json={"idempotency_key": key, "answers": answers or {}},
    )


def test_create_assessment_uses_real_material(client: TestClient) -> None:
    session = register(client, "assess@example.com")
    context_id = create_context(client, session["access_token"])
    add_material(client, session["access_token"], context_id)
    response = create_assessment(client, session["access_token"], context_id, count=3)
    assert response.status_code == 201
    body = response.json()
    assert body["format"] == "mcq"
    assert body["mode"] == "BASELINE"
    assert len(body["questions"]) == 3
    normalized = re.sub(r"\s+", " ", MATERIAL)
    for question in body["questions"]:
        assert len(question["options"]) == 4
        assert len(set(question["options"])) == 4
        for option in question["options"]:
            assert option in normalized
        assert "correct_option" not in question


def test_generator_produces_valid_varied_correct_letters() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as db:
        owner_id = uuid4()
        context_id = uuid4()
        resource = Resource(
            id=uuid4(),
            owner_id=owner_id,
            context_id=context_id,
            title="Locks",
            resource_type="TEXT",
            processing_status="READY",
        )
        db.add(resource)
        db.flush()
        sentences = [
            "Two-phase locking uses a growth phase and a shrink phase.",
            "Strict two-phase locking releases every lock only at commit time.",
            "A precedence graph detects cycles that indicate non-serializable schedules.",
            "Conflict serializability is a subset of view serializability.",
            "Deadlock detection requires waiting for a cycle in the wait-for graph.",
        ]
        for index, sentence in enumerate(sentences):
            db.add(
                ResourceChunk(
                    owner_id=owner_id,
                    resource_id=resource.id,
                    content=sentence,
                    chunk_index=index,
                )
            )
        db.commit()
        questions = generate_mcqs_deterministic(
            db, owner_id=owner_id, context_id=context_id, count=5, difficulty="medium"
        )
    engine.dispose()
    assert len(questions) == 5
    letters = set()
    for question in questions:
        assert len(question.options) == 4
        assert len(set(question.options)) == 4
        assert question.correct_option in "ABCD"
        letters.add(question.correct_option)
    assert len(letters) > 1


def test_create_requires_enough_material(client: TestClient) -> None:
    session = register(client, "short@example.com")
    context_id = create_context(client, session["access_token"])
    add_material(client, session["access_token"], context_id, text="Only one short sentence here.")
    response = create_assessment(client, session["access_token"], context_id, count=3)
    assert response.status_code == 422


def test_deterministic_score_and_idempotent_submit(client: TestClient) -> None:
    session = register(client, "score@example.com")
    context_id = create_context(client, session["access_token"])
    add_material(client, session["access_token"], context_id)
    assessment_id = create_assessment(
        client, session["access_token"], context_id, count=3
    ).json()["id"]
    attempt_id = start_attempt(client, session["access_token"], assessment_id).json()["attempt_id"]
    answers = {"not-a-real-question": "A"}
    first = submit(
        client, session["access_token"], assessment_id, attempt_id, "key-idempotent-0001", answers
    )
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "COMPLETED"
    assert body["total"] == 3
    assert body["score"] == 0

    again = submit(
        client, session["access_token"], assessment_id, attempt_id, "key-idempotent-0001", answers
    )
    assert again.status_code == 200
    second_body = again.json()
    assert second_body["attempt_id"] == body["attempt_id"]
    assert second_body["evaluation_id"] == body["evaluation_id"]
    assert second_body["score"] == body["score"]


def test_autosaved_answers_are_scored_on_submit(client: TestClient) -> None:
    session = register(client, "autosave@example.com")
    context_id = create_context(client, session["access_token"])
    add_material(client, session["access_token"], context_id)
    assessment_id = create_assessment(
        client, session["access_token"], context_id, count=3
    ).json()["id"]
    started = start_attempt(client, session["access_token"], assessment_id)
    attempt_id = started.json()["attempt_id"]
    questions = started.json()["questions"]
    question_id = questions[0]["id"]

    saved = client.put(
        f"/api/v1/assessments/{assessment_id}/attempts/{attempt_id}/answers",
        headers=headers(session["access_token"]),
        json={"answers": {question_id: "B"}},
    )
    assert saved.status_code == 200
    saved = client.put(
        f"/api/v1/assessments/{assessment_id}/attempts/{attempt_id}/answers",
        headers=headers(session["access_token"]),
        json={"answers": {question_id: "C", questions[1]["id"]: "A"}},
    )
    assert saved.status_code == 200

    result = submit(
        client, session["access_token"], assessment_id, attempt_id, "key-autosave-0001"
    )
    assert result.status_code == 200
    details = result.json()["details"]
    first_question = next(item for item in details if item["question_id"] == question_id)
    assert first_question["selected_option"] == "C"
    assert first_question["correct_option"] in "ABCD"


def test_empty_answers_produce_zero_score(client: TestClient) -> None:
    session = register(client, "empty@example.com")
    context_id = create_context(client, session["access_token"])
    add_material(client, session["access_token"], context_id)
    assessment_id = create_assessment(
        client, session["access_token"], context_id, count=3
    ).json()["id"]
    attempt_id = start_attempt(client, session["access_token"], assessment_id).json()["attempt_id"]
    result = submit(client, session["access_token"], assessment_id, attempt_id, "key-empty-0001")
    assert result.status_code == 200
    body = result.json()
    assert body["score"] == 0
    assert body["total"] == 3
    assert all(item["correct"] is False for item in body["details"])


def test_correct_answers_are_not_leaked_before_submit(client: TestClient) -> None:
    session = register(client, "leakless@example.com")
    context_id = create_context(client, session["access_token"])
    add_material(client, session["access_token"], context_id)
    assessment_id = create_assessment(
        client, session["access_token"], context_id, count=2
    ).json()["id"]
    started = start_attempt(client, session["access_token"], assessment_id)
    assert started.status_code == 201
    assert "correct_option" not in started.json()["questions"][0]
    detail = client.get(
        f"/api/v1/assessments/{assessment_id}", headers=headers(session["access_token"])
    )
    assert detail.status_code == 200
    assert "correct_option" not in detail.json()["questions"][0]


def test_assessments_and_attempts_are_isolated(client: TestClient) -> None:
    first = register(client, "iso-first@example.com")
    second = register(client, "iso-second@example.com")
    first_context = create_context(client, first["access_token"])
    second_context = create_context(client, second["access_token"])
    add_material(client, first["access_token"], first_context)
    assessment_id = create_assessment(
        client, first["access_token"], first_context, count=2
    ).json()["id"]

    listed_second = client.get(
        f"/api/v1/assessments?context_id={second_context}",
        headers=headers(second["access_token"]),
    )
    assert listed_second.status_code == 200
    assert listed_second.json() == []

    detail = client.get(
        f"/api/v1/assessments/{assessment_id}", headers=headers(second["access_token"])
    )
    assert detail.status_code == 404

    start = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts",
        headers=headers(second["access_token"]),
    )
    assert start.status_code == 404


def test_structured_schema_validation() -> None:
    with pytest.raises(ValidationError):
        MCQItem(
            prompt="A long enough prompt here",
            options=["a", "b", "c", "d"],
            correct_option="E",
        )
    with pytest.raises(ValidationError):
        MCQItem(
            prompt="A long enough prompt here",
            options=["a", "a", "c", "d"],
            correct_option="A",
        )
    with pytest.raises(ValidationError):
        MCQSet(questions=[])
    valid = MCQSet(
        questions=[
            MCQItem(
                prompt="A long enough prompt here",
                options=["first", "second", "third", "fourth"],
                correct_option="b",
            )
        ]
    )
    assert valid.questions[0].correct_option == "B"
