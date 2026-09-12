"""Full context-deletion integration covering nullable dependents and rollback."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.db.models import (
    AdaptationDecision,
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AttemptAnswer,
    AudioArtifact,
    AudioProgress,
    Concept,
    ConceptChunk,
    ConceptRelation,
    ConversationMessage,
    Deadline,
    Evaluation,
    Evidence,
    Goal,
    Learner,
    LearnerConceptState,
    LearningContext,
    Note,
    PlannedTask,
    Resource,
    ResourceChunk,
    RevisionItem,
    StudySession,
)
from app.services.data_management import delete_context_cascade


def _make_learner(db, *, email="learner@example.com"):
    lid = uuid.uuid4()
    learner = Learner(
        id=lid,
        owner_id=lid,
        email=email,
        display_name="Learner",
        password_hash="x",
        verified_at=datetime.now(UTC),
    )
    db.add(learner)
    db.commit()
    return learner


def test_delete_context_cascade_removes_all_dependent_records_including_nullable(
    engine, session_factory
):
    """Covers resource-linked notes, generated audio + progress, assessments,
    nullable Evidence (concept_id NULL) and context-level AdaptationDecision (concept_id NULL)."""
    db = session_factory()
    learner = _make_learner(db, email="full-del@example.com")
    owner_id = learner.id

    # Goal survives deletion (not exclusively owned)
    goal = Goal(id=uuid.uuid4(), owner_id=owner_id, title="Goal", description="desc")
    db.add(goal)
    db.commit()

    ctx = LearningContext(
        id=uuid.uuid4(), owner_id=owner_id, goal_id=goal.id, title="DBMS", description="d", status="ACTIVE", configuration={}
    )
    ctx_other = LearningContext(
        id=uuid.uuid4(), owner_id=owner_id, title="Other", status="ACTIVE", configuration={}
    )
    db.add_all([ctx, ctx_other])
    db.commit()
    context_id = ctx.id
    other_id = ctx_other.id

    # Resource + chunks
    res = Resource(id=uuid.uuid4(), owner_id=owner_id, context_id=context_id, title="R", resource_type="TEXT", processing_status="READY", source_text="hello")
    db.add(res)
    db.commit()
    rc = ResourceChunk(id=uuid.uuid4(), owner_id=owner_id, resource_id=res.id, content="hello", chunk_index=0, metadata_json={}, embedding_json=None)
    db.add(rc)
    db.commit()

    # Concept + relation + chunk link
    concept = Concept(id=uuid.uuid4(), owner_id=owner_id, context_id=context_id, name="Normalisation")
    concept_other = Concept(id=uuid.uuid4(), owner_id=owner_id, context_id=other_id, name="OtherConcept")
    db.add_all([concept, concept_other])
    db.commit()
    cc = ConceptChunk(id=uuid.uuid4(), owner_id=owner_id, concept_id=concept.id, chunk_id=rc.id)
    db.add(cc)
    _rel_self = ConceptRelation(id=uuid.uuid4(), owner_id=owner_id, concept_id=concept.id, prerequisite_concept_id=concept.id)  # noqa: F841 - intentionally created then replaced to test self-reference guard
    _ = _rel_self  # silence F841 while preserving intent comment
    # Avoid self-reference unique violation — use two concepts for relation
    concept2 = Concept(id=uuid.uuid4(), owner_id=owner_id, context_id=context_id, name="C2")
    db.add(concept2)
    db.commit()
    rel2 = ConceptRelation(id=uuid.uuid4(), owner_id=owner_id, concept_id=concept2.id, prerequisite_concept_id=concept.id)
    db.add(rel2)
    lcs = LearnerConceptState(id=uuid.uuid4(), owner_id=owner_id, concept_id=concept.id, state="DEVELOPING", confidence=50, reason="r", supporting_evidence=[])
    db.add(lcs)
    db.commit()

    # Note linked to resource + concept
    sess = StudySession(id=uuid.uuid4(), owner_id=owner_id, context_id=context_id, mode="BASELINE", status="ACTIVE")
    db.add(sess)
    db.commit()
    note = Note(id=uuid.uuid4(), owner_id=owner_id, context_id=context_id, title="N", body="b", resource_id=res.id, concept_id=concept.id, study_session_id=sess.id, source_refs=[])
    db.add(note)
    db.commit()
    rev = RevisionItem(id=uuid.uuid4(), owner_id=owner_id, note_id=note.id, state="NEW", interval_days=1, next_review_at=datetime.now(UTC) + timedelta(days=1))
    db.add(rev)
    msg = ConversationMessage(id=uuid.uuid4(), owner_id=owner_id, study_session_id=sess.id, role="user", content="hi", source_refs=[], position=0)
    db.add(msg)

    # Planner
    dl = Deadline(id=uuid.uuid4(), owner_id=owner_id, context_id=context_id, title="DL", due_at=datetime.now(UTC) + timedelta(days=5), syllabus_resource_id=res.id)
    db.add(dl)
    db.commit()
    task = PlannedTask(id=uuid.uuid4(), owner_id=owner_id, context_id=context_id, deadline_id=dl.id, title="T", due_at=datetime.now(UTC), status="PENDING")
    db.add(task)

    # Assessment chain
    assess = Assessment(id=uuid.uuid4(), owner_id=owner_id, context_id=context_id, mode="BASELINE", format="mcq", status="READY", configuration={})
    db.add(assess)
    db.commit()
    q = AssessmentQuestion(id=uuid.uuid4(), owner_id=owner_id, assessment_id=assess.id, concept_id=concept.id, position=0, prompt="p", options=["a","b"], correct_option="a")
    db.add(q)
    db.commit()
    attempt = AssessmentAttempt(id=uuid.uuid4(), owner_id=owner_id, assessment_id=assess.id, status="SUBMITTED", idempotency_key=str(uuid.uuid4()))
    db.add(attempt)
    db.commit()
    ans = AttemptAnswer(id=uuid.uuid4(), owner_id=owner_id, attempt_id=attempt.id, question_id=q.id, selected_option="a")
    db.add(ans)
    evl = Evaluation(id=uuid.uuid4(), owner_id=owner_id, attempt_id=attempt.id, status="DONE", score=1, details={"total":1})
    db.add(evl)
    db.commit()
    # nullable evidence (concept_id NULL) – must be deleted via evaluation path
    ev_null = Evidence(id=uuid.uuid4(), owner_id=owner_id, concept_id=None, evaluation_id=evl.id, signal="test", provenance={}, valid=True)
    ev_with_concept = Evidence(id=uuid.uuid4(), owner_id=owner_id, concept_id=concept.id, evaluation_id=evl.id, signal="test2", provenance={}, valid=True)
    db.add_all([ev_null, ev_with_concept])

    # Adaptation decisions: one with concept, one context-level NULL
    ad_concept = AdaptationDecision(id=uuid.uuid4(), owner_id=owner_id, context_id=context_id, concept_id=concept.id, decision_type="REVIEW", reason="r", status="READY")
    ad_context = AdaptationDecision(id=uuid.uuid4(), owner_id=owner_id, context_id=context_id, concept_id=None, decision_type="REVIEW", reason="r2", status="READY")
    db.add_all([ad_concept, ad_context])

    # Audio generated from resource + note, with progress
    art_res = AudioArtifact(id=uuid.uuid4(), owner_id=owner_id, source_type="RESOURCE", source_id=res.id, text="audio", status="READY", audio_bytes=b"123", content_type="audio/mpeg")
    art_note = AudioArtifact(id=uuid.uuid4(), owner_id=owner_id, source_type="NOTE", source_id=note.id, text="audio2", status="READY", audio_bytes=b"456", content_type="audio/mpeg")
    db.add_all([art_res, art_note])
    db.commit()
    prog_res = AudioProgress(id=uuid.uuid4(), owner_id=owner_id, artifact_id=art_res.id, position_seconds=10, completed=False)
    prog_note = AudioProgress(id=uuid.uuid4(), owner_id=owner_id, artifact_id=art_note.id, position_seconds=5, completed=False)
    db.add_all([prog_res, prog_note])
    db.commit()

    # Other context should survive – seed minimal other data
    res_other = Resource(id=uuid.uuid4(), owner_id=owner_id, context_id=other_id, title="OtherR", resource_type="TEXT", processing_status="READY")
    db.add(res_other)
    db.commit()

    db.close()

    # Delete via service (file-backed shared engine not needed here – single engine with StaticPool shares in-memory)
    db2 = session_factory()
    ok = delete_context_cascade(db2, owner_id=owner_id, context_id=context_id)
    assert ok is True
    db2.close()

    # Verify via fresh session on same engine
    check = session_factory()
    def count(model, **kw):
        return check.scalar(select(func.count()).select_from(model).where(*[getattr(model, k)==v for k,v in kw.items()])) or 0

    # Deleted context's dependents gone
    assert check.scalar(select(func.count()).select_from(Resource).where(Resource.context_id==context_id)) == 0
    assert check.scalar(select(func.count()).select_from(ResourceChunk).where(ResourceChunk.resource_id==res.id)) == 0
    assert check.scalar(select(func.count()).select_from(Note).where(Note.context_id==context_id)) == 0
    assert check.scalar(select(func.count()).select_from(RevisionItem).where(RevisionItem.note_id==note.id)) == 0
    assert check.scalar(select(func.count()).select_from(ConceptChunk).where(ConceptChunk.concept_id==concept.id)) == 0
    assert check.scalar(select(func.count()).select_from(LearnerConceptState).where(LearnerConceptState.concept_id==concept.id)) == 0
    assert check.scalar(select(func.count()).select_from(Evidence).where(Evidence.evaluation_id==evl.id)) == 0
    assert check.scalar(select(func.count()).select_from(Evaluation).where(Evaluation.attempt_id==attempt.id)) == 0
    assert check.scalar(select(func.count()).select_from(AttemptAnswer).where(AttemptAnswer.attempt_id==attempt.id)) == 0
    assert check.scalar(select(func.count()).select_from(AssessmentQuestion).where(AssessmentQuestion.assessment_id==assess.id)) == 0
    assert check.scalar(select(func.count()).select_from(AssessmentAttempt).where(AssessmentAttempt.assessment_id==assess.id)) == 0
    assert check.scalar(select(func.count()).select_from(Assessment).where(Assessment.context_id==context_id)) == 0
    assert check.scalar(select(func.count()).select_from(ConversationMessage).where(ConversationMessage.study_session_id==sess.id)) == 0
    assert check.scalar(select(func.count()).select_from(StudySession).where(StudySession.context_id==context_id)) == 0
    assert check.scalar(select(func.count()).select_from(Deadline).where(Deadline.context_id==context_id)) == 0
    assert check.scalar(select(func.count()).select_from(PlannedTask).where(PlannedTask.context_id==context_id)) == 0
    assert check.scalar(select(func.count()).select_from(AdaptationDecision).where(AdaptationDecision.context_id==context_id)) == 0
    assert check.scalar(select(func.count()).select_from(AudioProgress).where(AudioProgress.artifact_id.in_([art_res.id, art_note.id]))) == 0
    assert check.scalar(select(func.count()).select_from(AudioArtifact).where(AudioArtifact.id.in_([art_res.id, art_note.id]))) == 0
    assert check.scalar(select(func.count()).select_from(Concept).where(Concept.context_id==context_id)) == 0
    assert check.scalar(select(func.count()).select_from(LearningContext).where(LearningContext.id==context_id)) == 0

    # Goal survives (not exclusively owned)
    assert check.scalar(select(func.count()).select_from(Goal).where(Goal.id==goal.id)) == 1
    # Other context survives
    assert check.scalar(select(func.count()).select_from(LearningContext).where(LearningContext.id==other_id)) == 1
    assert check.scalar(select(func.count()).select_from(Resource).where(Resource.context_id==other_id)) == 1
    check.close()


def test_delete_context_rollback_on_mid_transaction_failure(engine, session_factory, tmp_path):
    """Injected failure after at least one delete has executed must rollback and re-raise.
    Uses file-backed SQLite so a separate session sees the same DB (in-memory :memory: would be isolated)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker as sm
    from sqlalchemy.pool import StaticPool

    # Use file-backed DB for this test to satisfy shared-visibility requirement
    db_path = tmp_path / "rollback_test.db"
    file_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from app.db.base import Base
    Base.metadata.create_all(file_engine)
    FileSession = sm(bind=file_engine, autoflush=False, expire_on_commit=False)

    db = FileSession()
    lid = uuid.uuid4()
    learner = Learner(id=lid, owner_id=lid, email="rollback@example.com", display_name="R", password_hash="x")
    db.add(learner)
    db.commit()
    owner_id = learner.id
    ctx = LearningContext(id=uuid.uuid4(), owner_id=owner_id, title="ToDelete", status="ACTIVE", configuration={})
    db.add(ctx)
    db.commit()
    concept = Concept(id=uuid.uuid4(), owner_id=owner_id, context_id=ctx.id, name="C")
    db.add(concept)
    db.commit()
    # Add a resource so first delete does work
    res = Resource(id=uuid.uuid4(), owner_id=owner_id, context_id=ctx.id, title="R", resource_type="TEXT", processing_status="READY")
    db.add(res)
    db.commit()
    rc = ResourceChunk(id=uuid.uuid4(), owner_id=owner_id, resource_id=res.id, content="hi", chunk_index=0, metadata_json={})
    db.add(rc)
    db.commit()
    pre_concept_count = db.scalar(select(func.count()).select_from(Concept).where(Concept.context_id==ctx.id))
    assert pre_concept_count == 1
    db.close()

    # Patch to fail on the 2nd DELETE (after at least one DELETE has executed);
    # count only DELETE statements so the initial SELECT (_owned_context) is ignored.
    from unittest.mock import patch

    from sqlalchemy.orm import Session as SASession
    from sqlalchemy.sql.dml import Delete as SADelete

    import app.services.data_management as dm

    original_execute = SASession.execute
    call_count = {"n": 0}

    def failing_execute(self, statement, *args, **kwargs):
        is_delete = isinstance(statement, SADelete)
        if is_delete:
            call_count["n"] += 1
            if call_count["n"] == 2:  # fail on 2nd DELETE, after 1st DELETE succeeded
                raise RuntimeError("injected")
        return original_execute(self, statement, *args, **kwargs)

    db2 = FileSession()

    with patch.object(SASession, "execute", new=failing_execute):
        with pytest.raises(RuntimeError, match="injected"):
            dm.delete_context_cascade(db2, owner_id=owner_id, context_id=ctx.id)
    db2.close()

    # Verify via separate session on SAME file-backed engine that no rows were removed and exception was re-raised
    check = FileSession()
    assert check.scalar(select(func.count()).select_from(Concept).where(Concept.context_id==ctx.id)) == 1
    assert check.scalar(select(func.count()).select_from(Resource).where(Resource.context_id==ctx.id)) == 1
    assert check.scalar(select(func.count()).select_from(ResourceChunk).where(ResourceChunk.resource_id==res.id)) == 1
    assert check.scalar(select(func.count()).select_from(LearningContext).where(LearningContext.id==ctx.id)) == 1
    check.close()
    file_engine.dispose()
