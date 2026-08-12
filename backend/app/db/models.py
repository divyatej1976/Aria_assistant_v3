from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class OwnedModel(TimestampMixin):
    owner_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)


class Learner(OwnedModel, Base):
    __tablename__ = "learners"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255))


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
    raw_bytes: Mapped[bytes | None] = mapped_column(LargeBinary)


class ResourceChunk(OwnedModel, Base):
    __tablename__ = "resource_chunks"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    resource_id: Mapped[UUID] = mapped_column(ForeignKey("resources.id"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    embedding_json: Mapped[list | None] = mapped_column(JSON)


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


class ConversationMessage(OwnedModel, Base):
    __tablename__ = "conversation_messages"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    study_session_id: Mapped[UUID] = mapped_column(ForeignKey("study_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Assessment(OwnedModel, Base):
    __tablename__ = "assessments"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    context_id: Mapped[UUID] = mapped_column(ForeignKey("learning_contexts.id"), index=True)
    mode: Mapped[str] = mapped_column(String(32), default="BASELINE", nullable=False)
    format: Mapped[str] = mapped_column(String(64), default="mcq", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="READY", nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class AssessmentQuestion(OwnedModel, Base):
    __tablename__ = "assessment_questions"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(ForeignKey("assessments.id"), index=True)
    concept_id: Mapped[UUID | None] = mapped_column(ForeignKey("concepts.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list] = mapped_column(JSON, nullable=False)
    correct_option: Mapped[str] = mapped_column(String(32), nullable=False)


class AssessmentAttempt(OwnedModel, Base):
    __tablename__ = "assessment_attempts"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(ForeignKey("assessments.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="IN_PROGRESS", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)


class AttemptAnswer(OwnedModel, Base):
    __tablename__ = "attempt_answers"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    attempt_id: Mapped[UUID] = mapped_column(ForeignKey("assessment_attempts.id"), index=True)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("assessment_questions.id"), index=True)
    selected_option: Mapped[str | None] = mapped_column(String(32))


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
