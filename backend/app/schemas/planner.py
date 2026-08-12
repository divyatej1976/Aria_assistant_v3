from datetime import datetime

from pydantic import BaseModel, Field


class DeadlineCreateRequest(BaseModel):
    context_id: str
    title: str = Field(min_length=1, max_length=255)
    due_at: datetime
    syllabus_resource_id: str | None = None
    reminder_days_before: int = Field(default=5, ge=1, le=60)


class DeadlineResponse(BaseModel):
    id: str
    context_id: str
    title: str
    due_at: datetime
    syllabus_resource_id: str | None
    reminder_days_before: int
    reminder_sent_days_before: int | None
    status: str


class TaskCreateRequest(BaseModel):
    context_id: str
    title: str = Field(min_length=1, max_length=255)
    deadline_id: str | None = None
    due_at: datetime | None = None


class TaskResponse(BaseModel):
    id: str
    context_id: str
    deadline_id: str | None
    title: str
    due_at: datetime | None
    status: str
    completed_at: datetime | None


class NotificationResponse(BaseModel):
    id: str
    ntype: str
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime


class ReminderCheckResponse(BaseModel):
    notifications_created: int
    emails_delivered: int
    emails_logged: int
    emails_failed: int
