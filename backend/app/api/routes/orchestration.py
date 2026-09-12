from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.schemas.orchestration import (
    ApprovalResponse,
    AuditResponse,
    TaskResponse,
    WorkflowResponse,
    WorkflowStartResponse,
)
from app.security.dependencies import CurrentLearner
from app.services.idempotency import find as find_idempotency
from app.services.idempotency import record as record_idempotency
from app.services.idempotency import release as release_idempotency
from app.services.idempotency import replayable
from app.services.idempotency import reserve as reserve_idempotency
from app.services.orchestration import (
    decide_approval,
    get_workflow,
    list_audit,
    list_workflows,
    pending_approvals,
    run_workflow,
)

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])
Db = Annotated[Session, Depends(get_db)]


class WorkflowStartRequest(BaseModel):
    payload: dict = Field(default_factory=dict)


def workflow_response(item) -> WorkflowResponse:
    return WorkflowResponse(
        id=str(item.id),
        name=item.name,
        status=item.status,
        current_step=item.current_step,
        error_detail=item.error_detail,
        created_at=item.created_at,
    )


def approval_response(item) -> ApprovalResponse:
    return ApprovalResponse(
        id=str(item.id),
        workflow_id=str(item.workflow_id),
        action=item.action,
        detail=item.detail,
        status=item.status,
    )


def audit_response(item) -> AuditResponse:
    return AuditResponse(
        id=str(item.id),
        agent=item.agent,
        action=item.action,
        detail=item.detail,
        request_id=item.request_id,
        created_at=item.created_at,
    )


def task_response(item) -> TaskResponse:
    return TaskResponse(
        id=str(item.id),
        workflow_id=str(item.workflow_id),
        agent=item.agent,
        status=item.status,
        attempt=item.attempt,
        error_detail=item.error_detail,
        created_at=item.created_at,
    )


def start_response(workflow, approval) -> WorkflowStartResponse:
    return WorkflowStartResponse(
        workflow_id=str(workflow.id),
        status=workflow.status,
        approval=approval_response(approval) if approval else None,
    )


@router.post("/workflows/{name}", response_model=WorkflowStartResponse, status_code=201)
async def start(
    name: str,
    request: WorkflowStartRequest,
    learner: CurrentLearner,
    db: Db,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> WorkflowStartResponse:
    scope = f"workflow:{name}"
    if idempotency_key:
        existing = find_idempotency(
            db, owner_id=learner.id, scope=scope, key=idempotency_key
        )
        if replayable(existing):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=existing.response_status, content=existing.response_json
            )
        state = reserve_idempotency(
            db, owner_id=learner.id, scope=scope, key=idempotency_key
        )
        if state == "in_progress":
            raise HTTPException(
                status_code=409,
                detail=(
                    "A request with this Idempotency-Key is already in progress; "
                    "retry after it completes"
                ),
            )
    try:
        workflow, approval = await run_workflow(
            db, owner_id=learner.id, name=name, payload=request.payload
        )
    except ValidationError as exc:
        if idempotency_key:
            # Release the reservation so the corrected retry is not stuck 409.
            release_idempotency(db, owner_id=learner.id, scope=scope, key=idempotency_key)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response = start_response(workflow, approval)
    if idempotency_key:
        record_idempotency(
            db,
            owner_id=learner.id,
            scope=scope,
            key=idempotency_key,
            status=201,
            response=response.model_dump(mode="json"),
        )
    return response


@router.get("/workflows", response_model=list[WorkflowResponse])
def workflows(learner: CurrentLearner, db: Db) -> list[WorkflowResponse]:
    return [workflow_response(item) for item in list_workflows(db, owner_id=learner.id)]


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def workflow_detail(
    workflow_id: UUID, learner: CurrentLearner, db: Db
) -> WorkflowResponse:
    try:
        item = get_workflow(db, owner_id=learner.id, workflow_id=workflow_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return workflow_response(item)


@router.get("/workflows/{workflow_id}/tasks", response_model=list[TaskResponse])
def workflow_tasks(
    workflow_id: UUID, learner: CurrentLearner, db: Db
) -> list[TaskResponse]:
    from sqlalchemy import select

    from app.db.models import AgentTask

    get_workflow(db, owner_id=learner.id, workflow_id=workflow_id)
    tasks = db.scalars(
        select(AgentTask)
        .where(AgentTask.workflow_id == workflow_id, AgentTask.owner_id == learner.id)
        .order_by(AgentTask.created_at)
    ).all()
    return [task_response(item) for item in tasks]


@router.get("/approvals", response_model=list[ApprovalResponse])
def approvals(learner: CurrentLearner, db: Db) -> list[ApprovalResponse]:
    return [
        approval_response(item) for item in pending_approvals(db, owner_id=learner.id)
    ]


@router.post("/approvals/{approval_id}/approve", response_model=WorkflowStartResponse)
async def approve(approval_id: UUID, learner: CurrentLearner, db: Db) -> WorkflowStartResponse:
    try:
        workflow, approval = await decide_approval(
            db, owner_id=learner.id, approval_id=approval_id, approved=True
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return start_response(workflow, approval)


@router.post("/approvals/{approval_id}/reject", response_model=WorkflowStartResponse)
async def reject(approval_id: UUID, learner: CurrentLearner, db: Db) -> WorkflowStartResponse:
    try:
        workflow, approval = await decide_approval(
            db, owner_id=learner.id, approval_id=approval_id, approved=False
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return start_response(workflow, approval)


@router.get("/audit", response_model=list[AuditResponse])
def audit(learner: CurrentLearner, db: Db) -> list[AuditResponse]:
    return [audit_response(item) for item in list_audit(db, owner_id=learner.id)]
