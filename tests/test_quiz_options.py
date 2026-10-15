"""Quizzes follow the learner's choices: format, length, source, timer and reveal mode."""

import random
import uuid

from fastapi.testclient import TestClient
from tests.test_assessments import MATERIAL, add_material, create_context, headers, register

from app.assessment.mcq import GeneratedMCQ
from app.assessment.shapes import shape_questions, short_answer_matches, to_short_answer, to_true_false

QUOTE = GeneratedMCQ(
    prompt="Complete the exact quotation from your study material. Which full statement fills the blank?\n"
           "“Loops repeat a ____ while a condition holds”",
    options=["Loops repeat a block while a condition holds", "Loops repeat a test while a condition holds",
             "Loops repeat a line while a condition holds", "Loops repeat a call while a condition holds"],
    correct_option="A", concept_id=None,
)


def test_true_false_keeps_the_answer_honest() -> None:
    for seed in range(6):
        item = to_true_false(QUOTE, random.Random(seed))
        assert item.kind == "true_false" and item.options == ["True", "False"]
        claims_correct = "“Loops repeat a block while a condition holds”" in item.prompt
        assert item.correct_option == ("A" if claims_correct else "B")


def test_quotation_becomes_fill_in_the_blank() -> None:
    item = to_short_answer(QUOTE)
    assert item.kind == "short_answer" and item.options == []
    assert item.correct_option == "block"
    assert "____" in item.prompt


def test_mixed_rotates_formats() -> None:
    kinds = [q.kind for q in shape_questions([QUOTE] * 6, "mixed", seed="x")]
    assert kinds == ["mcq", "true_false", "short_answer"] * 2


def test_short_answers_are_marked_by_meaning_not_exact_text() -> None:
    assert short_answer_matches("block", "a Block")
    assert short_answer_matches("an ordered immutable collection", "immutable ordered collection")
    assert not short_answer_matches("an ordered immutable collection", "a collection")
    assert not short_answer_matches("block", "I don't know")
    assert not short_answer_matches("block", "")


