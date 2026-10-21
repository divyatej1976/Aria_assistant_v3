from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

try:
    from pgvector.sqlalchemy import Vector as _PgVector  # type: ignore[import-not-found]

    def _embedding_column_type() -> object:
        from app.core.config import get_settings

        try:
            dim = get_settings().aria_embedding_dim
        except Exception:
            dim = 768
        # Store as pgvector on Postgres, JSON fallback for SQLite/tests
        return _PgVector(dim).with_variant(JSON, "sqlite")  # type: ignore[attr-defined]

    _EMBEDDING_TYPE = _embedding_column_type()
except ImportError:
    _EMBEDDING_TYPE = JSON  # type: ignore[assignment]


class OwnedModel(TimestampMixin):
    owner_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)


class Learner(OwnedModel, Base):
    __tablename__ = "learners"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LearnerSession(OwnedModel, Base):
    __tablename__ = "learner_sessions"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    device_label: Mapped[str | None] = mapped_column(String(120))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Goal(OwnedModel, Base):
    __tablename__ = "goals"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)


class LearningContext(OwnedModel, Base):
    __tablename__ = "learning_contexts"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    goal_id: Mapped[UUID | None] = mapped_column(ForeignKey("goals.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    concept_sync_fingerprint: Mapped[str | None] = mapped_column(String(64))
    concept_sync_names: Mapped[list | None] = mapped_column(JSON)


class Concept(OwnedModel, Base):
    __tablename__ = "concepts"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    context_id: Mapped[UUID] = mapped_column(ForeignKey("learning_contexts.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class ConceptRelation(OwnedModel, Base):
    __tablename__ = "concept_relations"
    __table_args__ = (
        UniqueConstraint(
            "concept_id", "prerequisite_concept_id", name="uq_concept_relation"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    concept_id: Mapped[UUID] = mapped_column(ForeignKey("concepts.id"), index=True)
    prerequisite_concept_id: Mapped[UUID] = mapped_column(ForeignKey("concepts.id"), index=True)


class LearnerPreference(OwnedModel, Base):
    __tablename__ = "learner_preferences"
    __table_args__ = (
        UniqueConstraint("owner_id", "key", name="uq_learner_preference_key"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)


class Note(OwnedModel, Base):
    __tablename__ = "notes"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    context_id: Mapped[UUID] = mapped_column(ForeignKey("learning_contexts.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(ForeignKey("resources.id"), index=True)
    concept_id: Mapped[UUID | None] = mapped_column(ForeignKey("concepts.id"), index=True)
    study_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("study_sessions.id"), index=True
    )
    source_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class RevisionItem(OwnedModel, Base):
    __tablename__ = "revision_items"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    note_id: Mapped[UUID] = mapped_column(ForeignKey("notes.id"), index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="NEW", nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_outcome: Mapped[str | None] = mapped_column(String(32))


class LearningActivity(OwnedModel, Base):
    __tablename__ = "learning_activities"
    __table_args__ = (
        # Dedupe guard for the same meaningful action on the same day;
        # record_activity callers always supply source_id.
        UniqueConstraint(
            "owner_id",
            "activity_type",
            "occurred_on",
            "source_id",
            name="uq_learning_activity_owner_type_day_source",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))


class LearnerBadge(OwnedModel, Base):
    __tablename__ = "learner_badges"
    __table_args__ = (
        UniqueConstraint("owner_id", "code", name="uq_learner_badge_code"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Deadline(OwnedModel, Base):
    __tablename__ = "deadlines"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    context_id: Mapped[UUID] = mapped_column(ForeignKey("learning_contexts.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    syllabus_resource_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("resources.id"), index=True
    )
    reminder_days_before: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    reminder_sent_days_before: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)


class PlannedTask(OwnedModel, Base):
    __tablename__ = "planned_tasks"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    context_id: Mapped[UUID] = mapped_column(ForeignKey("learning_contexts.id"), index=True)
    deadline_id: Mapped[UUID | None] = mapped_column(ForeignKey("deadlines.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(OwnedModel, Base):
    __tablename__ = "notifications"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    ntype: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PushSubscription(OwnedModel, Base):
    __tablename__ = "push_subscriptions"
    __table_args__ = (
        UniqueConstraint("endpoint", name="uq_push_subscription_endpoint"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)


class IdempotencyKey(OwnedModel, Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("owner_id", "scope", "key", name="uq_idempotency_owner_scope_key"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workflow_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_json: Mapped[dict | None] = mapped_column(JSON)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AiUsage(TimestampMixin, Base):
    __tablename__ = "ai_usage"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    period: Mapped[str] = mapped_column(String(7), nullable=False, unique=True)
    spend_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class LearnerLLMKey(OwnedModel, Base):
    """BYO Groq key per learner (Step 4). Only ciphertext is stored."""

    __tablename__ = "learner_llm_keys"
    __table_args__ = (
        UniqueConstraint("owner_id", name="uq_learner_llm_key_owner"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(32), default="groq", nullable=False)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    key_hint: Mapped[str] = mapped_column(String(16), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128))


class LearnerAiUsage(OwnedModel, Base):
    """Per-learner monthly AI spend (Step 4). Global `ai_usage` stays separate."""

    __tablename__ = "learner_ai_usage"
    __table_args__ = (
        UniqueConstraint("owner_id", "period", name="uq_learner_ai_usage_owner_period"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    spend_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class RateLimitBucket(Base):
    """Shared fixed-window rate-limit buckets (multi-replica safe, backend=db).

    `window_started_at` is deliberately naive UTC: SQLite drops tzinfo from
    DateTime(timezone=True) columns, which would make cross-dialect window
    comparisons inconsistent.
    """

    __tablename__ = "rate_limit_buckets"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class AudioArtifact(OwnedModel, Base):
    __tablename__ = "audio_artifacts"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text)
    audio_bytes: Mapped[bytes | None] = mapped_column(LargeBinary)
    content_type: Mapped[str | None] = mapped_column(String(64))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    storage_key: Mapped[str | None] = mapped_column(String(500))
    generation_token: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generation_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    # "explainer" or "conversation", kept so a recovered job uses the learner's choice.
    style: Mapped[str | None] = mapped_column(String(16), nullable=True)


class AudioProgress(OwnedModel, Base):
    __tablename__ = "audio_progress"
    __table_args__ = (
        UniqueConstraint("owner_id", "artifact_id", name="uq_audio_progress_artifact"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    artifact_id: Mapped[UUID] = mapped_column(
        ForeignKey("audio_artifacts.id"), index=True, nullable=False
    )
    position_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Workflow(OwnedModel, Base):
    __tablename__ = "workflows"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="RUNNING", nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text)


class AgentTask(OwnedModel, Base):
    __tablename__ = "agent_tasks"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflows.id"), index=True, nullable=False
    )
    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_refs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_refs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text)


class ApprovalRequest(OwnedModel, Base):
    __tablename__ = "approval_requests"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflows.id"), index=True, nullable=False
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(OwnedModel, Base):
    __tablename__ = "audit_log"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64))


class Resource(OwnedModel, Base):
    __tablename__ = "resources"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    context_id: Mapped[UUID] = mapped_column(ForeignKey("learning_contexts.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(32), default="PROCESSING", nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text)
    storage_key: Mapped[str | None] = mapped_column(String(500))
    source_text: Mapped[str | None] = mapped_column(Text)
    # Notes condensed from the whole file, built in the background for long files.
    digest: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_bytes: Mapped[bytes | None] = mapped_column(LargeBinary)
    # Set when the file was attached inside one chat: only that chat may use it.
    # NULL means it is in the subject's library and every chat can use it.
    study_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("study_sessions.id"), index=True, nullable=True
    )


class ResourceChunk(OwnedModel, Base):
    __tablename__ = "resource_chunks"
    __table_args__ = (
        # Created by migration 0011; declared so autogenerate does not drop it.
        Index(
            "ix_resource_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ).ddl_if(dialect="postgresql"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    resource_id: Mapped[UUID] = mapped_column(ForeignKey("resources.id"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    embedding_json: Mapped[list | None] = mapped_column(JSON)
    embedding: Mapped[list | None] = mapped_column(_EMBEDDING_TYPE, nullable=True)  # type: ignore[arg-type]


class ConceptChunk(OwnedModel, Base):
    __tablename__ = "concept_chunks"
    __table_args__ = (
        UniqueConstraint("concept_id", "chunk_id", name="uq_concept_chunk"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    concept_id: Mapped[UUID] = mapped_column(ForeignKey("concepts.id"), index=True)
    chunk_id: Mapped[UUID] = mapped_column(ForeignKey("resource_chunks.id"), index=True)


class StudySession(OwnedModel, Base):
    __tablename__ = "study_sessions"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    context_id: Mapped[UUID] = mapped_column(ForeignKey("learning_contexts.id"), index=True)
    mode: Mapped[str] = mapped_column(String(32), default="BASELINE", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    # A short name like "Array Patterns Learning Plan", written after the first reply.
    title: Mapped[str | None] = mapped_column(String(80), nullable=True)


class ConversationMessage(OwnedModel, Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        UniqueConstraint(
            "study_session_id", "position", name="uq_conversation_message_position"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    study_session_id: Mapped[UUID] = mapped_column(ForeignKey("study_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # NULL means legacy response provenance is unknown, not generated.
    fallback_used: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    action: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Reply length the tutor used (quick/balanced/deep); NULL for older replies.
    response_depth: Mapped[str | None] = mapped_column(String(16), nullable=True)


class BrainAction(OwnedModel, Base):
    """Durable action identity; LangGraph owns the new flow's execution."""
    __tablename__ = "brain_actions"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    context_id: Mapped[UUID] = mapped_column(ForeignKey("learning_contexts.id"), index=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("study_sessions.id"), index=True)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="proposed", nullable=False)
    artifact_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claim_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    through_position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Assessment(OwnedModel, Base):
    __tablename__ = "assessments"
    __table_args__ = (
        UniqueConstraint("owner_id", "context_id", "daily_review_date", name="uq_assessment_daily_review"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    context_id: Mapped[UUID] = mapped_column(ForeignKey("learning_contexts.id"), index=True)
    mode: Mapped[str] = mapped_column(String(32), default="BASELINE", nullable=False)
    format: Mapped[str] = mapped_column(String(64), default="mcq", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="READY", nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    daily_review_date: Mapped[str | None] = mapped_column(String(10), nullable=True)


class AssessmentQuestion(OwnedModel, Base):
    __tablename__ = "assessment_questions"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(ForeignKey("assessments.id"), index=True)
    concept_id: Mapped[UUID | None] = mapped_column(ForeignKey("concepts.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list] = mapped_column(JSON, nullable=False)
    # Unbounded text: option values are generated from real study material
    # and routinely exceed 32 chars; PostgreSQL enforces varchar limits that
    # SQLite ignores (StringDataRightTruncation in the production drill).
    correct_option: Mapped[str] = mapped_column(Text, nullable=False)
    # mcq | true_false | short_answer. Short answers store the expected text in
    # correct_option and have no options.
    kind: Mapped[str] = mapped_column(String(16), default="mcq", server_default="mcq", nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)


class AssessmentAttempt(OwnedModel, Base):
    __tablename__ = "assessment_attempts"
    __table_args__ = (
        # Client-generated keys are only required unique per owner; a global
        # unique made an unrelated learner's key collide with a 500.
        UniqueConstraint(
            "owner_id", "idempotency_key", name="uq_attempt_owner_idempotency"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(ForeignKey("assessments.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="IN_PROGRESS", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)


class AttemptAnswer(OwnedModel, Base):
    __tablename__ = "attempt_answers"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    attempt_id: Mapped[UUID] = mapped_column(ForeignKey("assessment_attempts.id"), index=True)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("assessment_questions.id"), index=True)
    selected_option: Mapped[str | None] = mapped_column(Text)


class Evaluation(OwnedModel, Base):
    __tablename__ = "evaluations"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    attempt_id: Mapped[UUID] = mapped_column(ForeignKey("assessment_attempts.id"), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    score: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Evidence(OwnedModel, Base):
    __tablename__ = "evidence"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    concept_id: Mapped[UUID | None] = mapped_column(ForeignKey("concepts.id"), index=True)
    evaluation_id: Mapped[UUID] = mapped_column(ForeignKey("evaluations.id"), index=True)
    signal: Mapped[str] = mapped_column(String(32), nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LearnerConceptState(OwnedModel, Base):
    __tablename__ = "learner_concept_states"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    concept_id: Mapped[UUID] = mapped_column(ForeignKey("concepts.id"), index=True)
    state: Mapped[str] = mapped_column(String(32), default="UNTESTED", nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class AdaptationDecision(OwnedModel, Base):
    __tablename__ = "adaptation_decisions"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    context_id: Mapped[UUID] = mapped_column(ForeignKey("learning_contexts.id"), index=True)
    concept_id: Mapped[UUID | None] = mapped_column(ForeignKey("concepts.id"), index=True)
    decision_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="READY", nullable=False)


class Roadmap(OwnedModel, Base):
    __tablename__ = "roadmaps"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    context_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("learning_contexts.id"), index=True, nullable=True
    )
    goal: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(64), default="Beginner", nullable=False)
    target_date: Mapped[str | None] = mapped_column(String(64))
    # Study time the learner can give each week; paces "This week" and the plan.
    hours_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # concepts | projects | exams | interviews | mixed; reused when the plan is refined.
    focus: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    generation_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fallback_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)


class RoadmapMilestone(OwnedModel, Base):
    __tablename__ = "roadmap_milestones"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    roadmap_id: Mapped[UUID] = mapped_column(
        ForeignKey("roadmaps.id", ondelete="CASCADE"), index=True, nullable=False
    )
    phase_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phase_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    key_skills: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    prerequisites: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="NOT_STARTED", nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # outcome, effort_hours, activity, check: how the learner works through it.
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Job(OwnedModel, Base):
    """Slow work done outside the request: audio episodes, whole-file digests.

    Any number of workers run jobs at once; each claims one row with a lease, so a job is
    never run twice, and a worker that dies or runs out of time is picked up again.
    """

    __tablename__ = "jobs"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    # queued, running, done, failed
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Saved between steps so a long job resumes where it stopped.
    progress: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)


class UploadChunk(OwnedModel, Base):
    """One piece of a large upload, kept until the upload is assembled (requests cap at 4.5 MB)."""

    __tablename__ = "upload_chunks"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    upload_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
