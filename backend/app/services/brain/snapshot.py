"""Bounded, subject-scoped projections. Reading never flushes or commits."""

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Concept,
    ConversationMessage,
    Deadline,
    Evidence,
    LearnerConceptState,
    LearnerPreference,
    PlannedTask,
    Roadmap,
    RoadmapMilestone,
    StudySession,
)
from app.services.contexts import get_owned_context
from app.services.learner_state import STATE_SUPPORTED
from app.services.memory import WEAK_STATES

MAX_CONCEPTS = 50
MAX_EVIDENCE = 30
MAX_ROADMAPS = 10
MAX_TASKS = 20


class SnapshotModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ConceptSnapshot(SnapshotModel):
    id: UUID
    name: str
    state: str
    confidence: int


class EvidenceSnapshot(SnapshotModel):
    id: UUID
    concept_id: UUID
    signal: str


class RoadmapSnapshot(SnapshotModel):
    id: UUID
    total: int
    supported: int


class TaskSnapshot(SnapshotModel):
    id: UUID
    due_at: datetime | None


class MemorySnapshot(SnapshotModel):
    concepts: int = 0
    supported_concepts: int = 0
    weak_concepts: int = 0
    evidence_count: int = 0
    message_count: int = 0


class AssessmentPreferences(SnapshotModel):
    # Missing preferences stay missing; the future action card can ask.
    format: Literal["mcq", "short_answer", "mixed"] | None = None
    question_count: int | None = Field(default=None, ge=1, le=100)
    timed: bool | None = None
    time_limit_seconds: int | None = Field(default=None, ge=1, le=86400)


class LearnerSnapshot(SnapshotModel):
    owner_id: UUID
    context_id: UUID
    as_of: datetime
    concepts: tuple[ConceptSnapshot, ...] = ()
    evidence: tuple[EvidenceSnapshot, ...] = ()
    roadmaps: tuple[RoadmapSnapshot, ...] = ()
    upcoming_deadlines: tuple[TaskSnapshot, ...] = ()
    missed_tasks: tuple[TaskSnapshot, ...] = ()
    memory: MemorySnapshot = Field(default_factory=MemorySnapshot)
    assessment_preferences: AssessmentPreferences = Field(default_factory=AssessmentPreferences)


def _assessment_preferences(db: Session, owner_id: UUID) -> AssessmentPreferences:
    keys = ("assessment.format", "assessment.question_count", "assessment.timed", "assessment.time_limit_seconds")
    values = dict(
        db.execute(
            select(LearnerPreference.key, LearnerPreference.value).where(
                LearnerPreference.owner_id == owner_id,
                LearnerPreference.key.in_(keys),
            )
        ).all()
    )
    parsed = {}
    for key in keys:
        value = values.get(key)
        if value is None:
            continue
        field = key.split(".", 1)[1]
        try:
            # Validate each field independently so one stale preference cannot
            # discard other settings or introduce arbitrary memory text.
            parsed[field] = getattr(AssessmentPreferences.model_validate({field: value}), field)
        except ValueError:
            continue
    return AssessmentPreferences(**parsed)