def _learner(client: TestClient) -> tuple[dict, str]:
    auth = register(client, f"quiz-{uuid.uuid4().hex[:8]}@example.com")
    token = auth["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id, MATERIAL)
    return headers(token), context_id


def _create(client: TestClient, h: dict, context_id: str, **body) -> object:
    return client.post("/api/v1/assessments", headers=h, json={"context_id": context_id, **body})


def test_default_length_is_ten_and_learners_can_ask_for_more(client: TestClient) -> None:
    h, cid = _learner(client)
    default = _create(client, h, cid)
    assert default.status_code == 201, default.text
    assert len(default.json()["questions"]) == 10
    assert _create(client, h, cid, question_count=50).status_code == 201
    assert _create(client, h, cid, question_count=51).status_code == 422


def test_chosen_format_shapes_every_question(client: TestClient) -> None:
    h, cid = _learner(client)
    tf = _create(client, h, cid, format="true_false", question_count=4).json()
    assert {q["kind"] for q in tf["questions"]} == {"true_false"}
    assert all(q["options"] == ["True", "False"] for q in tf["questions"])
    short = _create(client, h, cid, format="short_answer", question_count=4).json()
    assert {q["kind"] for q in short["questions"]} == {"short_answer"}
    assert all(q["options"] == [] for q in short["questions"])


def test_practice_mode_checks_each_answer_and_exam_mode_waits(client: TestClient) -> None:
    h, cid = _learner(client)
    practice = _create(client, h, cid, format="short_answer", question_count=3).json()
    assert practice["settings"]["reveal"] == "practice"
    attempt = client.post(f"/api/v1/assessments/{practice['id']}/attempts", headers=h).json()
    question = attempt["questions"][0]
    checked = client.post(
        f"/api/v1/assessments/{practice['id']}/attempts/{attempt['attempt_id']}/check", headers=h,
        json={"question_id": question["id"], "answer": "I don't know"},
    )
    assert checked.status_code == 200, checked.text
    body = checked.json()
    assert body["correct"] is False and body["correct_answer"] and body["explanation"]
    right = client.post(
        f"/api/v1/assessments/{practice['id']}/attempts/{attempt['attempt_id']}/check", headers=h,
        json={"question_id": question["id"], "answer": body["correct_answer"]},
    )
    assert right.json()["correct"] is True

    exam = _create(client, h, cid, reveal="exam", timing="total", time_limit_seconds=300, question_count=3).json()
    assert exam["settings"] == {"timing": "total", "time_limit_seconds": 300, "reveal": "exam", "source": "library"}
    exam_attempt = client.post(f"/api/v1/assessments/{exam['id']}/attempts", headers=h).json()
    blocked = client.post(
        f"/api/v1/assessments/{exam['id']}/attempts/{exam_attempt['attempt_id']}/check", headers=h,
        json={"question_id": exam_attempt["questions"][0]["id"], "answer": "x"},
    )
    assert blocked.status_code == 409


def test_timer_needs_a_limit(client: TestClient) -> None:
    h, cid = _learner(client)
    assert _create(client, h, cid, timing="per_question").status_code == 422


def test_quiz_from_chosen_chats_uses_only_those_chats(client: TestClient, session_factory) -> None:
    from uuid import UUID

    from app.db.models import StudySession
    from app.services.study import persist_conversation_turn

    h, cid = _learner(client)
    owner = UUID(client.get("/api/v1/auth/me", headers=h).json()["id"])
    with session_factory() as db:
        chat = StudySession(owner_id=owner, context_id=UUID(cid))
        db.add(chat)
        db.commit()
        persist_conversation_turn(
            db, owner_id=owner, session=chat, user_content="Explain stacks",
            assistant_content=("A stack stores items in last in first out order. Push places an item on top of the stack. "
                               "Pop removes the item that was added most recently. Peek reads the top item without removing it. "
                               "Stacks power undo features and function call tracking."),
            assistant_refs=[],
        )
        chat_id = str(chat.id)
    quiz = _create(client, h, cid, source="chats", session_ids=[chat_id], question_count=3)
    assert quiz.status_code == 201, quiz.text
    text = " ".join(q["prompt"] + " ".join(q["options"]) for q in quiz.json()["questions"])
    assert "stack" in text.lower() or "pop" in text.lower()
    assert quiz.json()["settings"]["source"] == "chats"
    assert _create(client, h, cid, source="chats", session_ids=[]).status_code == 422


def test_weak_spots_need_some_history_first(client: TestClient) -> None:
    h, cid = _learner(client)
    res = _create(client, h, cid, source="weak")
    assert res.status_code == 422
    assert "weak spots" in res.json()["detail"].lower()


class _SummaryProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.user = ""

    async def generate_text(self, *, system: str, user: str, prompt_version=None, temperature=0.0) -> str:
        self.calls += 1
        self.user = user
        return "You understand how functions are defined. Practise return values next."

    async def generate_structured(self, *, prompt: str, schema: type, prompt_version=None):
        raise RuntimeError("use the deterministic generator")


def _take_quiz(client: TestClient, h: dict, cid: str) -> tuple[str, str]:
    quiz = _create(client, h, cid, question_count=3).json()
    attempt = client.post(f"/api/v1/assessments/{quiz['id']}/attempts", headers=h).json()
    answers = {q["id"]: "I don't know" for q in attempt["questions"]}
    submitted = client.post(f"/api/v1/assessments/{quiz['id']}/attempts/{attempt['attempt_id']}/submit", headers=h,
                            json={"idempotency_key": str(uuid.uuid4()), "answers": answers})
    assert submitted.status_code == 200, submitted.text
    return quiz["id"], attempt["attempt_id"]


def test_summary_is_written_once_from_the_answers(client: TestClient, monkeypatch) -> None:
    import app.services.quiz_summary as quiz_summary

    h, cid = _learner(client)
    quiz_id, attempt_id = _take_quiz(client, h, cid)
    provider = _SummaryProvider()
    monkeypatch.setattr(quiz_summary, "get_llm_provider_for_owner", lambda db, owner_id: provider)
    url = f"/api/v1/assessments/{quiz_id}/attempts/{attempt_id}/summary"
    first = client.post(url, headers=h)
    assert first.status_code == 200, first.text
    assert first.json()["summary"].startswith("You understand")
    assert "I don't know" in provider.user and "WRONG" in provider.user
    assert client.post(url, headers=h).json() == first.json()
    assert provider.calls == 1


def test_summary_without_ai_still_points_to_a_next_step(client: TestClient) -> None:
    h, cid = _learner(client)
    quiz_id, attempt_id = _take_quiz(client, h, cid)
    summary = client.post(f"/api/v1/assessments/{quiz_id}/attempts/{attempt_id}/summary", headers=h).json()["summary"]
    assert "Explain this in chat" in summary
