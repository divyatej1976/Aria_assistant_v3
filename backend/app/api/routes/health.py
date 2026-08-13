from fastapi import APIRouter, Response
from sqlalchemy import text

from app.core.config import get_settings
from app.core.metrics import metrics_response
from app.db.session import engine

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "aria-api"}


@router.get("/metrics")
async def metrics(response: Response) -> Response:
    body, content_type = metrics_response()
    response.headers["content-type"] = content_type
    return Response(content=body, media_type=content_type)


@router.get("/ready")
async def readiness(response: Response) -> dict[str, str]:
    checks: dict[str, str] = {}
    ok = True
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - probe reports any failure
        checks["database"] = f"error: {exc}"
        ok = False

    settings = get_settings()
    checks["ai_provider"] = "configured" if settings.groq_api_key else "not_configured"

    from app.jobs.scheduler import scheduler_instance

    checks["scheduler"] = "running" if scheduler_instance().running else "idle"

    checks["status"] = "ready" if ok else "degraded"
    response.status_code = 200 if ok else 503
    return checks
