from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event

from app.core.errors import ValidationError
from app.db.models import (
    Assessment,
    AssessmentAttempt,
    Concept,
    ConversationMessage,
    Deadline,
    Evaluation,
    Evidence,
    Learner,
    LearnerConceptState,
    LearnerPreference,
    LearningContext,
    PlannedTask,
    Roadmap,
    RoadmapMilestone,
    StudySession,
)
from app.services.brain.snapshot import MAX_CONCEPTS, MAX_EVIDENCE, MAX_TASKS, build_snapshot


def learner_context(db):
    owner = uuid4()
    learner = Learner(id=owner, owner_id=owner, email=f"{uuid4()}@example.com")
    db.add(learner)
    db.flush()
    context = LearningContext(owner_id=learner.id, title="Subject")
    db.add(context)
    db.flush()
    return learner.id, context.id


def test_empty_snapshot_is_scoped_and_read_only(session_factory):
    with session_factory() as db:
        owner, cid = learner_context(db)
        other, other_cid = learner_context(db)
        db.commit()

        def no_write(*args):
            raise AssertionError("Snapshot attempted a write")

        event.listen(db, "before_commit", no_write)
        event.listen(db, "before_flush", no_write)
        # Pending writes must not be flushed merely by reading the snapshot.
        db.add(LearnerPreference(owner_id=owner, key="pending", value="not flushed"))
        snapshot = build_snapshot(db, owner_id=owner, context_id=cid)
        assert snapshot.concepts == snapshot.evidence == snapshot.roadmaps == ()
        assert snapshot.memory.model_dump() == dict.fromkeys(type(snapshot.memory).model_fields, 0)
        assert snapshot.assessment_preferences.question_count is None
        with pytest.raises(ValidationError):
            build_snapshot(db, owner_id=owner, context_id=other_cid)
        event.remove(db, "before_commit", no_write)
        event.remove(db, "before_flush", no_write)


def seed_subject(db, owner, cid, n):
    assessment = Assessment(owner_id=owner, context_id=cid)
    db.add(assessment)
    db.flush()
    attempt = AssessmentAttempt(owner_id=owner, assessment_id=assessment.id, idempotency_key=str(uuid4()))
    db.add(attempt)
    db.flush()
    evaluation = Evaluation(owner_id=owner, attempt_id=attempt.id)
    db.add(evaluation)
    db.flush()
    roadmap = Roadmap(owner_id=owner, context_id=cid, goal="Learn this")
    db.add(roadmap)
    db.flush()
    for i in range(n):
        concept = Concept(owner_id=owner, context_id=cid, name=f"Concept {i}")
        db.add(concept)
        db.flush()
        db.add(
            LearnerConceptState(
                owner_id=owner, concept_id=concept.id, state="NEEDS_REVIEW", confidence=20, reason="private reason"
            )
        )
        db.add(
            Evidence(
                owner_id=owner,
                concept_id=concept.id,
                evaluation_id=evaluation.id,
                signal="INCORRECT",
                provenance={"private": "not included"},
            )
        )
        db.add(
            PlannedTask(
                owner_id=owner, context_id=cid, title="Private task", due_at=datetime.now(UTC) - timedelta(days=1)
            )
        )
        db.add(
            Deadline(
                owner_id=owner, context_id=cid, title="Private deadline", due_at=datetime.now(UTC) + timedelta(days=1)
            )
        )
    db.add(
        RoadmapMilestone(owner_id=owner, roadmap_id=roadmap.id, phase_name="Intro", title="Topic", state="SUPPORTED")
    )
    session = StudySession(owner_id=owner, context_id=cid)
    db.add(session)
    db.flush()
    db.add(
        ConversationMessage(
            owner_id=owner, study_session_id=session.id, role="user", content="private chat", position=1
        )
    )
    return roadmap.id


def test_snapshot_bounds_totals_subject_isolation_and_no_private_text(session_factory):
    with session_factory() as db:
        owner, cid = learner_context(db)
        second = LearningContext(owner_id=owner, title="Other subject")
        db.add(second)
        db.flush()
        other, other_cid = learner_context(db)
        roadmap_id = seed_subject(db, owner, cid, 55)
        seed_subject(db, owner, second.id, 2)
        seed_subject(db, other, other_cid, 3)
        db.add_all(
            [
                LearnerPreference(owner_id=owner, key="assessment.question_count", value="10"),
                LearnerPreference(owner_id=owner, key="assessment.timed", value="true"),
                LearnerPreference(owner_id=owner, key="assessment.format", value="invalid-format"),
                LearnerPreference(owner_id=other, key="assessment.time_limit_seconds", value="600"),
                LearnerPreference(owner_id=owner, key="arbitrary", value="private memory"),
            ]
        )
        db.commit()
        snapshot = build_snapshot(db, owner_id=owner, context_id=cid)
        assert len(snapshot.concepts) == MAX_CONCEPTS
        assert len(snapshot.evidence) == MAX_EVIDENCE
        assert len(snapshot.missed_tasks) == len(snapshot.upcoming_deadlines) == MAX_TASKS
        assert snapshot.memory.concepts == snapshot.memory.weak_concepts == snapshot.memory.evidence_count == 55
        assert snapshot.memory.message_count == 1
        assert [(r.id, r.total, r.supported) for r in snapshot.roadmaps] == [(roadmap_id, 1, 1)]
        assert snapshot.assessment_preferences.question_count == 10
        assert snapshot.assessment_preferences.timed is True
        assert snapshot.assessment_preferences.format is None
        assert snapshot.assessment_preferences.time_limit_seconds is None
        assert "private" not in snapshot.model_dump_json()
        assert not db.dirty and not db.new
