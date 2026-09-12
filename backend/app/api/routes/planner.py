from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.schemas.planner import (
    DeadlineCreateRequest,
    DeadlineResponse,
    ReminderCheckResponse,
    TaskCreateRequest,
    TaskResponse,
)
from app.security.dependencies import CurrentLearner
from app.services.contexts import get_owned_context
from app.services.notifications import check_reminders
from app.services.planner import (
    complete_deadline,
    complete_task,
    create_deadline,
    create_task,
    delete_deadline,
    delete_task,
    list_deadlines,
    list_tasks,
    missed_tasks,
    upcoming_deadlines,
)

router = APIRouter(prefix="/api/v1/planner", tags=["planner"])
Db = Annotated[Session, Depends(get_db)]


def ensure_context(db: Session, *, context_id: UUID, owner_id: UUID) -> None:
    try:
        get_owned_context(db, owner_id=owner_id, context_id=context_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def deadline_response(deadline) -> DeadlineResponse:
    return DeadlineResponse(
        id=str(deadline.id),
        context_id=str(deadline.context_id),
        title=deadline.title,
        due_at=deadline.due_at,
        syllabus_resource_id=str(deadline.syllabus_resource_id)
        if deadline.syllabus_resource_id
        else None,
        reminder_days_before=deadline.reminder_days_before,
        reminder_sent_days_before=deadline.reminder_sent_days_before,
        status=deadline.status,
    )


def task_response(task) -> TaskResponse:
    return TaskResponse(
        id=str(task.id),
        context_id=str(task.context_id),
        deadline_id=str(task.deadline_id) if task.deadline_id else None,
        title=task.title,
        due_at=task.due_at,
        status=task.status,
        completed_at=task.completed_at,
    )


@router.post("/deadlines", response_model=DeadlineResponse, status_code=201)
def create_deadline_route(
    request: DeadlineCreateRequest, learner: CurrentLearner, db: Db
) -> DeadlineResponse:
    ensure_context(db, context_id=request.context_id, owner_id=learner.id)
    try:
        deadline = create_deadline(
            db,
            owner_id=learner.id,
            context_id=request.context_id,
            title=request.title,
            due_at=request.due_at,
            syllabus_resource_id=request.syllabus_resource_id,
            reminder_days_before=request.reminder_days_before,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return deadline_response(deadline)


@router.get("/deadlines", response_model=list[DeadlineResponse])
def list_deadlines_route(
    context_id: UUID, learner: CurrentLearner, db: Db
) -> list[DeadlineResponse]:
    ensure_context(db, context_id=context_id, owner_id=learner.id)
    return [
        deadline_response(item)
        for item in list_deadlines(db, owner_id=learner.id, context_id=context_id)
    ]


@router.get("/upcoming", response_model=list[DeadlineResponse])
def upcoming(
    learner: CurrentLearner, db: Db, days: int = 14, context_id: UUID | None = None
) -> list[DeadlineResponse]:
    return [
        deadline_response(item)
        for item in upcoming_deadlines(
            db, owner_id=learner.id, days=days, context_id=context_id
        )
    ]


@router.post("/deadlines/{deadline_id}/complete", response_model=DeadlineResponse)
def complete_deadline_route(
    deadline_id: UUID, learner: CurrentLearner, db: Db
) -> DeadlineResponse:
    try:
        deadline = complete_deadline(db, owner_id=learner.id, deadline_id=deadline_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return deadline_response(deadline)


@router.delete("/deadlines/{deadline_id}")
def delete_deadline_route(
    deadline_id: UUID, learner: CurrentLearner, db: Db
) -> dict[str, object]:
    try:
        delete_deadline(db, owner_id=learner.id, deadline_id=deadline_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": True}


@router.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task_route(
    request: TaskCreateRequest, learner: CurrentLearner, db: Db
) -> TaskResponse:
    ensure_context(db, context_id=request.context_id, owner_id=learner.id)
    try:
        task = create_task(
            db,
            owner_id=learner.id,
            context_id=request.context_id,
            title=request.title,
            deadline_id=request.deadline_id,
            due_at=request.due_at,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return task_response(task)


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks_route(
    context_id: UUID, learner: CurrentLearner, db: Db
) -> list[TaskResponse]:
    ensure_context(db, context_id=context_id, owner_id=learner.id)
    return [
        task_response(item)
        for item in list_tasks(db, owner_id=learner.id, context_id=context_id)
    ]


@router.get("/missed", response_model=list[TaskResponse])
def missed(learner: CurrentLearner, db: Db, context_id: UUID | None = None) -> list[TaskResponse]:
    return [
        task_response(item)
        for item in missed_tasks(db, owner_id=learner.id, context_id=context_id)
    ]


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_task_route(
    task_id: UUID, learner: CurrentLearner, db: Db
) -> TaskResponse:
    try:
        task = complete_task(db, owner_id=learner.id, task_id=task_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return task_response(task)


@router.delete("/tasks/{task_id}")
def delete_task_route(
    task_id: UUID, learner: CurrentLearner, db: Db
) -> dict[str, object]:
    try:
        delete_task(db, owner_id=learner.id, task_id=task_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": True}


@router.post("/reminders/check", response_model=ReminderCheckResponse)
def reminders_check(learner: CurrentLearner, db: Db) -> ReminderCheckResponse:
    return ReminderCheckResponse(**check_reminders(db, owner_id=learner.id))
