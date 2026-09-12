from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StudySessionCreate(BaseModel):
    context_id: UUID
    mode: str = Field(default="BASELINE", max_length=32)


class StudySessionResponse(BaseModel):
    id: str
    context_id: str
    mode: str
    status: str
    created_at: datetime


class StudyMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)


class SourceReference(BaseModel):
    resource_id: str
    chunk_id: str
    title: str
    score: float


class StudyMessageResponse(BaseModel):
    session_id: str
    content: str
    sources: list[SourceReference]
    fallback_used: bool


class StudyMessage(BaseModel):
    id: str
    role: str
    content: str
    sources: list[SourceReference]
