from uuid import UUID

from pydantic import BaseModel, Field


class PreferenceItem(BaseModel):
    key: str
    value: str


class PreferenceUpsertRequest(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=500)


class MemorySummary(BaseModel):
    preferences: list[PreferenceItem]
    concepts: int
    weak_concepts: int
    supported_concepts: int
    evidence_count: int
    message_count: int


class PrerequisiteAddRequest(BaseModel):
    prerequisite_concept_id: UUID


class PrerequisiteResponse(BaseModel):
    concept_id: str
    prerequisite_concept_id: str
    prerequisite_name: str
