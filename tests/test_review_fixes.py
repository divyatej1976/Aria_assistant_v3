"""Regressions for failures reproduced in the full-stack review."""

from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.db.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AttemptAnswer,
    Concept,
    ConversationMessage,
    Evaluation,
    Evidence,
    LearnerConceptState,
    Note,
    Roadmap,
    RoadmapMilestone,
)
from app.services.roadmap import get_roadmap


def learner(client, email):
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "review-password-123"})
    assert response.status_code == 201
    data = response.json()
    return UUID(data["learner_id"]), {"Authorization": "Bearer " + data["access_token"]}


def subject(client, headers, title):
    response = client.post("/api/v1/contexts", headers=headers, json={"title": title})
    assert response.status_code == 201
    return UUID(response.json()["id"])


def test_first_text_ingestion_database_failure_preserves_retryable_source(client, session_factory, engine):
    from sqlalchemy import event

    from app.db.models import Resource, ResourceChunk

    owner, headers = learner(client, "first-ingestion-failure@example.com")
    context = subject(client, headers, "Biology")
    text = "Photosynthesis converts light energy into chemical energy in chloroplasts."

    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO RESOURCE_CHUNKS"):
            raise RuntimeError("private database details")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        response = client.post("/api/v1/resources/text", headers=headers, json={
            "context_id": str(context), "title": "Original", "text": text,
        })
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    assert response.status_code == 201
    item = response.json()
    assert item["processing_status"] == "FAILED"
    assert item["error_detail"] == "Resource processing failed. Please retry."
    resource_id = UUID(item["id"])
    with session_factory() as db:
        resource = db.get(Resource, resource_id)
        assert resource.owner_id == owner
        assert resource.source_text == text
        assert db.scalar(select(func.count()).select_from(ResourceChunk).where(
            ResourceChunk.resource_id == resource_id
        )) == 0
    retry = client.post(f"/api/v1/resources/{resource_id}/process", headers=headers)
    assert retry.status_code == 200
    assert retry.json()["processing_status"] == "READY"
    assert retry.json()["chunk_count"] > 0


@pytest.mark.parametrize("deleted_index", [0, 2])
def test_chat_continues_after_deleting_an_early_message(client, session_factory, deleted_index):
    owner, headers = learner(client, "deletion@example.com")
    context = subject(client, headers, "Algorithms")
    sid = client.post("/api/v1/study/sessions", headers=headers, json={"context_id": str(context)}).json()["id"]
    path = f"/api/v1/study/sessions/{sid}/messages"
    for _ in range(2):
        assert client.post(path, headers=headers, json={"content": "hello"}).status_code == 200
    old = client.get(path, headers=headers).json()
    assert client.delete(path + "/" + old[deleted_index]["id"], headers=headers).status_code == 200
    assert client.post(path, headers=headers, json={"content": "hello"}).status_code == 200
    with session_factory() as db:
        positions = list(db.scalars(select(ConversationMessage.position).where(
            ConversationMessage.owner_id == owner, ConversationMessage.study_session_id == UUID(sid)
        ).order_by(ConversationMessage.position)))
    assert positions[-2:] == [5, 6]
    assert len(positions) == len(set(positions)) == 5


def test_foreign_roadmap_context_rejected_before_generation(client, monkeypatch, session_factory):
    owner, headers = learner(client, "roadmap-owner@example.com")
    _, other_headers = learner(client, "roadmap-other@example.com")
    foreign = subject(client, other_headers, "Foreign")

    async def unexpected_generation(**kwargs):
        raise AssertionError("Invalid ownership must be rejected before any provider call")

    monkeypatch.setattr("app.services.roadmap.generate_roadmap_tree", unexpected_generation)
    response = client.post("/api/v1/roadmaps", headers=headers, json={"goal": "Python", "context_id": str(foreign)})
    assert response.status_code == 422
    with session_factory() as db:
        assert db.scalar(select(func.count(Roadmap.id)).where(Roadmap.owner_id == owner)) == 0


