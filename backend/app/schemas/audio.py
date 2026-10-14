from datetime import datetime

from pydantic import BaseModel, Field


class AudioResponse(BaseModel):
    id: str
    source_type: str
    source_id: str
    text: str
    status: str
    error_detail: str | None
    content_type: str | None
    duration_seconds: int | None
    created_at: datetime


class AudioListItem(BaseModel):
    """Lightweight durable-listing row (no bulky text; title resolved via source)."""

    id: str
    source_type: str
    source_id: str
    title: str
    status: str
    content_type: str | None
    duration_seconds: int | None
    position_seconds: int
    completed: bool
    created_at: datetime


class ProgressUpdateRequest(BaseModel):
    position_seconds: int = Field(default=0, ge=0)
    completed: bool = False


class ProgressResponse(BaseModel):
    position_seconds: int
    completed: bool


class TranscribeResponse(BaseModel):
    text: str
