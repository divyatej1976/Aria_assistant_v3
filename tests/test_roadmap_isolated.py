from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import Concept, Learner, LearnerConceptState, LearningContext
from app.services.roadmap import (
    create_roadmap,
    get_roadmap,
    list_roadmaps,
    sync_roadmap_ticks,
)


@pytest.mark.parametrize("filtered", [True, False])
def test_many_roadmaps_share_reads_and_one_commit(db_session, test_user_and_context, filtered):
    from sqlalchemy import event

    from app.db.models import Roadmap, RoadmapMilestone

    learner, context = test_user_and_context
    owner_id, context_id = learner.id, context.id
    concept = Concept(owner_id=owner_id, context_id=context_id, name="Skill")
    db_session.add(concept)
    db_session.flush()
    db_session.add(LearnerConceptState(owner_id=owner_id, concept_id=concept.id,
                                      state="SUPPORTED", confidence=90, reason="Evidence"))
    for index in range(30):
        roadmap = Roadmap(owner_id=owner_id, context_id=context_id, goal=f"Goal {index}")
        db_session.add(roadmap)
        db_session.flush()
        db_session.add(RoadmapMilestone(owner_id=owner_id, roadmap_id=roadmap.id,
                                       phase_name="Foundations", title="Skill", key_skills=["Skill"]))
    other = LearningContext(owner_id=owner_id, title="Other subject")
    db_session.add(other)
    db_session.flush()
    unrelated = Concept(owner_id=owner_id, context_id=other.id, name="Skill")
    other_roadmap = Roadmap(owner_id=owner_id, context_id=other.id, goal="Other goal")
    db_session.add_all([unrelated, other_roadmap])
    db_session.flush()
    db_session.add_all([
        LearnerConceptState(owner_id=owner_id, concept_id=unrelated.id,
                            state="NEEDS_REVIEW", confidence=10, reason="Other subject evidence"),
        RoadmapMilestone(owner_id=owner_id, roadmap_id=other_roadmap.id,
                         phase_name="Foundations", title="Skill", key_skills=["Skill"]),
    ])
    db_session.commit()
    reads, commits = [], []

    def query(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            reads.append(statement)

    def committed(session):
        commits.append(1)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", query)
    event.listen(db_session, "after_commit", committed)
    try:
        summaries = list_roadmaps(db_session, owner_id=owner_id, context_id=context_id if filtered else None)
    finally:
        event.remove(engine, "before_cursor_execute", query)
        event.remove(db_session, "after_commit", committed)
    assert len(summaries) == (30 if filtered else 31)
    assert all(summary.total == summary.done == 1 for summary in summaries if summary.goal != "Other goal")
    if not filtered:
        assert next(summary for summary in summaries if summary.goal == "Other goal").done == 0
    assert len(reads) == 3
    assert len(commits) == 1


@pytest.fixture
def db_session(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture
def test_user_and_context(db_session):
    learner = Learner(
        id=uuid4(),
        owner_id=uuid4(),
        email=f"learner_{uuid4().hex[:8]}@example.com",
        display_name="Test Learner",
    )
    learner.owner_id = learner.id
    db_session.add(learner)

    context = LearningContext(
        id=uuid4(),
        owner_id=learner.id,
        title="Go & Systems Context",
        description="Learning systems programming",
    )
    db_session.add(context)
    db_session.commit()
    return learner, context


@pytest.mark.asyncio
async def test_create_goal_isolated_roadmap(db_session, test_user_and_context):
    learner, context = test_user_and_context

    roadmap = await create_roadmap(
        db_session,
        owner_id=learner.id,
        goal="Master Go Backend Microservices",
        level="Intermediate",
        target_date="2026-12-01",
        context_id=context.id,
    )

    assert roadmap.id is not None
    assert roadmap.goal == "Master Go Backend Microservices"
    assert roadmap.level == "Intermediate"

    data = get_roadmap(db_session, owner_id=learner.id, roadmap_id=roadmap.id)
    assert data.total > 0
    assert len(data.tiers) > 0
    assert data.done == 0

    # Verify tiered phase structure
    phase_names = [tier.name for tier in data.tiers]
    assert "Foundations" in phase_names
    assert "Core Concepts" in phase_names


@pytest.mark.asyncio
async def test_document_upload_does_not_pollute_roadmap(db_session, test_user_and_context):
    learner, context = test_user_and_context

    # 1. Create a roadmap for Go
    roadmap = await create_roadmap(
        db_session,
        owner_id=learner.id,
        goal="Master Go Backend Microservices",
        level="Intermediate",
        context_id=context.id,
    )
    initial_data = get_roadmap(db_session, owner_id=learner.id, roadmap_id=roadmap.id)
    initial_titles = {
        topic.title for tier in initial_data.tiers for topic in tier.topics
    }

    # 2. Simulate document upload that extracts completely unrelated concepts
    unrelated_concepts = ["Sourdough Fermentation", "Flour Hydration", "Oven Steam Injection"]
    for c_name in unrelated_concepts:
        db_session.add(
            Concept(
                id=uuid4(),
                owner_id=learner.id,
                context_id=context.id,
                name=c_name,
            )
        )
    db_session.commit()

    # 3. Fetch roadmap again and verify ZERO pollution
    refreshed_data = get_roadmap(db_session, owner_id=learner.id, roadmap_id=roadmap.id)
    refreshed_titles = {
        topic.title for tier in refreshed_data.tiers for topic in tier.topics
    }

    assert refreshed_titles == initial_titles
    for c_name in unrelated_concepts:
        assert c_name not in refreshed_titles


@pytest.mark.asyncio
async def test_selective_auto_ticking_only_on_matched_skills(db_session, test_user_and_context):
    learner, context = test_user_and_context

    roadmap = await create_roadmap(
        db_session,
        owner_id=learner.id,
        goal="Master Go Backend Microservices",
        level="Beginner",
        context_id=context.id,
    )
    data = get_roadmap(db_session, owner_id=learner.id, roadmap_id=roadmap.id)
    assert data.done == 0

    # Pick a milestone from Foundations
    foundations_tier = next(t for t in data.tiers if t.name == "Foundations")
    first_milestone = foundations_tier.topics[0]
    matched_skill = first_milestone.key_skills[0] if first_milestone.key_skills else "Core Syntax"

    # Add a concept matching this skill that reaches SUPPORTED
    matched_concept = Concept(
        id=uuid4(),
        owner_id=learner.id,
        context_id=context.id,
        name=matched_skill,
    )
    db_session.add(matched_concept)
    db_session.flush()

    db_session.add(
        LearnerConceptState(
            id=uuid4(),
            owner_id=learner.id,
            concept_id=matched_concept.id,
            state="SUPPORTED",
            confidence=95,
            reason="Demonstrated mastery on quizzes",
        )
    )

    # Also add an UNRELATED concept that is SUPPORTED
    unrelated_concept = Concept(
        id=uuid4(),
        owner_id=learner.id,
        context_id=context.id,
        name="Ancient Roman History",
    )
    db_session.add(unrelated_concept)
    db_session.flush()

    db_session.add(
        LearnerConceptState(
            id=uuid4(),
            owner_id=learner.id,
            concept_id=unrelated_concept.id,
            state="SUPPORTED",
            confidence=100,
            reason="Demonstrated mastery on history quiz",
        )
    )
    db_session.commit()

    # Sync and verify
    sync_roadmap_ticks(db_session, owner_id=learner.id, roadmap=roadmap)
    updated_data = get_roadmap(db_session, owner_id=learner.id, roadmap_id=roadmap.id)

    # One supported skill establishes partial progress, not full mastery.
    updated_first_milestone = next(
        topic
        for tier in updated_data.tiers
        for topic in tier.topics
        if topic.id == first_milestone.id
    )
    assert updated_first_milestone.ticked is False
    assert updated_first_milestone.state == "DEVELOPING"

    for skill in first_milestone.key_skills[1:]:
        concept = Concept(owner_id=learner.id, context_id=context.id, name=skill)
        db_session.add(concept)
        db_session.flush()
        db_session.add(LearnerConceptState(
            owner_id=learner.id, concept_id=concept.id, state="SUPPORTED",
            confidence=95, reason="Demonstrated mastery on quizzes",
        ))
    db_session.commit()
    complete = get_roadmap(db_session, owner_id=learner.id, roadmap_id=roadmap.id)
    completed_first = next(topic for tier in complete.tiers for topic in tier.topics
                           if topic.id == first_milestone.id)
    assert completed_first.ticked is True
    assert completed_first.confidence == 95

    # Unrelated concept must NOT exist as a milestone in this roadmap
    all_titles = {
        topic.title for tier in updated_data.tiers for topic in tier.topics
    }
    assert "Ancient Roman History" not in all_titles


@pytest.mark.asyncio
async def test_multiple_separate_roadmaps(db_session, test_user_and_context):
    learner, context = test_user_and_context

    r1 = await create_roadmap(
        db_session,
        owner_id=learner.id,
        goal="Master Go Backend Microservices",
        level="Intermediate",
        context_id=context.id,
    )
    r2 = await create_roadmap(
        db_session,
        owner_id=learner.id,
        goal="Machine Learning with PyTorch",
        level="Beginner",
        context_id=context.id,
    )

    summaries = list_roadmaps(db_session, owner_id=learner.id, context_id=context.id)
    assert len(summaries) >= 2
    assert {str(r1.id), str(r2.id)}.issubset({summary.id for summary in summaries})
    goals = {s.goal for s in summaries}
    assert "Master Go Backend Microservices" in goals
    assert "Machine Learning with PyTorch" in goals


def test_roadmap_api_endpoints(client: TestClient):
    # 1. Register test user
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": f"api_user_{uuid4().hex[:6]}@example.com", "password": "password-123", "display_name": "API Learner"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 2. Create learning context
    ctx_res = client.post(
        "/api/v1/contexts",
        headers=auth_headers,
        json={"title": "Cloud Context", "description": "Cloud native engineering"},
    )
    assert ctx_res.status_code == 201
    context_id = ctx_res.json()["id"]

    # 3. Create roadmap via POST /api/v1/roadmaps
    create_res = client.post(
        "/api/v1/roadmaps",
        headers=auth_headers,
        json={
            "goal": "Cloud Kubernetes Architecture",
            "level": "Advanced",
            "target_date": "2026-11-15",
            "context_id": context_id,
        },
    )
    assert create_res.status_code == 201
    roadmap_data = create_res.json()
    roadmap_id = roadmap_data["id"]
    assert roadmap_data["goal"] == "Cloud Kubernetes Architecture"
    assert roadmap_data["level"] == "Advanced"
    assert len(roadmap_data["tiers"]) > 0
    assert roadmap_data["total"] > 0
    assert roadmap_data["done"] == 0

    # 4. List roadmaps via GET /api/v1/roadmaps
    list_res = client.get(
        f"/api/v1/roadmaps?context_id={context_id}",
        headers=auth_headers,
    )
    assert list_res.status_code == 200
    summaries = list_res.json()
    assert len(summaries) == 1
    assert summaries[0]["id"] == roadmap_id
    assert summaries[0]["goal"] == "Cloud Kubernetes Architecture"

    # 5. Get roadmap details via GET /api/v1/roadmaps/{id}
    detail_res = client.get(
        f"/api/v1/roadmaps/{roadmap_id}",
        headers=auth_headers,
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == roadmap_id

    # 6. Delete roadmap via DELETE /api/v1/roadmaps/{id}
    del_res = client.delete(
        f"/api/v1/roadmaps/{roadmap_id}",
        headers=auth_headers,
    )
    assert del_res.status_code == 200
    assert del_res.json() == {"deleted": True}

    # 7. Verify 404 after deletion
    after_del = client.get(
        f"/api/v1/roadmaps/{roadmap_id}",
        headers=auth_headers,
    )
    assert after_del.status_code == 404
