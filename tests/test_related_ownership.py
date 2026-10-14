import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.errors import ValidationError
from app.db.models import (
    Assessment,
    Concept,
    ConceptRelation,
    Deadline,
    LearningContext,
    Note,
    PlannedTask,
    Resource,
    StudySession,
)
from app.services.assessment import create_assessment
from app.services.memory import add_prerequisite
from app.services.notes import create_note
from app.services.planner import create_deadline, create_task


@pytest.mark.parametrize("foreign_owner", [True, False])
@pytest.mark.parametrize("action", ["concept_note", "session_note", "task", "deadline", "assessment", "prerequisite"])
def test_related_references_reject_foreign_owner_and_other_subject(
    engine, session_factory, monkeypatch, action, foreign_owner,
):
    owner, context, other_context = uuid4(), uuid4(), uuid4()
    other_owner = uuid4() if foreign_owner else owner
    with session_factory() as db:
        db.add_all([LearningContext(id=context, owner_id=owner, title="Own"),
                    LearningContext(id=other_context, owner_id=other_owner, title="Other")])
        db.flush()
        base = Concept(owner_id=owner, context_id=context, name="Base")
        concept = Concept(owner_id=other_owner, context_id=other_context, name="Other")
        session = StudySession(owner_id=other_owner, context_id=other_context)
        resource = Resource(owner_id=other_owner, context_id=other_context, title="Other", resource_type="TEXT")
        deadline = Deadline(owner_id=other_owner, context_id=other_context, title="Other", due_at=datetime.now(UTC))
        db.add_all([base, concept, session, resource, deadline])
        db.commit()

        async def unexpected_sync(*args, **kwargs):
            raise AssertionError("Invalid references must be rejected before synchronization/provider work")

        monkeypatch.setattr("app.services.assessment.sync_concepts", unexpected_sync)
        with pytest.raises(ValidationError):
            if action.endswith("note"):
                create_note(db, owner_id=owner, context_id=context, title="New", body="Body",
                            **({"concept_id": concept.id} if action == "concept_note" else {"study_session_id": session.id}))
            elif action == "task":
                create_task(db, owner_id=owner, context_id=context, title="New", deadline_id=deadline.id, due_at=None)
            elif action == "deadline":
                create_deadline(db, owner_id=owner, context_id=context, title="New", due_at=datetime.now(UTC),
                                syllabus_resource_id=resource.id, reminder_days_before=1)
            elif action == "assessment":
                asyncio.run(create_assessment(db, owner_id=owner, context_id=context, format_name="mcq",
                                              question_count=1, difficulty="medium", mode="BASELINE",
                                              concept_ids=[concept.id]))
            else:
                add_prerequisite(db, owner_id=owner, concept_id=base.id, prerequisite_concept_id=concept.id)
        for model in (Note, PlannedTask, Assessment, ConceptRelation):
            assert db.scalar(select(func.count(model.id))) == 0
        assert db.scalar(select(func.count(Deadline.id))) == 1
        # Rejected links must not obstruct deleting the referenced subject.
        from app.services.data_management import delete_context_cascade
        assert delete_context_cascade(db, owner_id=other_owner, context_id=other_context)


@pytest.mark.parametrize("action", ["note", "task", "deadline", "assessment", "text", "pdf", "image", "concepts", "states", "adaptation"])
def test_service_entry_points_reject_foreign_destination_before_any_write(engine, session_factory, action):
    from app.services.adaptation import generate_adaptation_decisions
    from app.services.concepts import sync_concepts
    from app.services.learner_state import recompute_learner_states
    from app.services.resource_ingestion import create_image_resource, create_pdf_resource, create_text_resource

    with session_factory() as db:
        owner, foreign = uuid4(), uuid4()
        db.add(LearningContext(id=foreign, owner_id=uuid4(), title="Foreign"))
        db.commit()
        with pytest.raises(ValidationError, match="Learning context not found"):
            if action == "note":
                create_note(db, owner_id=owner, context_id=foreign, title="New", body="Body")
            elif action == "task":
                create_task(db, owner_id=owner, context_id=foreign, title="New", deadline_id=None, due_at=None)
            elif action == "deadline":
                create_deadline(db, owner_id=owner, context_id=foreign, title="New", due_at=datetime.now(UTC),
                                syllabus_resource_id=None, reminder_days_before=1)
            elif action == "assessment":
                asyncio.run(create_assessment(db, owner_id=owner, context_id=foreign, format_name="mcq",
                                              question_count=1, difficulty="medium", mode="BASELINE", concept_ids=[]))
            elif action in {"states", "adaptation"}:
                fn = recompute_learner_states if action == "states" else generate_adaptation_decisions
                fn(db, owner_id=owner, context_id=foreign)
            elif action == "concepts":
                asyncio.run(sync_concepts(db, owner_id=owner, context_id=foreign))
            else:
                fn = {"text": create_text_resource, "pdf": create_pdf_resource, "image": create_image_resource}[action]
                content = {"text": "Source"} if action == "text" else {"content": b"invalid"}
                asyncio.run(fn(db, owner_id=owner, context_id=foreign, title="New", **content))
        for model in (Note, PlannedTask, Deadline, Assessment, Resource, Concept):
            assert db.scalar(select(func.count(model.id))) == 0


