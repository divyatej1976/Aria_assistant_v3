from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.security.csrf import clear_auth_cookies
from app.security.dependencies import CurrentLearner
from app.services.account import reset_learner_data

router = APIRouter(prefix="/api/v1/account", tags=["account"])
Db = Annotated[Session, Depends(get_db)]


@router.delete("/data")
def reset_data(learner: CurrentLearner, response: Response, db: Db) -> dict[str, str]:
    reset_learner_data(db, owner_id=learner.id)
    clear_auth_cookies(response)
    return {"detail": "All learning data deleted and sessions signed out"}
