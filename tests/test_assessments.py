import re
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.assessment.mcq import generate_mcqs_deterministic
from app.assessment.schema import MCQItem, MCQSet
from app.db.models import Concept, ConceptChunk, LearningContext, Resource, ResourceChunk

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
        json={"email": email, "password": "correct-horse-9", "display_name": "Learner"},
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


def test_summary_counts_submitted_reviews_and_is_scoped_to_the_learner(client: TestClient) -> None:
    token = register(client, "first-review@example.com")["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    assessment_id = create_assessment(client, token, context_id).json()["id"]
    url = f"/api/v1/assessments?context_id={context_id}"
    assert client.get(url, headers=headers(token)).json()[0]["submitted_attempt_count"] == 0
    assert client.get(url, headers=headers(token)).json()[0]["completed_scores"] == []
    attempt = start_attempt(client, token, assessment_id).json()
    assert client.get(url, headers=headers(token)).json()[0]["submitted_attempt_count"] == 0
    answers = {question["id"]: question["options"][0] for question in attempt["questions"]}
    result = submit(client, token, assessment_id, attempt["attempt_id"], "first-review-summary-key", answers)
    assert result.status_code == 200, result.text
    assert client.get(url, headers=headers(token)).json()[0]["submitted_attempt_count"] == 1
    scores = client.get(url, headers=headers(token)).json()[0]["completed_scores"]
    assert len(scores) == 1
    assert scores[0]["attempt_id"] == attempt["attempt_id"]
    assert scores[0]["score"] == result.json()["score"]
    assert scores[0]["total"] == result.json()["total"]
    assert scores[0]["completed_at"]
    submit(client, token, assessment_id, attempt["attempt_id"], "first-review-summary-key", answers)
    assert client.get(url, headers=headers(token)).json()[0]["submitted_attempt_count"] == 1
    stranger = register(client, "first-review-stranger@example.com")["access_token"]
    assert client.get(url, headers=headers(stranger)).status_code == 404


@pytest.mark.parametrize("retry_key", ["original-key", "different-key"])
def test_completed_submission_rejects_changed_answers(client, retry_key):
    token = register(client, f"changed-{retry_key}@example.com")["access_token"]
    context = create_context(client, token)
    add_material(client, token, context)
    assessment = create_assessment(client, token, context, count=1).json()
    assessment_id = assessment["id"]
    question = assessment["questions"][0]
    attempt_id = start_attempt(client, token, assessment_id).json()["attempt_id"]
    answers = {question["id"]: question["options"][0]}
    first = submit(client, token, assessment_id, attempt_id, "original-key", answers)
    assert first.status_code == 200
    replay = submit(client, token, assessment_id, attempt_id, retry_key, answers)
    assert replay.status_code == 200
    assert replay.json()["evaluation_id"] == first.json()["evaluation_id"]
    changed = submit(client, token, assessment_id, attempt_id, retry_key,
                     {question["id"]: question["options"][1]})
    assert changed.status_code == 422
    assert "differ" in changed.json()["detail"]
    invalid = submit(client, token, assessment_id, attempt_id, retry_key, {"not-a-uuid": "A"})
    assert invalid.status_code == 422
    final = submit(client, token, assessment_id, attempt_id, "original-key", answers)
    assert final.json()["evaluation_id"] == first.json()["evaluation_id"]


def test_assessment_answer_columns_hold_option_text() -> None:
    """Regression: answer columns must be unbounded text.

    PostgreSQL enforces VARCHAR(32) and crashed submission with
    StringDataRightTruncation on real option text ("Loops repeat a block
    while a condition holds"); SQLite ignores the length, so this schema
    assertion is what catches the regression on every backend.
    """
    from sqlalchemy import Text

    from app.db.models import AssessmentQuestion, AttemptAnswer

    assert isinstance(AssessmentQuestion.__table__.c.correct_option.type, Text)
    assert isinstance(AttemptAnswer.__table__.c.selected_option.type, Text)


def test_submit_option_text_persists_and_scores(client: TestClient) -> None:
    """End-to-end: the UI submits option TEXT; it must persist (PostgreSQL
    length enforcement) and score identically to the letter contract."""
    session = register(client, "assess-text@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    assessment = create_assessment(client, token, context_id, count=3).json()

    # Long option text must persist — the exact live production failure.
    attempt = start_attempt(client, token, assessment["id"]).json()
    longest = max(
        attempt["questions"], key=lambda q: max(len(option) for option in q["options"])
    )
    answer_text = max(longest["options"], key=len)
    assert len(answer_text) > 32
    first = submit(
        client, token, assessment["id"], attempt["attempt_id"],
        key=f"text-long-{uuid4()}", answers={longest["id"]: answer_text},
    )
    assert first.status_code == 200
    detail = next(
        d for d in first.json()["details"] if d["question_id"] == longest["id"]
    )
    assert detail["selected_option"] == answer_text

    # Answering the correct option's TEXT must score correct on a fresh
    # attempt (raw text == letter comparison scored every UI answer wrong).
    letters = {d["question_id"]: d["correct_option"] for d in first.json()["details"]}
    attempt2 = start_attempt(client, token, assessment["id"]).json()
    answers2 = {
        question["id"]: question["options"]["ABCD".index(letters[question["id"]])]
        for question in attempt2["questions"]
    }
    second = submit(
        client, token, assessment["id"], attempt2["attempt_id"],
        key=f"text-correct-{uuid4()}", answers=answers2,
    )
    assert second.status_code == 200
    body = second.json()
    assert body["score"] == body["total"]
    for d in body["details"]:
        assert d["correct"] is True


def test_generator_produces_valid_varied_correct_letters(engine, session_factory) -> None:
    with session_factory() as db:
        owner_id = uuid4()
        context_id = uuid4()
        db.add(LearningContext(id=context_id, owner_id=owner_id, title="Locks"))
        db.flush()
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
    assert len(questions) == 5
    letters = set()
    for question in questions:
        assert len(question.options) == 4
        assert len(set(question.options)) == 4
        assert question.correct_option in "ABCD"
        letters.add(question.correct_option)
    assert len(letters) > 1


def test_targeted_generator_credits_requested_concept(session_factory) -> None:
    with session_factory() as db:
        owner_id, context_id = uuid4(), uuid4()
        db.add(LearningContext(id=context_id, owner_id=owner_id, title="Practice"))
        db.flush()
        resource = Resource(
            owner_id=owner_id, context_id=context_id, title="Practice",
            resource_type="TEXT", processing_status="READY",
        )
        db.add(resource)
        db.flush()
        chunk = ResourceChunk(
            owner_id=owner_id, resource_id=resource.id, chunk_index=0,
            content=("Functions accept values. Values can be numbers. "
                     "Values can be strings. Functions return values. "
                     "Values can be lists."),
        )
        requested = Concept(owner_id=owner_id, context_id=context_id, name="Functions")
        dominant = Concept(owner_id=owner_id, context_id=context_id, name="Values")
        db.add_all([chunk, requested, dominant])
        db.flush()
        for concept in (requested, dominant):
            db.add(ConceptChunk(owner_id=owner_id, concept_id=concept.id, chunk_id=chunk.id))
        db.commit()
        unscoped = generate_mcqs_deterministic(
            db, owner_id=owner_id, context_id=context_id, count=2, difficulty="easy",
        )
        scoped = generate_mcqs_deterministic(
            db, owner_id=owner_id, context_id=context_id, count=2, difficulty="easy",
            concept_ids=[str(requested.id)],
        )
        assert all(question.concept_id == dominant.id for question in unscoped)
        assert all(question.concept_id == requested.id for question in scoped)


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
    answers = {}  # A valid unanswered submission keeps this test focused on replay.
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


def test_assessment_submit_accepts_idempotency_key_header(client: TestClient) -> None:
    session = register(client, "header-key@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    assessment_id = create_assessment(client, token, context_id, count=3).json()["id"]
    attempt_id = start_attempt(client, token, assessment_id).json()["attempt_id"]
    answers = {}  # A valid unanswered submission keeps this test focused on replay.

    first = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        headers={**headers(token), "Idempotency-Key": "header-key-0001"},
        json={"answers": answers},
    )
    assert first.status_code == 200
    body = first.json()

    again = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        headers={**headers(token), "Idempotency-Key": "header-key-0001"},
        json={"answers": answers},
    )
    assert again.status_code == 200
    assert again.json()["evaluation_id"] == body["evaluation_id"]


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


def test_pdf_present_does_not_break_concept_linking(client: TestClient) -> None:
    import fitz

    session = register(client, "pdf-concept@example.com")
    context_id = create_context(client, session["access_token"])
    add_material(client, session["access_token"], context_id)
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Conflict serializability is tested with precedence graphs.")
    pdf_bytes = document.tobytes()
    document.close()
    uploaded = client.post(
        f"/api/v1/resources/pdf?context_id={context_id}&title=Notes.pdf",
        headers={**headers(session["access_token"]), "Content-Type": "application/pdf"},
        content=pdf_bytes,
    )
    assert uploaded.status_code == 201
    assessment_id = create_assessment(
        client, session["access_token"], context_id, count=3
    ).json()["id"]
    detail = client.get(
        f"/api/v1/assessments/{assessment_id}", headers=headers(session["access_token"])
    ).json()
    assert any(question["concept_id"] for question in detail["questions"])

    started = start_attempt(client, session["access_token"], assessment_id)
    attempt_id = started.json()["attempt_id"]
    questions = started.json()["questions"]
    result = submit(
        client,
        session["access_token"],
        assessment_id,
        attempt_id,
        f"key-{uuid4()}",
        {q["id"]: "A" for q in questions},
    )
    assert result.status_code == 200
    evidence = client.get(
        f"/api/v1/contexts/{context_id}/evidence", headers=headers(session["access_token"])
    )
    assert len(evidence.json()) > 0


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


def test_concurrent_duplicate_submit_replays_single_evaluation(tmp_path) -> None:
    """Two simultaneous submits of one attempt must not 500 or double-evaluate.

    A flush barrier forces both threads past the check-then-insert reads, so
    the loser deterministically hits the Evaluation unique constraint and must
    take the IntegrityError replay path.
    """
    import threading

    from sqlalchemy import func, select
    from sqlalchemy.orm import Session as SASession

    from app.db.base import Base
    from app.db.models import (
        Assessment,
        AssessmentAttempt,
        AssessmentQuestion,
        Evaluation,
        Learner,
        LearningContext,
    )
    from app.services.assessment import submit_attempt

    db_file = tmp_path / "race.db"
    file_engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False, "timeout": 30}
    )
    Base.metadata.create_all(file_engine)
    file_factory = sessionmaker(bind=file_engine, autoflush=False, expire_on_commit=False)

    owner_id = uuid4()
    context_id = uuid4()
    assessment_id = uuid4()
    attempt_id = uuid4()
    with file_factory() as db:
        learner_id = uuid4()
        db.add(Learner(id=learner_id, owner_id=learner_id, email="race@example.com"))
        db.add(LearningContext(id=context_id, owner_id=owner_id, title="DBMS"))
        db.add(Assessment(id=assessment_id, owner_id=owner_id, context_id=context_id))
        for index in range(3):
            db.add(
                AssessmentQuestion(
                    owner_id=owner_id,
                    assessment_id=assessment_id,
                    concept_id=None,
                    position=index,
                    prompt=f"Question {index}?",
                    options=["A1", "A2", "A3", "A4"],
                    correct_option="A",
                )
            )
        db.add(
            AssessmentAttempt(
                id=attempt_id,
                owner_id=owner_id,
                assessment_id=assessment_id,
                status="IN_PROGRESS",
                idempotency_key=str(uuid4()),
            )
        )
        db.commit()

    key = f"race-key-{uuid4()}"
    barrier = threading.Barrier(2)
    gated = {"count": 0}
    real_flush = SASession.flush

    def gated_flush(self):
        # Gate only the evaluation flush of each submit (commit's internal
        # flushes pass through once both threads are past the barrier).
        if gated["count"] < 2:
            gated["count"] += 1
            barrier.wait(timeout=30)
        return real_flush(self)

    results: dict[int, object] = {}
    errors: dict[int, BaseException] = {}

    def run(slot: int) -> None:
        with file_factory() as db:
            try:
                results[slot] = submit_attempt(
                    db,
                    owner_id=owner_id,
                    attempt_id=attempt_id,
                    idempotency_key=key,
                    answers={},
                )
            except BaseException as exc:  # noqa: BLE001 - collected, asserted below
                errors[slot] = exc

    SASession.flush = gated_flush  # type: ignore[method-assign]
    try:
        threads = [threading.Thread(target=run, args=(slot,)) for slot in (0, 1)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
            assert not thread.is_alive()
    finally:
        SASession.flush = real_flush  # type: ignore[method-assign]
    file_engine.dispose()

    assert not errors, f"concurrent submit raised: {errors}"
    assert set(results) == {0, 1}
    assert results[0][1].id == results[1][1].id

    check_engine = create_engine(f"sqlite:///{db_file}")
    try:
        with sessionmaker(bind=check_engine)() as db:
            count = db.scalar(select(func.count(Evaluation.id)))
    finally:
        check_engine.dispose()
    assert count == 1


def test_deterministic_question_targets_one_fact_instead_of_several_true_statements():
    import re

    from app.assessment.mcq import _quotation_question

    options = [
        "Binary search halves a sorted list on each comparison",
        "Linear search checks each item in sequence",
        "A stack removes the most recently added item",
        "A queue removes the earliest added item",
    ]
    for correct in options:
        prompt = _quotation_question(correct, options)
        assert "which of the following statements is correct" not in prompt.lower()
        quotation = prompt.split("“", 1)[1].rsplit("”", 1)[0]
        pattern = re.escape(quotation).replace("____", r"[\w-]+")
        matching = [option for option in options if re.fullmatch(pattern, option)]
        assert matching == [correct]


def test_shuffle_options_moves_answer_and_keeps_it_correct():
    import random

    from app.assessment.mcq import GeneratedMCQ
    from app.services.assessment import shuffle_options

    rng = random.Random(7)
    text = GeneratedMCQ("Q?", ["right", "w1", "w2", "w3"], "right", None)
    letter = GeneratedMCQ("Q?", ["right", "w1", "w2", "w3"], "A", None)
    positions = set()
    for _ in range(40):
        t = shuffle_options(text, rng)
        assert t.correct_option == "right" and sorted(t.options) == sorted(text.options)
        positions.add(t.options.index("right"))
        lt = shuffle_options(letter, rng)
        assert lt.options["ABCD".index(lt.correct_option)] == "right"
    assert len(positions) > 1  # the answer no longer always sits first
    tf = GeneratedMCQ("Q?", ["True", "False"], "True", None, kind="true_false")
    assert shuffle_options(tf, rng) is tf


def test_quiz_levels_are_basic_medium_advanced_and_defined_for_the_ai():
    import pytest
    from pydantic import ValidationError

    from app.ai.prompts import get_prompt
    from app.schemas.assessment import AssessmentCreateRequest

    cid = "00000000-0000-0000-0000-000000000001"
    assert AssessmentCreateRequest(context_id=cid, difficulty="Basic").difficulty == "easy"
    assert AssessmentCreateRequest(context_id=cid, difficulty="advanced").difficulty == "hard"
    assert AssessmentCreateRequest(context_id=cid).difficulty == "medium"
    with pytest.raises(ValidationError):
        AssessmentCreateRequest(context_id=cid, difficulty="extreme")
    prompt = get_prompt("mcq_generation").render(difficulty="hard", count=3, material="M")
    assert "easy (Basic) = recall" in prompt and "hard (Advanced) = multi-step" in prompt


def test_library_quiz_questions_keep_the_ai_topic_label():
    import asyncio

    from app.assessment import mcq
    from app.assessment.schema import MCQItem, MCQSet

    class Provider:
        async def generate_structured(self, *, prompt, schema, prompt_version):
            return MCQSet(questions=[MCQItem(prompt="Which structure is last in, first out?",
                                             options=["Stack", "Queue", "Heap", "Tree"], correct_option="A",
                                             concept="Stack basics")])

    class Db:  # generate_mcqs_structured only reads material through the patched helpers
        pass

    import pytest
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(mcq, "_chunk_id_filter", lambda *a, **k: None)
    monkeypatch.setattr(mcq, "_material_preview", lambda *a, **k: "Stacks are LIFO.")
    monkeypatch.setattr(mcq, "get_llm_provider_for_owner", lambda *a, **k: Provider())
    try:
        questions = asyncio.run(mcq.generate_mcqs_structured(
            Db(), owner_id=None, context_id=None, count=1, difficulty="easy"))
    finally:
        monkeypatch.undo()
    assert questions[0].concept_name == "Stack basics"
