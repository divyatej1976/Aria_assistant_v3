"""Learner data controls: full export and context deletion (explicit cascades)."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

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
    LearnerBadge,
    LearnerConceptState,
    LearnerLLMKey,
    LearnerPreference,
    LearningActivity,
    LearningContext,
    Note,
    Notification,
    PlannedTask,
    PushSubscription,
    Resource,
    ResourceChunk,
    RevisionItem,
    StudySession,
)


def _owned_context(db: Session, *, owner_id: UUID, context_id: UUID) -> LearningContext | None:
    return db.scalar(
        select(LearningContext).where(
            LearningContext.id == context_id, LearningContext.owner_id == owner_id
        )
    )


def _rows(db: Session, model, *, owner_id: UUID) -> list:
    return list(db.scalars(select(model).where(model.owner_id == owner_id)).all())


# Binary/vector columns excluded from the portable JSON export: their repr
# dumps are enormous and unusable outside the app.
_EXPORT_EXCLUDED_COLUMNS = {"audio_bytes", "raw_bytes", "embedding", "embedding_json"}


def _serialize(row) -> dict:
    out = {}
    for column in row.__table__.columns:
        if column.name in _EXPORT_EXCLUDED_COLUMNS:
            out[column.name] = None
            continue
        value = getattr(row, column.name)
        out[column.name] = value.isoformat() if hasattr(value, "isoformat") else value
    return out


def export_learner_data(db: Session, *, owner_id: UUID) -> dict:
    """Assemble every learner-owned artifact into a portable JSON dict."""
    learner = db.get(Learner, owner_id)
    data: dict = {
        "profile": {
            "email": learner.email if learner else None,
            "display_name": learner.display_name if learner else None,
            "verified": learner.verified_at is not None if learner else False,
        },
        "preferences": [_serialize(p) for p in _rows(db, LearnerPreference, owner_id=owner_id)],
        "contexts": [],
    }

    contexts = _rows(db, LearningContext, owner_id=owner_id)
    notes_out: list[dict] = []
    tasks_out: list[dict] = []
    deadlines_out: list[dict] = []
    sessions_out: list[dict] = []
    concepts_out: list[dict] = []
    resources_out: list[dict] = []
    assessments_out: list[dict] = []

    for ctx in contexts:
        cid = ctx.id
        data["contexts"].append(
            {
                "id": str(cid),
                "title": ctx.title,
                "description": ctx.description,
                "status": ctx.status,
                "configuration": ctx.configuration,
                "goal_id": str(ctx.goal_id) if ctx.goal_id else None,
            }
        )

        for note in db.scalars(
            select(Note).where(Note.owner_id == owner_id, Note.context_id == cid)
        ).all():
            rev = db.scalar(
                select(RevisionItem).where(
                    RevisionItem.owner_id == owner_id, RevisionItem.note_id == note.id
                )
            )
            notes_out.append(
                {
                    "title": note.title,
                    "body": note.body,
                    "review_state": rev.state if rev else None,
                    "next_review_at": rev.next_review_at.isoformat()
                    if rev and rev.next_review_at
                    else None,
                }
            )

        for task in db.scalars(
            select(PlannedTask).where(PlannedTask.owner_id == owner_id, PlannedTask.context_id == cid)
        ).all():
            tasks_out.append(
                {
                    "title": task.title,
                    "status": task.status,
                    "due_at": task.due_at.isoformat() if task.due_at else None,
                }
            )

        for dl in db.scalars(
            select(Deadline).where(Deadline.owner_id == owner_id, Deadline.context_id == cid)
        ).all():
            deadlines_out.append(
                {"title": dl.title, "due_at": dl.due_at.isoformat() if dl.due_at else None}
            )

        for sess in db.scalars(
            select(StudySession).where(StudySession.owner_id == owner_id, StudySession.context_id == cid)
        ).all():
            msgs = [
                {"role": m.role, "content": m.content}
                for m in db.scalars(
                    select(ConversationMessage).where(
                        ConversationMessage.owner_id == owner_id,
                        ConversationMessage.study_session_id == sess.id,
                    )
                ).all()
            ]
            sessions_out.append({"mode": sess.mode, "messages": msgs})

        for concept in db.scalars(
            select(Concept).where(Concept.owner_id == owner_id, Concept.context_id == cid)
        ).all():
            state_row = db.scalar(
                select(LearnerConceptState).where(
                    LearnerConceptState.owner_id == owner_id,
                    LearnerConceptState.concept_id == concept.id,
                )
            )
            concepts_out.append(
                {
                    "name": concept.name,
                    "state": state_row.state if state_row else None,
                    "confidence": state_row.confidence if state_row else None,
                }
            )

        for res in db.scalars(
            select(Resource).where(Resource.owner_id == owner_id, Resource.context_id == cid)
        ).all():
            resources_out.append({"title": res.title, "type": res.resource_type})

        for assessment in db.scalars(
            select(Assessment).where(Assessment.owner_id == owner_id, Assessment.context_id == cid)
        ).all():
            attempts: list[dict] = []
            for attempt in db.scalars(
                select(AssessmentAttempt).where(
                    AssessmentAttempt.owner_id == owner_id,
                    AssessmentAttempt.assessment_id == assessment.id,
                )
            ).all():
                ev = db.scalar(select(Evaluation).where(Evaluation.attempt_id == attempt.id))
                if ev:
                    attempts.append(
                        {
                            "score": ev.score,
                            "total": ev.details.get("total"),
                            "attempt_status": attempt.status,
                        }
                    )
            assessments_out.append({"format": assessment.format, "attempts": attempts})

    data["notes"] = notes_out
    data["planned_tasks"] = tasks_out
    data["deadlines"] = deadlines_out
    data["study_sessions"] = sessions_out
    data["concepts"] = concepts_out
    data["resources"] = resources_out
    data["assessments"] = assessments_out
    data["badges"] = [_serialize(b) for b in _rows(db, LearnerBadge, owner_id=owner_id)]

    # --- additional learner-owned data omitted previously (issue 6) ---
    data["goals"] = [_serialize(g) for g in _rows(db, Goal, owner_id=owner_id)]
    data["learning_activities"] = [_serialize(a) for a in _rows(db, LearningActivity, owner_id=owner_id)]
    data["notifications"] = [_serialize(n) for n in _rows(db, Notification, owner_id=owner_id)]
    data["push_subscriptions"] = [_serialize(p) for p in _rows(db, PushSubscription, owner_id=owner_id)]

    # audio artifacts with nested progress
    audio_out: list[dict] = []
    for art in _rows(db, AudioArtifact, owner_id=owner_id):
        prog = db.scalar(
            select(AudioProgress).where(
                AudioProgress.owner_id == owner_id, AudioProgress.artifact_id == art.id
            )
        )
        d = _serialize(art)
        d["progress"] = _serialize(prog) if prog else None
        audio_out.append(d)
    data["audio_artifacts"] = audio_out
    data["audio_progress"] = [_serialize(p) for p in _rows(db, AudioProgress, owner_id=owner_id)]

    # concept graph and learner model
    data["concept_relations"] = [_serialize(r) for r in _rows(db, ConceptRelation, owner_id=owner_id)]
    data["resource_chunks"] = [_serialize(c) for c in _rows(db, ResourceChunk, owner_id=owner_id)]
    data["concept_chunks"] = [_serialize(c) for c in _rows(db, ConceptChunk, owner_id=owner_id)]
    data["evidence"] = [_serialize(e) for e in _rows(db, Evidence, owner_id=owner_id)]
    data["adaptation_decisions"] = [_serialize(a) for a in _rows(db, AdaptationDecision, owner_id=owner_id)]

    # BYO LLM key: metadata only (provider/model/hint). Ciphertext and
    # plaintext are never included in exports.
    data["llm_key"] = [
        {"provider": row.provider, "model": row.model, "hint": row.key_hint}
        for row in _rows(db, LearnerLLMKey, owner_id=owner_id)
    ]
    data["attempt_answers"] = [_serialize(a) for a in _rows(db, AttemptAnswer, owner_id=owner_id)]
    data["learner_concept_states"] = [_serialize(s) for s in _rows(db, LearnerConceptState, owner_id=owner_id)]
    return data


def delete_context_cascade(db: Session, *, owner_id: UUID, context_id: UUID) -> bool:
    ctx = _owned_context(db, owner_id=owner_id, context_id=context_id)
    if ctx is None:
        return False

    resource_ids = select(Resource.id).where(
        Resource.owner_id == owner_id, Resource.context_id == context_id
    )
    concept_ids = select(Concept.id).where(
        Concept.owner_id == owner_id, Concept.context_id == context_id
    )
    note_ids = select(Note.id).where(Note.owner_id == owner_id, Note.context_id == context_id)
    session_ids = select(StudySession.id).where(
        StudySession.owner_id == owner_id, StudySession.context_id == context_id
    )
    assessment_ids = select(Assessment.id).where(
        Assessment.owner_id == owner_id, Assessment.context_id == context_id
    )
    attempt_ids = select(AssessmentAttempt.id).where(
        AssessmentAttempt.owner_id == owner_id,
        AssessmentAttempt.assessment_id.in_(assessment_ids),
    )
    question_ids = select(AssessmentQuestion.id).where(
        AssessmentQuestion.assessment_id.in_(assessment_ids),
        AssessmentQuestion.owner_id == owner_id,
    )

    # --- children-first deletes (FK-safe): leaf tables before their parents ---
    # Explicit try/except with rollback covers every delete (not just final commit);
    # do NOT wrap in a second db.begin() — _owned_context lookup already opened
    # SQLAlchemy's autobegin transaction for this Session.
    try:
        # audio progress before artifacts (AudioProgress.artifact_id -> AudioArtifact.id)
        audio_note_artifact_ids = select(AudioArtifact.id).where(
            AudioArtifact.source_type == "NOTE", AudioArtifact.source_id.in_(note_ids)
        )
        audio_resource_artifact_ids = select(AudioArtifact.id).where(
            AudioArtifact.source_type == "RESOURCE", AudioArtifact.source_id.in_(resource_ids)
        )
        db.execute(delete(AudioProgress).where(AudioProgress.artifact_id.in_(audio_note_artifact_ids)))
        db.execute(delete(AudioProgress).where(AudioProgress.artifact_id.in_(audio_resource_artifact_ids)))
        # audio artifacts must be deleted before Note/Resource (note_ids/resource_ids subqueries would be empty after)
        db.execute(
            delete(AudioArtifact).where(AudioArtifact.source_type == "NOTE", AudioArtifact.source_id.in_(note_ids))
        )
        db.execute(
            delete(AudioArtifact).where(
                AudioArtifact.source_type == "RESOURCE", AudioArtifact.source_id.in_(resource_ids)
            )
        )

        # Evidence via required evaluation_id -> Evaluation -> AssessmentAttempt -> Assessment.context_id
        # (evaluation-based only; do not add OR concept_id — hides orphans)
        eval_ids_for_ctx = select(Evaluation.id).where(Evaluation.attempt_id.in_(attempt_ids))
        db.execute(delete(Evidence).where(Evidence.evaluation_id.in_(eval_ids_for_ctx)))
        db.execute(delete(AttemptAnswer).where(AttemptAnswer.attempt_id.in_(attempt_ids)))
        db.execute(delete(Evaluation).where(Evaluation.attempt_id.in_(attempt_ids)))

        # revision before note; concept-chunk before its two parents
        db.execute(delete(RevisionItem).where(RevisionItem.owner_id == owner_id, RevisionItem.note_id.in_(note_ids)))
        db.execute(delete(ConceptChunk).where(ConceptChunk.concept_id.in_(concept_ids)))

        # concept dependents before concept
        db.execute(
            delete(ConceptRelation).where(
                ConceptRelation.concept_id.in_(concept_ids)
                | ConceptRelation.prerequisite_concept_id.in_(concept_ids)
            )
        )
        db.execute(
            delete(LearnerConceptState).where(
                LearnerConceptState.owner_id == owner_id, LearnerConceptState.concept_id.in_(concept_ids)
            )
        )
        # AdaptationDecision linked by required context_id (covers NULL concept_id rows)
        db.execute(
            delete(AdaptationDecision).where(
                AdaptationDecision.owner_id == owner_id,
                AdaptationDecision.context_id == context_id,
            )
        )

        # messages before sessions; tasks before deadlines
        db.execute(delete(ConversationMessage).where(ConversationMessage.study_session_id.in_(session_ids)))
        db.execute(delete(PlannedTask).where(PlannedTask.owner_id == owner_id, PlannedTask.context_id == context_id))

        # note before its referenced parents (resource, concept, study_session)
        db.execute(delete(Note).where(Note.owner_id == owner_id, Note.context_id == context_id))

        # assessment question/attempt before assessment; chunks before resources
        db.execute(delete(AssessmentQuestion).where(AssessmentQuestion.id.in_(question_ids)))
        db.execute(delete(AssessmentAttempt).where(AssessmentAttempt.assessment_id.in_(assessment_ids)))
        db.execute(delete(ResourceChunk).where(ResourceChunk.resource_id.in_(resource_ids)))

        # deadline before resource (syllabus_resource_id -> resources)
        db.execute(delete(Deadline).where(Deadline.owner_id == owner_id, Deadline.context_id == context_id))

        # session/assessment/resource/concept before learning_context
        db.execute(delete(StudySession).where(StudySession.owner_id == owner_id, StudySession.context_id == context_id))
        db.execute(delete(Assessment).where(Assessment.owner_id == owner_id, Assessment.context_id == context_id))

        db.execute(delete(Resource).where(Resource.owner_id == owner_id, Resource.context_id == context_id))
        db.execute(delete(Concept).where(Concept.owner_id == owner_id, Concept.context_id == context_id))

        db.delete(ctx)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True