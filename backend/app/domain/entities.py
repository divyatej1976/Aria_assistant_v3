from dataclasses import dataclass
from uuid import UUID

from app.domain.enums import LearnerConceptState, WorkflowState


@dataclass(frozen=True)
class LearnerIdentity:
    id: UUID
    email: str


@dataclass(frozen=True)
class LearningContextRef:
    id: UUID
    owner_id: UUID
    title: str


@dataclass(frozen=True)
class LearnerConceptSignal:
    concept_id: UUID
    state: LearnerConceptState
    confidence: int
    reason: str


@dataclass(frozen=True)
class WorkflowSnapshot:
    context_id: UUID
    state: WorkflowState