@pytest.mark.parametrize("foreign_owner", [True, False])
def test_note_rejects_foreign_or_other_subject_concept(client, session_factory, foreign_owner):
    owner, headers = learner(client, "note-owner@example.com")
    own_context = subject(client, headers, "Own")
    concept_owner = owner
    other_headers = headers
    if foreign_owner:
        concept_owner, other_headers = learner(client, "note-other@example.com")
    other_context = subject(client, other_headers, "Other")
    with session_factory() as db:
        concept = Concept(owner_id=concept_owner, context_id=other_context, name="Functions")
        db.add(concept)
        db.commit()
        cid = str(concept.id)
    response = client.post("/api/v1/notes", headers=headers, json={
        "context_id": str(own_context), "concept_id": cid, "title": "Example", "body": "Study",
    })
    assert response.status_code == 422
    with session_factory() as db:
        assert db.scalar(select(func.count(Note.id)).where(Note.owner_id == owner)) == 0


def test_note_generation_rejects_other_subject_conversation_before_provider(client, monkeypatch):
    _, headers = learner(client, "note-session@example.com")
    first = subject(client, headers, "First")
    second = subject(client, headers, "Second")
    sid = client.post("/api/v1/study/sessions", headers=headers, json={"context_id": str(first)}).json()["id"]
    assert client.post(f"/api/v1/study/sessions/{sid}/messages", headers=headers, json={"content": "hello"}).status_code == 200

    def unexpected_provider(*args, **kwargs):
        raise AssertionError("Invalid scope must not reach provider selection")

    monkeypatch.setattr("app.services.notes.get_llm_provider_for_owner", unexpected_provider)
    response = client.post("/api/v1/notes/generate", headers=headers, json={
        "context_id": str(second), "study_session_id": sid,
    })
    assert response.status_code == 422


@pytest.mark.parametrize("operation", ["answers", "submit"])
def test_wrong_parent_assessment_leaves_everything_unchanged(client, session_factory, operation):
    owner, headers = learner(client, "assessment-parent@example.com")
    context = subject(client, headers, "Algorithms")
    with session_factory() as db:
        parents = [Assessment(owner_id=owner, context_id=context, format="mcq", mode="BASELINE", configuration={})
                   for _ in range(2)]
        db.add_all(parents)
        db.flush()
        question = AssessmentQuestion(owner_id=owner, assessment_id=parents[1].id, position=1,
                                      prompt="Review", options=["one", "two", "three", "four"], correct_option="A")
        db.add(question)
        db.commit()
        first, second = [str(item.id) for item in parents]
        question_id = str(question.id)
    attempt = client.post(f"/api/v1/assessments/{second}/attempts", headers=headers).json()["attempt_id"]
    path = f"/api/v1/assessments/{first}/attempts/{attempt}/{operation}"
    payload = {"answers": {question_id: "A"}}
    if operation == "submit":
        payload["idempotency_key"] = "review-wrong-parent"
    response = getattr(client, "post" if operation == "submit" else "put")(path, headers=headers, json=payload)
    assert response.status_code == 404
    with session_factory() as db:
        assert db.get(AssessmentAttempt, UUID(attempt)).status == "IN_PROGRESS"
        for model in [AttemptAnswer, Evaluation, Evidence]:
            assert db.scalar(select(func.count(model.id)).where(model.owner_id == owner)) == 0


