from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AssessmentSubmitted:
    attempt_id: UUID
    owner_id: UUID


@dataclass(frozen=True)
class EvaluationCompleted:
    evaluation_id: UUID
    attempt_id: UUID
    owner_id: UUID


@dataclass(frozen=True)
class EvidenceRecorded:
    evidence_id: UUID
    concept_id: UUID
    owner_id: UUID


@dataclass(frozen=True)
class LearnerStateUpdated:
    concept_id: UUID
    owner_id: UUID
    state: str


@dataclass(frozen=True)
class AdaptationCreated:
    adaptation_id: UUID
    context_id: UUID
    owner_id: UUID