def build_snapshot(db: Session, *, owner_id: UUID, context_id: UUID) -> LearnerSnapshot:
    now = datetime.now(UTC)
    with db.no_autoflush:
        get_owned_context(db, owner_id=owner_id, context_id=context_id)
        states = (
            select(Concept.id, Concept.name, LearnerConceptState.state, LearnerConceptState.confidence)
            .join(
                LearnerConceptState,
                LearnerConceptState.concept_id == Concept.id,
            )
            .where(
                Concept.owner_id == owner_id, Concept.context_id == context_id, LearnerConceptState.owner_id == owner_id
            )
        )
        concept_rows = db.execute(
            states.order_by(LearnerConceptState.updated_at.desc(), Concept.id).limit(MAX_CONCEPTS)
        ).all()
        # Aggregates use their own owner-scoped join, never the bounded sample.
        concept_count = (
            db.scalar(
                select(func.count(Concept.id)).where(Concept.owner_id == owner_id, Concept.context_id == context_id)
            )
            or 0
        )
        state_counts = dict(
            db.execute(
                select(LearnerConceptState.state, func.count())
                .join(
                    Concept,
                    Concept.id == LearnerConceptState.concept_id,
                )
                .where(
                    Concept.owner_id == owner_id,
                    Concept.context_id == context_id,
                    LearnerConceptState.owner_id == owner_id,
                )
                .group_by(LearnerConceptState.state)
            ).all()
        )
        evidence_query = (
            select(Evidence.id, Evidence.concept_id, Evidence.signal)
            .join(
                Concept,
                Concept.id == Evidence.concept_id,
            )
            .where(
                Evidence.owner_id == owner_id,
                Evidence.valid.is_(True),
                Concept.owner_id == owner_id,
                Concept.context_id == context_id,
            )
        )
        evidence_rows = db.execute(
            evidence_query.order_by(Evidence.created_at.desc(), Evidence.id).limit(MAX_EVIDENCE)
        ).all()
        evidence_count = db.scalar(select(func.count()).select_from(evidence_query.subquery())) or 0
        roadmap_ids = (
            select(Roadmap.id)
            .where(Roadmap.owner_id == owner_id, Roadmap.context_id == context_id, Roadmap.status == "ACTIVE")
            .order_by(Roadmap.created_at.desc(), Roadmap.id)
            .limit(MAX_ROADMAPS)
            .subquery()
        )
        roadmap_rows = db.execute(
            select(
                Roadmap.id,
                func.count(RoadmapMilestone.id),
                func.sum(case((RoadmapMilestone.state == STATE_SUPPORTED, 1), else_=0)),
            )
            .join(
                roadmap_ids,
                roadmap_ids.c.id == Roadmap.id,
            )
            .outerjoin(
                RoadmapMilestone, (RoadmapMilestone.roadmap_id == Roadmap.id) & (RoadmapMilestone.owner_id == owner_id)
            )
            .group_by(Roadmap.id)
            .order_by(Roadmap.id)
        ).all()
        deadlines = db.execute(
            select(Deadline.id, Deadline.due_at)
            .where(
                Deadline.owner_id == owner_id,
                Deadline.context_id == context_id,
                Deadline.status == "ACTIVE",
                Deadline.due_at >= now,
                Deadline.due_at <= now + timedelta(days=14),
            )
            .order_by(Deadline.due_at, Deadline.id)
            .limit(MAX_TASKS)
        ).all()
        missed = db.execute(
            select(PlannedTask.id, PlannedTask.due_at)
            .where(
                PlannedTask.owner_id == owner_id,
                PlannedTask.context_id == context_id,
                PlannedTask.status == "PENDING",
                PlannedTask.due_at < now,
            )
            .order_by(PlannedTask.due_at, PlannedTask.id)
            .limit(MAX_TASKS)
        ).all()
        message_count = (
            db.scalar(
                select(func.count(ConversationMessage.id))
                .join(
                    StudySession,
                    StudySession.id == ConversationMessage.study_session_id,
                )
                .where(
                    ConversationMessage.owner_id == owner_id,
                    StudySession.owner_id == owner_id,
                    StudySession.context_id == context_id,
                )
            )
            or 0
        )
        return LearnerSnapshot(
            owner_id=owner_id,
            context_id=context_id,
            as_of=now,
            concepts=tuple(
                ConceptSnapshot(id=r.id, name=r.name[:200], state=r.state, confidence=r.confidence)
                for r in concept_rows
            ),
            evidence=tuple(EvidenceSnapshot(id=r.id, concept_id=r.concept_id, signal=r.signal) for r in evidence_rows),
            roadmaps=tuple(RoadmapSnapshot(id=r[0], total=r[1], supported=r[2] or 0) for r in roadmap_rows),
            upcoming_deadlines=tuple(TaskSnapshot(id=r.id, due_at=r.due_at) for r in deadlines),
            missed_tasks=tuple(TaskSnapshot(id=r.id, due_at=r.due_at) for r in missed),
            memory=MemorySnapshot(
                concepts=concept_count,
                supported_concepts=state_counts.get(STATE_SUPPORTED, 0),
                weak_concepts=sum(state_counts.get(s, 0) for s in WEAK_STATES),
                evidence_count=evidence_count,
                message_count=message_count,
            ),
            assessment_preferences=_assessment_preferences(db, owner_id),
        )
