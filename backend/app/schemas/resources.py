from datetime import datetime

from pydantic import BaseModel, Field


class TextResourceCreate(BaseModel):
    context_id: str
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


class ChunkResponse(BaseModel):
    chunk_index: int
    content: str