@pytest.mark.parametrize("mismatch", ["foreign_concept", "other_subject", "question", "evaluation_owner", "attempt"])
def test_evidence_rejects_inconsistent_parent_and_concept_references(engine, session_factory, mismatch):
    from app.db.models import AssessmentAttempt, AssessmentQuestion, Evaluation, Evidence
    from app.services.evidence import record_assessment_evidence

    with session_factory() as db:
        owner, context, other = uuid4(), uuid4(), uuid4()
        db.add_all([LearningContext(id=context, owner_id=owner, title="Own"),
                    LearningContext(id=other, owner_id=owner, title="Other")])
        db.flush()
        concept = Concept(owner_id=owner, context_id=context, name="Own")
        foreign = Concept(owner_id=uuid4() if mismatch == "foreign_concept" else owner,
                          context_id=other, name="Other")
        db.add_all([concept, foreign])
        assessment = Assessment(owner_id=owner, context_id=context)
        another = Assessment(owner_id=owner, context_id=context)
        db.add_all([assessment, another])
        db.flush()
        attempt = AssessmentAttempt(owner_id=owner, assessment_id=assessment.id, idempotency_key="first")
        another_attempt = AssessmentAttempt(owner_id=owner, assessment_id=another.id, idempotency_key="second")
        db.add_all([attempt, another_attempt])
        db.flush()
        question = AssessmentQuestion(owner_id=owner, assessment_id=another.id if mismatch == "question" else assessment.id,
                                      concept_id=concept.id, position=1, prompt="Q", options=["A", "B"], correct_option="A")
        evaluation = Evaluation(owner_id=uuid4() if mismatch == "evaluation_owner" else owner,
                                attempt_id=another_attempt.id if mismatch == "attempt" else attempt.id)
        db.add_all([question, evaluation])
        db.commit()
        selected = foreign.id if mismatch in {"foreign_concept", "other_subject"} else concept.id
        with pytest.raises(ValidationError):
            record_assessment_evidence(db, owner_id=owner, attempt_id=attempt.id, evaluation_id=evaluation.id,
                                       details=[{"concept_id": str(selected), "question_id": str(question.id),
                                                 "correct": True, "correct_option": "A"}])
        assert db.scalar(select(func.count(Evidence.id))) == 0


@pytest.mark.parametrize("submit", [False, True])
@pytest.mark.parametrize("invalid", ["not-a-uuid", "other_assessment"])
def test_invalid_answer_references_do_not_clear_previous_answers(engine, session_factory, submit, invalid):
    from app.db.models import AssessmentAttempt, AssessmentQuestion, AttemptAnswer, Evaluation
    from app.services.assessment import save_answers, submit_attempt

    with session_factory() as db:
        owner, context = uuid4(), uuid4()
        db.add(LearningContext(id=context, owner_id=owner, title="Own"))
        db.flush()
        first = Assessment(owner_id=owner, context_id=context)
        second = Assessment(owner_id=owner, context_id=context)
        db.add_all([first, second])
        db.flush()
        question = AssessmentQuestion(owner_id=owner, assessment_id=first.id, position=1,
                                      prompt="Q", options=["A", "B"], correct_option="A")
        other = AssessmentQuestion(owner_id=owner, assessment_id=second.id, position=1,
                                   prompt="Q", options=["A", "B"], correct_option="A")
        attempt = AssessmentAttempt(owner_id=owner, assessment_id=first.id, idempotency_key="initial")
        db.add_all([question, other, attempt])
        db.flush()
        answer = AttemptAnswer(owner_id=owner, attempt_id=attempt.id, question_id=question.id, selected_option="A")
        db.add(answer)
        db.commit()
        key = str(other.id) if invalid == "other_assessment" else invalid
        with pytest.raises(ValidationError):
            if submit:
                submit_attempt(db, owner_id=owner, attempt_id=attempt.id, idempotency_key="submission", answers={key: "B"})
            else:
                save_answers(db, owner_id=owner, attempt_id=attempt.id, answers={key: "B"})
        db.expire_all()
        assert db.get(AttemptAnswer, answer.id).selected_option == "A"
        assert db.get(AssessmentAttempt, attempt.id).status == "IN_PROGRESS"
        assert db.scalar(select(func.count(Evaluation.id))) == 0
