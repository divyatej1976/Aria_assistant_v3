from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TextAudioRequest(BaseModel):
    context_id: UUID
    title: str = Field(default="Audio from text", min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=200_000)
    # "explainer": one tutor voice; "conversation": a tutor and a learner.
    style: Literal["explainer", "conversation"] = "explainer"


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
    # Where each part of a long episode starts; empty for single-part episodes.
    parts: list[dict] = []
    # The background job's current step while the episode is being made.
    step: str | None = None
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
