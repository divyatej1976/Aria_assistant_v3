from datetime import datetime

from pydantic import BaseModel


class ApprovalResponse(BaseModel):
    id: str
    workflow_id: str
    action: str
    detail: str
    status: str


class WorkflowStartResponse(BaseModel):
    workflow_id: str
    status: str
    approval: ApprovalResponse | None = None


class WorkflowResponse(BaseModel):
    id: str
    name: str
    status: str
    current_step: int
    error_detail: str | None
    created_at: datetime


class TaskResponse(BaseModel):
    id: str
    workflow_id: str
    agent: str
    status: str
    attempt: int
    error_detail: str | None
    created_at: datetime


class AuditResponse(BaseModel):
    id: str
    agent: str
    action: str
    detail: dict
    request_id: str | None
    created_at: datetime
