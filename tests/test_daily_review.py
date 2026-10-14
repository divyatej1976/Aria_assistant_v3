from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from tests.test_resources_study import create_context, headers, register

from app.db.models import Assessment, ConversationMessage

LESSON = (
    "Transactions group related database changes into one atomic operation. "
    "Isolation prevents concurrent transactions from interfering with each other. "
    "Durability preserves committed changes even after a server restart. "
    "Consistency keeps every database constraint valid before and after transactions. "
    "Atomicity means all changes commit together or all changes are rolled back."
)


def seed_day(client, session_factory, *, email="daily@example.com"):
    token = register(client, email)["access_token"]
    context_id = create_context(client, token)
    sid = client.post("/api/v1/study/sessions", headers=headers(token),
                      json={"context_id": context_id}).json()["id"]
    with session_factory() as db:
        for position, (role, content) in enumerate([
            ("user", "Explain database transactions and their four properties."),
            ("assistant", LESSON),
        ], 1):
            db.add(ConversationMessage(owner_id=UUID(register_owner(client, token)),
                                      study_session_id=UUID(sid), role=role, content=content,
                                      position=position, source_refs=[]))
        db.commit()
    return token, context_id


def register_owner(client, token):
    return client.get("/api/v1/auth/me", headers=headers(token)).json()["id"]


def test_daily_review_without_notes_is_durable_and_not_mastery(client, session_factory):
    token, cid = seed_day(client, session_factory)
    url = f"/api/v1/study/contexts/{cid}/finish-day"
    result = client.post(url, headers=headers(token))
    assert result.status_code == 200, result.text
    assert client.post(url, headers=headers(token)).json() == result.json()
    detail = client.get(f"/api/v1/assessments/{result.json()['assessment_id']}", headers=headers(token)).json()
    assert detail["mode"] == "DAILY_REVIEW"
    assert len(detail["questions"]) == 5
    assert all(question["concept_id"] is None for question in detail["questions"])
    assert all("conversation" in question["prompt"] for question in detail["questions"])
    with session_factory() as db:
        assert len(list(db.scalars(select(Assessment)))) == 1


def test_daily_review_excludes_yesterday_and_other_owners(client, session_factory):
    token, cid = seed_day(client, session_factory)
    stranger = register(client, "stranger@example.com")["access_token"]
    url = f"/api/v1/study/contexts/{cid}/finish-day"
    assert client.post(url, headers=headers(stranger)).status_code == 422
    with session_factory() as db:
        for message in db.scalars(select(ConversationMessage)):
            message.created_at = datetime.now(UTC) - timedelta(days=2)
        db.commit()
    result = client.post(url, headers=headers(token))
    assert result.status_code == 422
    with session_factory() as db:
        assert not list(db.scalars(select(Assessment)))


