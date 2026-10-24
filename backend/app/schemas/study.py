from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.brain import ActionResponse


class StudySessionCreate(BaseModel):
    context_id: UUID
    mode: str = Field(default="BASELINE", max_length=32)


class StudySessionResponse(BaseModel):
    id: str
    context_id: str
    mode: str
    status: str
    created_at: datetime
    title: str | None = None
    preview: str | None = None
    message_count: int = 0
    last_message_at: datetime | None = None


class StudyMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)
    request_id: UUID | None = None
    # "auto" reads the question's tone; the screen size keeps phone replies short.
    depth: Literal["auto", "quick", "balanced", "deep"] = "auto"
    screen: Literal["compact", "regular", "wide"] = "regular"
    # Web search: None = when the question needs current information; True = always (the 🌐 button).
    web: bool | None = None


class SourceReference(BaseModel):
    resource_id: str
    chunk_id: str
    title: str
    score: float
    url: str | None = None  # web sources only


class StudyMessageResponse(BaseModel):
    id: str | None = None
    session_id: str
    content: str
    sources: list[SourceReference]
    fallback_used: bool
    action: ActionResponse | None = None
    depth: str | None = None


class StudyMessage(BaseModel):
    id: str
    role: str
    content: str
    sources: list[SourceReference]
    position: int
    fallback_used: bool | None = None
    action: ActionResponse | None = None
    depth: str | None = None
