from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models import Goal, LearningContext
from app.schemas.learning import ContextCreateRequest, ContextResponse
from app.security.dependencies import CurrentLearner

router = APIRouter(prefix="/api/v1/contexts", tags=["learning-contexts"])
Db = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ContextResponse, status_code=201)
def create_context(
    request: ContextCreateRequest, learner: CurrentLearner, db: Db
) -> ContextResponse:
    goal = None
    if request.goal_title:
        goal = Goal(owner_id=learner.id, title=request.goal_title)
        db.add(goal)
        db.flush()
    context = LearningContext(
        owner_id=learner.id,
        goal_id=goal.id if goal else None,
        title=request.title,
        description=request.description,
        configuration=request.configuration,
    )
    db.add(context)
    db.commit()
    db.refresh(context)
    return ContextResponse(
        id=str(context.id),
        title=context.title,
        description=context.description,
        status=context.status,
        configuration=context.configuration,
    )


@router.get("", response_model=list[ContextResponse])
def list_contexts(learner: CurrentLearner, db: Db) -> list[ContextResponse]:
    contexts = db.scalars(
        select(LearningContext)
        .where(LearningContext.owner_id == learner.id)
        .order_by(LearningContext.created_at)
    ).all()
    return [
        ContextResponse(
            id=str(item.id),
            title=item.title,
            description=item.description,
            status=item.status,
            configuration=item.configuration,
        )
        for item in contexts
    ]


@router.get("/{context_id}", response_model=ContextResponse)
def get_context(context_id: UUID, learner: CurrentLearner, db: Db) -> ContextResponse:
    context = db.scalar(
        select(LearningContext).where(
            LearningContext.id == context_id, LearningContext.owner_id == learner.id
        )
    )
    if context is None:
        raise HTTPException(status_code=404, detail="Learning context not found")
    return ContextResponse(
        id=str(context.id),
        title=context.title,
        description=context.description,
        status=context.status,
        configuration=context.configuration,
    )
