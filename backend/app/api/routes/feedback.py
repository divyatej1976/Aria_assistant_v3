import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models import Feedback
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.security.dependencies import CurrentLearner
from app.security.rate_limit import rate_limited

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])
Db = Annotated[Session, Depends(get_db)]
logger = logging.getLogger(__name__)


@router.post("", response_model=FeedbackResponse, status_code=201,
             dependencies=[Depends(rate_limited(20, 60))])
def send_feedback(request: FeedbackRequest, learner: CurrentLearner, db: Db) -> FeedbackResponse:
    item = Feedback(owner_id=learner.id, **request.model_dump())
    db.add(item)
    db.commit()
    logger.info("feedback received kind=%s rating=%s reason=%s", item.kind, item.rating, item.reason)
    if item.kind == "report" or item.rating == "down":
        # With Sentry on, each problem report or thumbs-down raises an alert linked to the user.
        try:
            import sentry_sdk

            with sentry_sdk.new_scope() as scope:
                scope.set_user({"id": str(learner.id)})
                scope.set_context("feedback", {"id": str(item.id), "kind": item.kind, "reason": item.reason,
                                               "page": item.page, "answer_id": str(item.answer_id or "")})
                sentry_sdk.capture_message(f"User feedback ({item.kind}): {(item.message or item.reason or '')[:120]}",
                                           level="warning")
        except Exception:  # noqa: BLE001 - feedback is saved either way
            pass
    return FeedbackResponse(id=str(item.id), status=item.status)
