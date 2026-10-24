import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.metrics import metrics_response
from app.core.request_context import request_id_context
from app.db.base import Base
from app.db.dependencies import get_db

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)
Db = Annotated[Session, Depends(get_db)]


@router.get("/health")
# Also under /api so it is reachable on Vercel, where only /api/* reaches this service.
@router.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "aria-api"}


@router.get("/metrics")
async def metrics(
    response: Response, x_metrics_token: str | None = Header(default=None)
) -> Response:
    """Prometheus internals. The edge proxy blocks /metrics publicly; when
    ARIA_METRICS_TOKEN is set, direct backend scrapes must also present it."""
    import hmac

    expected = get_settings().aria_metrics_token
    if expected:
        if not x_metrics_token or not hmac.compare_digest(
            x_metrics_token.encode(), expected.encode()
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
            )
    body, content_type = metrics_response()
    response.headers["content-type"] = content_type
    return Response(content=body, media_type=content_type)


@router.get("/ready")
async def readiness(response: Response, db: Db) -> dict:
    checks: dict = {"database": "unavailable", "schema": "unchecked"}
    ok = True
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
        # Empty selects validate required tables and columns without reading
        # learner data. Connectivity alone does not prove a migrated schema.
        for table in Base.metadata.sorted_tables:
            db.execute(select(table).limit(0))
        checks["schema"] = "ok"
    except Exception as exc:
        db.rollback()
        if checks["database"] == "ok":
            checks["schema"] = "unavailable"
        logger.warning(
            "readiness database/schema check failed error_type=%s request_id=%s",
            type(exc).__name__, request_id_context.get(),
        )
        ok = False

    settings = get_settings()
    # Optional providers do not gate core readiness. Configuration is not a
    # successful provider health check and does not include personal keys.
    checks["ai_provider"] = "configured" if settings.groq_api_key else "not_configured"
    checks["capabilities"] = {
        "global_tutor": "configured_unverified" if settings.groq_api_key else "not_configured",
        "speech_to_text": "configured_unverified" if (
            settings.groq_api_key or settings.aria_stt_api_key
        ) else "not_configured",
        "scope": "deployment_configuration_only",
    }
    from app.jobs.scheduler import scheduler_instance

    checks["scheduler"] = "running" if scheduler_instance().running else "idle"
    checks["status"] = "ready" if ok else "degraded"
    response.status_code = 200 if ok else 503
    return checks