def test_grounded_daily_review_drives_plan_and_roadmap(client, session_factory, monkeypatch):
    from app.db.models import (
        AssessmentQuestion,
        Concept,
        ConceptChunk,
        LearnerConceptState,
        PlannedTask,
        Resource,
        ResourceChunk,
        Roadmap,
        RoadmapMilestone,
    )

    token, cid = seed_day(client, session_factory)
    owner = UUID(register_owner(client, token))
    async def already_synced(*args, **kwargs):
        return []
    monkeypatch.setattr("app.services.daily_review.sync_concepts", already_synced)
    with session_factory() as db:
        concept = Concept(owner_id=owner, context_id=UUID(cid), name="transactions")
        resource = Resource(owner_id=owner, context_id=UUID(cid), title="Transactions", resource_type="TEXT", processing_status="READY")
        roadmap = Roadmap(owner_id=owner, context_id=UUID(cid), goal="Learn transactions")
        db.add_all([concept, resource, roadmap])
        db.flush()
        chunk = ResourceChunk(owner_id=owner, resource_id=resource.id, content=LESSON, chunk_index=0)
        db.add(chunk)
        db.flush()
        db.add(ConceptChunk(owner_id=owner, concept_id=concept.id, chunk_id=chunk.id))
        milestone = RoadmapMilestone(owner_id=owner, roadmap_id=roadmap.id, phase_name="Foundations", title="Transactions", key_skills=["transactions"])
        db.add(milestone)
        answer = db.scalar(select(ConversationMessage).where(ConversationMessage.role == "assistant"))
        answer.content = " ".join("Transactions: " + sentence.strip() + "." for sentence in LESSON.split(".") if sentence.strip())
        answer.source_refs = [{"chunk_id": str(chunk.id), "resource_id": str(resource.id), "title": resource.title, "score": 1}]
        db.commit()
        concept_id, milestone_id = concept.id, milestone.id
    result = client.post(f"/api/v1/study/contexts/{cid}/finish-day", headers=headers(token))
    assert result.status_code == 200, result.text
    aid = result.json()["assessment_id"]
    with session_factory() as db:
        questions = list(db.scalars(select(AssessmentQuestion).where(AssessmentQuestion.assessment_id == UUID(aid))))
        assert all(question.concept_id == concept_id for question in questions)
        correct = {str(question.id): question.correct_option for question in questions}
        wrong = {str(question.id): "B" if question.correct_option == "A" else "A" for question in questions}
    def submit(answers):
        attempt = client.post(f"/api/v1/assessments/{aid}/attempts", headers=headers(token)).json()["attempt_id"]
        url = f"/api/v1/assessments/{aid}/attempts/{attempt}/submit"
        body = {"answers": answers, "idempotency_key": "daily-test-" + attempt}
        response = client.post(url, headers=headers(token), json=body)
        assert response.status_code == 200, response.text
        assert client.post(url, headers=headers(token), json=body).status_code == 200
        return url, body
    replay_url, replay_body = submit(wrong)
    with session_factory() as db:
        assert db.scalar(select(LearnerConceptState)).state == "NEEDS_REVIEW"
        assert len(list(db.scalars(select(PlannedTask)))) == 1
        assert db.get(RoadmapMilestone, milestone_id).state == "NEEDS_REVIEW"
        task = db.scalar(select(PlannedTask))
        db.delete(task)
        db.commit()
    assert client.post(replay_url, headers=headers(token), json=replay_body).status_code == 200
    with session_factory() as db:
        assert not list(db.scalars(select(PlannedTask)))
    submit(wrong)
    submit(correct)
    with session_factory() as db:
        assert db.scalar(select(LearnerConceptState)).state == "SUPPORTED"
        assert db.get(RoadmapMilestone, milestone_id).state == "SUPPORTED"
        assert len(list(db.scalars(select(PlannedTask)))) == 1
        assert db.scalar(select(PlannedTask)).status == "DONE"


def test_daily_review_uses_llm_without_notes(client, session_factory, monkeypatch):
    from app.assessment.schema import MCQItem, MCQSet

    calls = []
    class Provider:
        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            return MCQSet(questions=[MCQItem(
                prompt="What does transaction atomicity guarantee?",
                options=["All changes commit or none do", "Every query is fast", "No disk space is used", "Backups are automatic"],
                correct_option="A",
            )])
    monkeypatch.setattr("app.assessment.mcq.get_llm_provider_for_owner", lambda *args, **kwargs: Provider())
    token, cid = seed_day(client, session_factory)
    response = client.post(f"/api/v1/study/contexts/{cid}/finish-day", headers=headers(token))
    assert response.status_code == 200, response.text
    assert len(calls) == 1
    assert "Transactions group" in calls[0]["prompt"]
    assert "unverified conversation" in calls[0]["prompt"]


def test_simultaneous_daily_creation_keeps_one_assessment(client, session_factory, engine, monkeypatch):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    import pytest

    from app.assessment.mcq import GeneratedMCQ
    from app.services.assessment import create_assessment

    if engine.dialect.name != "postgresql":
        pytest.skip("Requires independent PostgreSQL transactions")
    token, cid = seed_day(client, session_factory)
    owner = UUID(register_owner(client, token))
    simultaneous = Barrier(2)
    async def generate(*args, **kwargs):
        simultaneous.wait(timeout=15)
        return [GeneratedMCQ("What does atomicity guarantee?", ["All or nothing", "Speed", "Backups", "Indexes"], "A", None)]
    monkeypatch.setattr("app.services.assessment.generate_conversation_mcqs", generate)
    def create():
        with session_factory() as db:
            return asyncio.run(create_assessment(
                db, owner_id=owner, context_id=UUID(cid), format_name="mcq",
                question_count=1, difficulty="medium", mode="DAILY_REVIEW", concept_ids=[],
                study_transcript=LESSON, daily_review_date="2026-10-14",
            )).id
    with ThreadPoolExecutor(max_workers=2) as threads:
        first, second = list(threads.map(lambda _: create(), range(2)))
    assert first == second
    with session_factory() as db:
        assert len(list(db.scalars(select(Assessment)))) == 1


