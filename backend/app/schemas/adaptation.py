from datetime import datetime

from pydantic import BaseModel


class ConceptResponse(BaseModel):
    id: str
    name: str


class ConceptStateResponse(BaseModel):
    concept_id: str
    concept_name: str
    state: str
    confidence: int
    reason: str


class AdaptationDecisionResponse(BaseModel):
    concept_id: str | None
    decision_type: str
    reason: str


class EvidenceResponse(BaseModel):
    id: str
    concept_id: str
    concept_name: str
    signal: str
    valid: bool
    created_at: datetime


class CycleSummaryResponse(BaseModel):
    states: list[ConceptStateResponse]
    decisions: list[AdaptationDecisionResponse]
