
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.security.csrf import clear_auth_cookies
from app.security.dependencies import CurrentLearner
from app.services.account import reset_learner_data
from app.services.data_management import stream_learner_data

router = APIRouter(prefix="/api/v1/account", tags=["account"])
Db = Annotated[Session, Depends(get_db)]


@router.delete("/data")
def reset_data(learner: CurrentLearner, response: Response, db: Db) -> dict[str, str]:
    reset_learner_data(db, owner_id=learner.id)
    clear_auth_cookies(response)
    # Honest scope: security/audit records and workflow history are retained
    # per the retention policy (see docs/ops/production-runbook.md).
    return {
        "detail": (
            "All learning data deleted and sessions signed out. Security audit "
            "records and workflow history are retained per the retention policy."
        )
    }


@router.get("/export")
def export_data(learner: CurrentLearner, db: Db) -> StreamingResponse:
    """Download a versioned portable export, streaming uncapped snapshot records."""
    return StreamingResponse(
        stream_learner_data(db, owner_id=learner.id),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="aria-data-export.json"'
        },
    )