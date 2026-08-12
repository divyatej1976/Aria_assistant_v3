from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.schemas.learning import ContextCreateRequest, ContextResponse
from app.security.dependencies import CurrentLearner
from app.services.contexts import (
    create_context,
    get_owned_context,
    list_contexts,
)

router = APIRouter(prefix="/api/v1/contexts", tags=["learning-contexts"])
Db = Annotated[Session, Depends(get_db)]


def context_response(context) -> ContextResponse:
    return ContextResponse(
        id=str(context.id),
        title=context.title,
        description=context.description,
        status=context.status,
        configuration=context.configuration,
    )


@router.post("", response_model=ContextResponse, status_code=201)
def create(
    request: ContextCreateRequest, learner: CurrentLearner, db: Db
) -> ContextResponse:
    context = create_context(
        db,
        owner_id=learner.id,
        title=request.title,
        description=request.description,
        goal_title=request.goal_title,
        configuration=request.configuration,
    )
    return context_response(context)


@router.get("", response_model=list[ContextResponse])
def list(learner: CurrentLearner, db: Db) -> list[ContextResponse]:
    return [
        context_response(item) for item in list_contexts(db, owner_id=learner.id)
    ]


@router.get("/{context_id}", response_model=ContextResponse)
def get(context_id: UUID, learner: CurrentLearner, db: Db) -> ContextResponse:
    try:
        context = get_owned_context(
            db, owner_id=learner.id, context_id=context_id
        )
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return context_response(context)
