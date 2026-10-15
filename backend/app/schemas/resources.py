from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TextResourceCreate(BaseModel):
    context_id: UUID
    title: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1)


class TextResourceUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1)


class ResourceResponse(BaseModel):
    id: str
    context_id: str
    title: str
    resource_type: str
    processing_status: str
    error_detail: str | None = None
    chunk_count: int
    created_at: datetime
    # The chat this file belongs to; None when it is in the shared library.
    session_id: str | None = None


class ChunkResponse(BaseModel):
    chunk_index: int
    content: str
