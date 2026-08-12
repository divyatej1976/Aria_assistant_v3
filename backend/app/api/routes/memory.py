from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.memory import MemorySummary, PreferenceItem, PreferenceUpsertRequest
from app.security.dependencies import CurrentLearner
from app.services.memory import (
    delete_preference,
    list_preferences,
    memory_summary,
    upsert_preference,
)

router = APIRouter(prefix="/api/v1", tags=["memory"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/me/preferences", response_model=list[PreferenceItem])
def get_preferences(learner: CurrentLearner, db: Db) -> list[PreferenceItem]:
    return [
        PreferenceItem(key=preference.key, value=preference.value)
        for preference in list_preferences(db, owner_id=learner.id)
    ]


@router.put("/me/preferences", response_model=PreferenceItem)
def put_preference(
    request: PreferenceUpsertRequest, learner: CurrentLearner, db: Db
) -> PreferenceItem:
    preference = upsert_preference(
        db, owner_id=learner.id, key=request.key, value=request.value
    )
    return PreferenceItem(key=preference.key, value=preference.value)


@router.delete("/me/preferences/{key}")
def remove_preference(key: str, learner: CurrentLearner, db: Db) -> dict[str, object]:
    if not delete_preference(db, owner_id=learner.id, key=key):
        raise HTTPException(status_code=404, detail="Preference not found")
    return {"deleted": True}


@router.get("/memory", response_model=MemorySummary)
def summary(learner: CurrentLearner, db: Db) -> MemorySummary:
    return MemorySummary(**memory_summary(db, owner_id=learner.id))
