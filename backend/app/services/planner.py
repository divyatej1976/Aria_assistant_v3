"""Planner: exam deadlines, planned tasks, and missed-work detection."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.models import Deadline, PlannedTask, Resource
from app.services.contexts import get_owned_context, get_owned_related
from app.services.progress import learner_timezone, record_activity


def _now() -> datetime:
    return datetime.now(UTC)


def _coerce_aware(value: datetime, *, tz) -> datetime:
    aware = value if value.tzinfo is not None else value.replace(tzinfo=tz)
    return aware.astimezone(UTC)


def get_owned_deadline(db: Session, *, owner_id: UUID, deadline_id: UUID) -> Deadline:
    deadline = db.scalar(
        select(Deadline).where(
            Deadline.id == deadline_id, Deadline.owner_id == owner_id
        )
    )
    if deadline is None:
        raise ValidationError("Deadline not found")
    return deadline


def create_deadline(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    title: str,
    due_at: datetime,
    syllabus_resource_id: UUID | None,
    reminder_days_before: int,
) -> Deadline:
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    if syllabus_resource_id is not None:
        get_owned_related(db, Resource, owner_id=owner_id, context_id=context_id,
                          related_id=syllabus_resource_id, label="Syllabus resource")
    tz = learner_timezone(db, owner_id=owner_id)
    deadline = Deadline(
        owner_id=owner_id,
        context_id=context_id,
        title=title,
        due_at=_coerce_aware(due_at, tz=tz),
        syllabus_resource_id=syllabus_resource_id,
        reminder_days_before=reminder_days_before,
    )
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline


def list_deadlines(db: Session, *, owner_id: UUID, context_id: UUID) -> list[Deadline]:
    return list(
        db.scalars(
            select(Deadline)
            .where(Deadline.owner_id == owner_id, Deadline.context_id == context_id)
            .order_by(Deadline.due_at)
        )
    )


def upcoming_deadlines(
    db: Session, *, owner_id: UUID, days: int = 14, context_id: UUID | None = None
) -> list[Deadline]:
    now = _now()
    window_end = now + timedelta(days=days)
    query = select(Deadline).where(
        Deadline.owner_id == owner_id,
        Deadline.status == "ACTIVE",
        Deadline.due_at >= now,
        Deadline.due_at <= window_end,
    )
    if context_id is not None:
        query = query.where(Deadline.context_id == context_id)
    return list(
        db.scalars(
            query.order_by(Deadline.due_at)
        )
    )


def complete_deadline(db: Session, *, owner_id: UUID, deadline_id: UUID) -> Deadline:
    deadline = get_owned_deadline(db, owner_id=owner_id, deadline_id=deadline_id)
    deadline.status = "DONE"
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline


def delete_deadline(db: Session, *, owner_id: UUID, deadline_id: UUID) -> None:
    deadline = get_owned_deadline(db, owner_id=owner_id, deadline_id=deadline_id)
    db.execute(
        update(PlannedTask)
        .where(PlannedTask.deadline_id == deadline.id, PlannedTask.owner_id == owner_id)
        .values(deadline_id=None)
    )
    db.delete(deadline)
    db.commit()


def get_owned_task(db: Session, *, owner_id: UUID, task_id: UUID) -> PlannedTask:
    task = db.scalar(
        select(PlannedTask).where(PlannedTask.id == task_id, PlannedTask.owner_id == owner_id)
    )
    if task is None:
        raise ValidationError("Planned task not found")
    return task


def create_task(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    title: str,
    deadline_id: UUID | None,
    due_at: datetime | None,
) -> PlannedTask:
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    if deadline_id is not None:
        get_owned_related(db, Deadline, owner_id=owner_id, context_id=context_id,
                          related_id=deadline_id, label="Deadline")
    if due_at is not None and due_at.tzinfo is None:
        tz = learner_timezone(db, owner_id=owner_id)
        due_at = _coerce_aware(due_at, tz=tz)
    task = PlannedTask(
        owner_id=owner_id,
        context_id=context_id,
        title=title,
        deadline_id=deadline_id,
        due_at=due_at,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session, *, owner_id: UUID, context_id: UUID) -> list[PlannedTask]:
    return list(
        db.scalars(
            select(PlannedTask)
            .where(PlannedTask.owner_id == owner_id, PlannedTask.context_id == context_id)
            .order_by(PlannedTask.created_at.desc())
        )
    )


def complete_task(db: Session, *, owner_id: UUID, task_id: UUID) -> PlannedTask:
    task = get_owned_task(db, owner_id=owner_id, task_id=task_id)
    task.status = "DONE"
    task.completed_at = _now()
    db.add(task)
    db.commit()
    db.refresh(task)
    record_activity(
        db, owner_id=owner_id, activity_type="planned_task", source_id=task.id
    )
    return task


def delete_task(db: Session, *, owner_id: UUID, task_id: UUID) -> None:
    task = get_owned_task(db, owner_id=owner_id, task_id=task_id)
    db.delete(task)
    db.commit()


def missed_tasks(db: Session, *, owner_id: UUID, context_id: UUID | None = None) -> list[PlannedTask]:
    query = select(PlannedTask).where(
        PlannedTask.owner_id == owner_id,
        PlannedTask.status == "PENDING",
        PlannedTask.due_at.is_not(None),
        PlannedTask.due_at < _now(),
    )
    if context_id is not None:
        query = query.where(PlannedTask.context_id == context_id)
    return list(
        db.scalars(
            query.order_by(PlannedTask.due_at)
        )
    )
