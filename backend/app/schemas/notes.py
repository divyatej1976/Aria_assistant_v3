from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NoteCreateRequest(BaseModel):
    context_id: UUID
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    concept_id: UUID | None = None


class NoteUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)


class NoteResponse(BaseModel):
    id: str
    context_id: str
    title: str
    body: str
    concept_id: str | None
    study_session_id: str | None
    created_at: datetime
    state: str | None = None
    interval_days: int | None = None
    next_review_at: datetime | None = None
    last_outcome: str | None = None


class NoteDraft(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)


class GenerateRequest(BaseModel):
    context_id: UUID
    study_session_id: UUID | None = None


class ReviewRequest(BaseModel):
    outcome: str = Field(pattern="^(again|good)$")
