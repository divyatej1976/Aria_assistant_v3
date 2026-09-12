from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.schemas.settings import LLMKeyStatusResponse, LLMKeyUpsertRequest
from app.security.dependencies import CurrentLearner
from app.services.llm_keys import delete_key, get_status, set_key

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/llm-key", response_model=LLMKeyStatusResponse)
def llm_key_status(learner: CurrentLearner, db: Db) -> LLMKeyStatusResponse:
    return LLMKeyStatusResponse(**get_status(db, owner_id=learner.id))


@router.post("/llm-key", response_model=LLMKeyStatusResponse, status_code=201)
def llm_key_upsert(
    request: LLMKeyUpsertRequest, learner: CurrentLearner, db: Db
) -> LLMKeyStatusResponse:
    try:
        row = set_key(db, owner_id=learner.id, key=request.key, model=request.model)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return LLMKeyStatusResponse(
        configured=True, provider=row.provider, model=row.model, hint=row.key_hint
    )


@router.delete("/llm-key")
def llm_key_delete(learner: CurrentLearner, db: Db) -> dict[str, object]:
    if not delete_key(db, owner_id=learner.id):
        raise HTTPException(status_code=404, detail="No personal LLM key is configured")
    # Verify deletion: the row must be gone in the same request scope.
    if get_status(db, owner_id=learner.id)["configured"]:
        raise HTTPException(status_code=500, detail="Failed to delete LLM key")
    return {"deleted": True}