def test_roadmap_requires_scoped_full_coverage_and_reverses_completion(client, session_factory):
    owner, headers = learner(client, "roadmap-evidence@example.com")
    context = subject(client, headers, "Python")
    other = subject(client, headers, "Other")
    with session_factory() as db:
        roadmap = Roadmap(owner_id=owner, context_id=context, goal="Python", level="Beginner")
        db.add(roadmap)
        db.flush()
        milestone = RoadmapMilestone(owner_id=owner, roadmap_id=roadmap.id, phase_name="Foundations",
                                     phase_order=0, order_index=0, title="Basics", key_skills=["Functions", "Loops"],
                                     prerequisites=[], state="NOT_STARTED", confidence=0)
        db.add(milestone)
        unrelated = Concept(owner_id=owner, context_id=other, name="Functions")
        db.add(unrelated)
        db.flush()
        db.add(LearnerConceptState(owner_id=owner, concept_id=unrelated.id, state="SUPPORTED", confidence=100, reason="test"))
        db.commit()
        assert get_roadmap(db, owner_id=owner, roadmap_id=roadmap.id).done == 0
        states = []
        for name, confidence in [("Functions", 50), ("Loops", 70)]:
            concept = Concept(owner_id=owner, context_id=context, name=name)
            db.add(concept)
            db.flush()
            state = LearnerConceptState(owner_id=owner, concept_id=concept.id, state="SUPPORTED",
                                        confidence=confidence, reason="test")
            db.add(state)
            db.commit()
            states.append(state)
            result = get_roadmap(db, owner_id=owner, roadmap_id=roadmap.id)
            assert result.done == (1 if len(states) == 2 else 0)
        assert result.tiers[0].topics[0].confidence == 50
        states[0].state = "NEEDS_REVIEW"
        states[0].confidence = 0
        db.commit()
        result = get_roadmap(db, owner_id=owner, roadmap_id=roadmap.id)
        assert result.done == 0
        assert result.tiers[0].topics[0].state == "NEEDS_REVIEW"
        assert result.tiers[0].topics[0].confidence == 0


def test_roadmap_prerequisites_and_cycles_block_completion(client, session_factory):
    owner, headers = learner(client, "roadmap-prereq@example.com")
    context = subject(client, headers, "Python")
    with session_factory() as db:
        roadmap = Roadmap(owner_id=owner, context_id=context, goal="Python", level="Beginner")
        db.add(roadmap)
        db.flush()
        milestones = []
        for order, (name, prereqs) in enumerate([("Functions", []), ("Loops", ["Functions"])]):
            milestone = RoadmapMilestone(owner_id=owner, roadmap_id=roadmap.id, phase_name="Foundations",
                                         phase_order=0, order_index=order, title=name, key_skills=[name], prerequisites=prereqs)
            db.add(milestone)
            milestones.append(milestone)
        concept = Concept(owner_id=owner, context_id=context, name="Loops")
        db.add(concept)
        db.flush()
        db.add(LearnerConceptState(owner_id=owner, concept_id=concept.id, state="SUPPORTED", confidence=60, reason="test"))
        db.commit()
        assert get_roadmap(db, owner_id=owner, roadmap_id=roadmap.id).done == 0
        concept = Concept(owner_id=owner, context_id=context, name="Functions")
        db.add(concept)
        db.flush()
        db.add(LearnerConceptState(owner_id=owner, concept_id=concept.id, state="SUPPORTED", confidence=60, reason="test"))
        db.commit()
        assert get_roadmap(db, owner_id=owner, roadmap_id=roadmap.id).done == 2
        milestones[0].prerequisites = ["Loops"]
        db.commit()
        assert get_roadmap(db, owner_id=owner, roadmap_id=roadmap.id).done == 0


@pytest.mark.parametrize("payload", [
    {"goal": " "}, {"goal": "x" * 256}, {"goal": "Biology", "level": "anything"},
    {"goal": "Biology", "target_date": "2026-02-30"},
    {"goal": "Biology", "target_date": "20261005"},
])
def test_roadmap_invalid_input_is_rejected_before_generation(client, monkeypatch, payload):
    _, headers = learner(client, "roadmap-input@example.com")
    def unexpected(*args, **kwargs):
        raise AssertionError("Invalid input must not invoke roadmap generation")
    monkeypatch.setattr("app.services.roadmap.generate_roadmap_tree", unexpected)
    assert client.post("/api/v1/roadmaps", headers=headers, json=payload).status_code == 422


def test_offline_roadmap_for_biology_is_an_honest_learning_starter():
    from app.services.roadmap import _fallback_roadmap_tree
    tree = _fallback_roadmap_tree("Understand human anatomy", "Beginner")
    text = tree.model_dump_json().lower()
    assert "offline starter plan" in text
    assert "human anatomy" in text
    for programming_claim in ("core syntax", "loops", "variables", "deployment", "production-grade"):
        assert programming_claim not in text


