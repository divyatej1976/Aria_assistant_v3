"""Learner data controls: full export and context deletion (explicit cascades)."""

import base64
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    AdaptationDecision,
    AgentTask,
    ApprovalRequest,
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AttemptAnswer,
    AudioArtifact,
    AudioProgress,
    AuditLog,
    Concept,
    ConceptChunk,
    ConceptRelation,
    ConversationMessage,
    Deadline,
    Evaluation,
    Evidence,
    Goal,
    Learner,
    LearnerAiUsage,
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
    Roadmap,
    RoadmapMilestone,
    StudySession,
    Workflow,
)


def _owned_context(db: Session, *, owner_id: UUID, context_id: UUID) -> LearningContext | None:
    return db.scalar(
        select(LearningContext).where(
            LearningContext.id == context_id, LearningContext.owner_id == owner_id
        )
    )


# Explicit allowlist: authentication/session/idempotency records are never exported.
_EXPORT_COLLECTIONS = {
    "preferences": LearnerPreference, "goals": Goal, "contexts": LearningContext,
    "notes": Note, "revision_items": RevisionItem, "planned_tasks": PlannedTask,
    "deadlines": Deadline, "study_sessions": StudySession,
    "conversation_messages": ConversationMessage, "concepts": Concept,
    "resources": Resource, "resource_chunks": ResourceChunk,
    "concept_chunks": ConceptChunk, "concept_relations": ConceptRelation,
    "learner_concept_states": LearnerConceptState, "assessments": Assessment,
    "assessment_questions": AssessmentQuestion, "assessment_attempts": AssessmentAttempt,
    "attempt_answers": AttemptAnswer, "evaluations": Evaluation, "evidence": Evidence,
    "adaptation_decisions": AdaptationDecision, "badges": LearnerBadge,
    "learning_activities": LearningActivity, "notifications": Notification,
    "audio_artifacts": AudioArtifact, "audio_progress": AudioProgress,
    "roadmaps": Roadmap, "roadmap_milestones": RoadmapMilestone,
    "workflows": Workflow, "agent_tasks": AgentTask, "approvals": ApprovalRequest,
    "audit_logs": AuditLog, "learner_ai_usage": LearnerAiUsage,
    "push_subscriptions": PushSubscription, "llm_key": LearnerLLMKey,
}


def _serialize_export(row) -> dict:
    if isinstance(row, LearnerLLMKey):
        return {"id": str(row.id), "owner_id": str(row.owner_id),
                "provider": row.provider, "model": row.model, "hint": row.key_hint}
    out = {}
    for column in row.__table__.columns:
        # Derived vectors and push authentication material are deliberately omitted.
        if column.name in {"embedding", "embedding_json", "generation_token", "lease_until"}:
            continue
        if isinstance(row, PushSubscription) and column.name in {"auth", "p256dh"}:
            continue
        value = getattr(row, column.name)
        if isinstance(value, bytes):
            value = base64.b64encode(value).decode("ascii")
        elif isinstance(value, UUID):
            value = str(value)
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        out[column.name] = value
    if isinstance(row, AudioArtifact):
        from app.services.audio import load_audio_bytes

        audio = load_audio_bytes(row)
        out["audio_bytes"] = base64.b64encode(audio).decode("ascii") if audio is not None else None
        out["audio_bytes_status"] = (
            "included" if audio is not None else "unavailable" if row.status == "READY" else "not_generated"
        )
    if isinstance(row, Resource):
        out["original_bytes_status"] = (
            "included" if row.raw_bytes is not None
            else "not_applicable" if row.resource_type == "TEXT" else "unavailable"
        )
    return out


def stream_learner_data(db: Session, *, owner_id: UUID):
    """Stream portable JSON with bounded row batches from an owned snapshot.

    The generator owns its session through completion/cancellation; it does not
    depend on FastAPI dependency cleanup timing. No collection/message caps.
    """
    encoder = json.JSONEncoder(default=str, ensure_ascii=True)
    with Session(bind=db.get_bind()) as snapshot:
        dialect = snapshot.get_bind().dialect.name
        snapshot.connection(execution_options={
            "isolation_level": "REPEATABLE READ" if dialect == "postgresql" else "SERIALIZABLE"
        })
        if dialect == "sqlite":
            # Python's legacy SQLite mode otherwise does not start a snapshot on SELECT.
            snapshot.connection().exec_driver_sql("BEGIN")
        learner = snapshot.get(Learner, owner_id)
        metadata = {
            "schema_version": 2,
            "exported_at": datetime.now(UTC).isoformat(),
            "owner_id": str(owner_id), "truncated": False,
            "binary_encoding": "base64",
            "omissions": [
                "Authentication secrets, active sessions and idempotency reservations",
                "LLM credential ciphertext/plaintext and push authentication keys",
                "Derived embedding vectors (regenerate from resource chunks)",
                "Transient audio leases and generation tokens",
            ],
            "relationships": "Original UUIDs and foreign IDs are preserved in separate collections.",
        }
        profile = {"id": str(owner_id), "email": learner.email if learner else None,
                   "display_name": learner.display_name if learner else None,
                   "verified": learner.verified_at is not None if learner else False}
        if learner:
            for field in ("owner_id", "created_at", "updated_at", "verified_at"):
                value = getattr(learner, field)
                profile[field] = value.isoformat() if hasattr(value, "isoformat") else str(value) if value else None
        yield '{"metadata":'
        yield from encoder.iterencode(metadata)
        yield ',"profile":'
        yield from encoder.iterencode(profile)
        counts = {}
        for name, model in _EXPORT_COLLECTIONS.items():
            yield ',' + json.dumps(name) + ':['
            count = 0
            batch_size = 1 if model in (Resource, AudioArtifact) else 100
            rows = snapshot.scalars(select(model).where(model.owner_id == owner_id)
                                    .order_by(model.id).execution_options(yield_per=batch_size))
            for row in rows:
                if count:
                    yield ','
                yield from encoder.iterencode(_serialize_export(row))
                count += 1
                snapshot.expunge(row)
            counts[name] = count
            yield ']'
        yield ',"record_counts":'
        yield from encoder.iterencode(counts)
        yield '}'


def export_learner_data(db: Session, *, owner_id: UUID) -> dict:
    """Materialized helper for offline callers; HTTP uses the streaming variant."""
    return json.loads("".join(stream_learner_data(db, owner_id=owner_id)))


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
        audio_keys = list(db.scalars(select(AudioArtifact.storage_key).where(
            AudioArtifact.owner_id == owner_id,
            or_(
                (AudioArtifact.source_type == "NOTE") & AudioArtifact.source_id.in_(note_ids),
                (AudioArtifact.source_type == "RESOURCE") & AudioArtifact.source_id.in_(resource_ids),
            ),
        )))
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

        # roadmaps before learning_context
        roadmap_ids = select(Roadmap.id).where(Roadmap.owner_id == owner_id, Roadmap.context_id == context_id)
        db.execute(delete(RoadmapMilestone).where(RoadmapMilestone.roadmap_id.in_(roadmap_ids)))
        db.execute(delete(Roadmap).where(Roadmap.owner_id == owner_id, Roadmap.context_id == context_id))

        db.execute(delete(Resource).where(Resource.owner_id == owner_id, Resource.context_id == context_id))
        db.execute(delete(Concept).where(Concept.owner_id == owner_id, Concept.context_id == context_id))

        db.delete(ctx)
        db.commit()
    except Exception:
        db.rollback()
        raise
    from app.services.audio import _remove_stored

    _remove_stored(audio_keys)
    return True