def test_daily_review_stays_visible_after_large_assessment_history(client, session_factory):
    token, cid = seed_day(client, session_factory)
    owner = UUID(register_owner(client, token))
    with session_factory() as db:
        db.add_all([Assessment(owner_id=owner, context_id=UUID(cid),
                               created_at=datetime.now(UTC) - timedelta(days=2)) for _ in range(105)])
        db.commit()
    result = client.post(f"/api/v1/study/contexts/{cid}/finish-day", headers=headers(token))
    assert result.status_code == 200, result.text
    items = client.get(f"/api/v1/assessments?context_id={cid}", headers=headers(token)).json()
    assert len(items) == 100
    assert items[0]["id"] == result.json()["assessment_id"]
    remainder = client.get(f"/api/v1/assessments?context_id={cid}&offset=100", headers=headers(token)).json()
    assert len(remainder) == 6
    assert not {item["id"] for item in items} & {item["id"] for item in remainder}


def test_daily_review_accepts_short_learning_questions(client, session_factory):
    token, cid = seed_day(client, session_factory)
    with session_factory() as db:
        db.scalar(select(ConversationMessage).where(ConversationMessage.role == "user")).content = "SQL?"
        db.commit()
    result = client.post(f"/api/v1/study/contexts/{cid}/finish-day", headers=headers(token))
    assert result.status_code == 200, result.text


def test_daily_review_rejects_small_talk_even_with_long_reply(client, session_factory):
    token, cid = seed_day(client, session_factory)
    with session_factory() as db:
        db.scalar(select(ConversationMessage).where(ConversationMessage.role == "user")).content = "good evening!!"
        db.commit()
    result = client.post(f"/api/v1/study/contexts/{cid}/finish-day", headers=headers(token))
    assert result.status_code == 422, result.text
    with session_factory() as db:
        assert not list(db.scalars(select(Assessment)))


def test_daily_review_uses_local_midnight_not_utc_date(client, session_factory, monkeypatch):
    from app.db.models import LearnerPreference, StudySession

    class ReviewClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 13, 19, tzinfo=UTC).astimezone(tz or UTC)

    monkeypatch.setattr("app.services.daily_review.datetime", ReviewClock)
    token, cid = seed_day(client, session_factory)
    owner = UUID(register_owner(client, token))
    with session_factory() as db:
        db.add(LearnerPreference(owner_id=owner, key="timezone", value="Asia/Calcutta"))
        for message in db.scalars(select(ConversationMessage)):
            message.created_at = datetime(2026, 10, 13, 18, 45, tzinfo=UTC)
        old_session = StudySession(owner_id=owner, context_id=UUID(cid))
        db.add(old_session)
        db.flush()
        db.add_all([
            ConversationMessage(owner_id=owner, study_session_id=old_session.id, role="user",
                                position=1, content="Explain yesterday's topic",
                                created_at=datetime(2026, 10, 13, 17, tzinfo=UTC)),
            ConversationMessage(owner_id=owner, study_session_id=old_session.id, role="assistant",
                                position=2, content="Yesterday's learning should not appear in today's review.",
                                created_at=datetime(2026, 10, 13, 17, tzinfo=UTC)),
        ])
        db.commit()
    result = client.post(f"/api/v1/study/contexts/{cid}/finish-day", headers=headers(token))
    assert result.status_code == 200, result.text
    assert result.json()["review_date"] == "2026-10-14"
    detail = client.get(f"/api/v1/assessments/{result.json()['assessment_id']}", headers=headers(token)).json()
    assert all("Yesterday" not in option for question in detail["questions"] for option in question["options"])