@pytest.mark.parametrize("failure", ["embedding", "count", "database"])
def test_failed_resource_replacement_preserves_usable_source_and_links(
    client, session_factory, engine, monkeypatch, failure
):
    from sqlalchemy import event

    from app.db.models import ConceptChunk, Resource, ResourceChunk

    owner, headers = learner(client, "replace-preserve@example.com")
    context = subject(client, headers, "Biology")
    original_text = "Photosynthesis converts light energy into chemical energy in chloroplasts."
    created = client.post("/api/v1/resources/text", headers=headers, json={
        "context_id": str(context), "title": "Original", "text": original_text,
    }).json()
    resource_id = UUID(created["id"])
    with session_factory() as db:
        chunks = list(db.scalars(select(ResourceChunk).where(ResourceChunk.resource_id == resource_id)))
        ids = {chunk.id for chunk in chunks}
        concept = Concept(owner_id=owner, context_id=context, name="Photosynthesis")
        db.add(concept)
        db.flush()
        db.add(ConceptChunk(owner_id=owner, concept_id=concept.id, chunk_id=chunks[0].id))
        db.commit()
    if failure != "database":
        class BrokenEmbeddings:
            async def embed(self, texts):
                if failure == "count":
                    return []
                raise RuntimeError("provider secret must not be stored")
        monkeypatch.setattr("app.services.resource_ingestion.get_embedding_provider", lambda: BrokenEmbeddings())
    def reject_insert(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO RESOURCE_CHUNKS"):
            raise RuntimeError("Injected chunk-write failure")
    if failure == "database":
        event.listen(engine, "before_cursor_execute", reject_insert)
    try:
        response = client.put(f"/api/v1/resources/{resource_id}/text", headers=headers,
                              json={"title": "Replacement", "text": "Different material about anatomy and physiology."})
    finally:
        if failure == "database":
            event.remove(engine, "before_cursor_execute", reject_insert)
    assert response.status_code == 200
    assert response.json()["processing_status"] == "READY"
    assert "previous material remains available" in response.json()["error_detail"]
    with session_factory() as db:
        resource = db.get(Resource, resource_id)
        assert resource.title == "Original"
        assert resource.source_text == original_text
        assert {chunk.id for chunk in db.scalars(select(ResourceChunk).where(
            ResourceChunk.resource_id == resource_id
        ))} == ids
        assert db.scalar(select(func.count()).select_from(ConceptChunk).where(
            ConceptChunk.chunk_id.in_(ids)
        )) == 1


def test_outdated_resource_replacement_cannot_overwrite_newer_change(client, session_factory, monkeypatch):
    from datetime import UTC, datetime

    from app.ai.providers import DeterministicEmbeddingProvider
    from app.db.models import Resource

    _, headers = learner(client, "replace-race@example.com")
    context = subject(client, headers, "Biology")
    created = client.post("/api/v1/resources/text", headers=headers, json={
        "context_id": str(context), "title": "Original", "text": "Photosynthesis transforms light into chemical energy.",
    }).json()
    resource_id = UUID(created["id"])
    class ConcurrentEmbedding:
        async def embed(self, texts):
            with session_factory() as competing:
                row = competing.get(Resource, resource_id)
                row.title = "Newer change"
                row.updated_at = datetime.now(UTC)
                competing.commit()
            return await DeterministicEmbeddingProvider().embed(texts)
    monkeypatch.setattr("app.services.resource_ingestion.get_embedding_provider", lambda: ConcurrentEmbedding())
    response = client.put(f"/api/v1/resources/{resource_id}/text", headers=headers,
                          json={"title": "Stale replacement", "text": "A replacement arriving late from another request."})
    assert response.status_code == 422
    with session_factory() as db:
        assert db.get(Resource, resource_id).title == "Newer change"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["before_commit", "after_commit", "audit_write"])
