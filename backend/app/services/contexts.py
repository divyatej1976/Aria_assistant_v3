"""Learning contexts: persistence and ownership."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.models import Goal, LearningContext


def get_owned_context(db: Session, *, owner_id: UUID, context_id: UUID) -> LearningContext:
    context = db.scalar(
        select(LearningContext).where(
            LearningContext.id == context_id, LearningContext.owner_id == owner_id
        )
    )
    if context is None:
        raise ValidationError("Learning context not found")
    return context


def create_context(
    db: Session,
    *,
    owner_id: UUID,
    title: str,
    description: str | None,
    goal_title: str | None = None,
    configuration: dict | None = None,
) -> LearningContext:
    goal = None
    if goal_title:
        goal = Goal(owner_id=owner_id, title=goal_title)
        db.add(goal)
        db.flush()
    context = LearningContext(
        owner_id=owner_id,
        goal_id=goal.id if goal else None,
        title=title,
        description=description,
        configuration=configuration or {},
    )
    db.add(context)
    db.commit()
    db.refresh(context)
    return context


def list_contexts(db: Session, *, owner_id: UUID) -> list[LearningContext]:
    return list(
        db.scalars(
            select(LearningContext)
            .where(LearningContext.owner_id == owner_id)
            .order_by(LearningContext.created_at)
        )
    )