async def test_workflow_recovers_without_repeating_committed_domain_work(
    client, session_factory, failure
):
    from sqlalchemy import event

    from app.db.models import AgentTask, AuditLog, Learner, Workflow
    from app.services.orchestration import _run_step

    owner, headers = learner(client, "workflow-retry@example.com")
    context = subject(client, headers, "Workflow recovery")
    calls = 0
    audit_failures = 0
    def handler(db, **kwargs):
        nonlocal calls
        calls += 1
        if failure == "before_commit" and calls == 1:
            db.add(Learner(owner_id=owner, email="workflow-retry@example.com"))
            db.flush()  # real IntegrityError leaves the Session needing rollback
        note = Note(owner_id=owner, context_id=context, title="Single result", body="Test result")
        db.add(note)
        db.commit()
        if failure == "after_commit":
            raise RuntimeError("gsk_provider_secret must never appear in audit")
        return {"note_id": str(note.id)}
    def fail_audit(mapper, connection, target):
        nonlocal audit_failures
        if failure == "audit_write" and target.action == "succeeded" and not audit_failures:
            audit_failures += 1
            raise RuntimeError("Injected audit write failure")
    event.listen(AuditLog, "before_insert", fail_audit)
    try:
        with session_factory() as db:
            workflow = Workflow(owner_id=owner, name="generate_notes", status="RUNNING", payload={})
            db.add(workflow)
            db.flush()
            task = AgentTask(owner_id=owner, workflow_id=workflow.id, agent="notes")
            db.add(task)
            db.commit()
            succeeded = await _run_step(db, owner_id=owner, workflow=workflow, task=task,
                                        agent={"handler": handler}, context_id=context, payload={})
            assert succeeded is (failure != "after_commit")
            assert calls == (2 if failure == "before_commit" else 1)
            assert db.scalar(select(func.count()).select_from(Note).where(Note.owner_id == owner)) == 1
            assert "gsk_provider_secret" not in (task.error_detail or "")
            if failure == "after_commit":
                assert "Review the result" in task.error_detail
            audit = list(db.scalars(select(AuditLog).where(AuditLog.owner_id == owner)))
            assert all("gsk_provider_secret" not in str(row.detail) for row in audit)
    finally:
        event.remove(AuditLog, "before_insert", fail_audit)


def test_invalid_workflow_uuid_is_rejected_before_any_workflow_is_written(client, session_factory):
    from app.db.models import Workflow
    owner, headers = learner(client, "workflow-input@example.com")
    response = client.post("/api/v1/orchestration/workflows/generate_notes", headers=headers,
                           json={"payload": {"context_id": "not-a-uuid"}})
    assert response.status_code == 422
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Workflow).where(Workflow.owner_id == owner)) == 0



def test_provider_secrets_and_exception_bodies_do_not_reach_log_records(caplog, monkeypatch):
    import logging
    from types import SimpleNamespace

    import app.core.logging as log_config

    monkeypatch.setattr(log_config, "get_settings", lambda: SimpleNamespace(
        aria_log_level="INFO", groq_api_key="configured-secret-for-test",
    ))
    log_config.configure_logging()
    logger = logging.getLogger("review.provider")
    with caplog.at_level(logging.WARNING):
        logger.warning("key=%s bearer personal_token https://user:password@private.example/?api_key=secret",
                       "configured-secret-for-test")
        try:
            raise RuntimeError("Private prompt and gsk_learner_secret_key")
        except RuntimeError as exc:
            logger.exception("Provider call failed")
            logger.warning("Provider failed: %s", exc)
            logger.warning("Provider failed: %(error)s", {"error": exc})
            logger.warning(exc)
    output = caplog.text
    for secret in ("configured-secret-for-test", "personal_token", "user:password", "api_key=secret",
                   "gsk_learner_secret_key", "Private prompt"):
        assert secret not in output
    assert "error_type=RuntimeError" in output
    assert all(record.exc_info is None for record in caplog.records if record.name == "review.provider")

def test_secret_redaction_preserves_uvicorn_access_formatter(monkeypatch):
    import logging
    from types import SimpleNamespace

    from uvicorn.logging import AccessFormatter

    from app.core.logging import configure_logging

    monkeypatch.setattr("app.core.logging.get_settings", lambda: SimpleNamespace(aria_log_level="INFO"))
    configure_logging()
    record = logging.getLogger("uvicorn.access").makeRecord(
        "uvicorn.access", logging.INFO, "test", 1, '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:1234", "GET", "/callback?token=private-value", "1.1", 200), None,
    )
    output = AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s', use_colors=False).format(record)
    assert "private-value" not in output
    assert "[REDACTED]" in output
    assert "GET /callback" in output
    assert "200" in output
