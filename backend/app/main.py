import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes.account import router as account_router
from app.api.routes.adaptation import router as adaptation_router
from app.api.routes.assessments import router as assessments_router
from app.api.routes.audio import router as audio_router
from app.api.routes.auth import router as auth_router
from app.api.routes.contexts import router as contexts_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.health import router as health_router
from app.api.routes.internal import router as internal_router
from app.api.routes.memory import router as memory_router
from app.api.routes.notes import router as notes_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.orchestration import router as orchestration_router
from app.api.routes.planner import router as planner_router
from app.api.routes.progress import router as progress_router
from app.api.routes.push import router as push_router
from app.api.routes.resources import router as resources_router
from app.api.routes.roadmaps import router as roadmaps_router
from app.api.routes.settings import router as settings_router
from app.api.routes.study import router as study_router
from app.core.config import get_settings
from app.core.errors import AuthorizationError, ValidationError
from app.core.logging import configure_logging
from app.core.metrics import init_sentry
from app.core.request_context import RequestContextMiddleware
from app.jobs.scheduler import shutdown_scheduler, start_scheduler
from app.security.csrf import CSRFMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    # litellm takes ~8-10s to import; pay it at startup, not on the event loop
    # during a learner's first AI request. The bundled cost map avoids a fetch.
    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    import litellm  # noqa: F401

    init_sentry()
    if get_settings().aria_brain_routing:
        from starlette.concurrency import run_in_threadpool

        from app.db.session import engine
        from app.services.brain.checkpoints import setup_postgres_checkpoints

        if engine.dialect.name == "postgresql":
            await run_in_threadpool(setup_postgres_checkpoints, engine.url)
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


settings = get_settings()
app = FastAPI(title="ARIA API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(ValidationError)
async def validation_error_handler(_: Request, exc: ValidationError) -> JSONResponse:
    """Domain validation/not-found failures map to 422 everywhere.

    Routes that do not wrap lookups in try/except previously leaked an
    uncaught ValidationError as HTTP 500; this keeps the documented contract
    (validation failures are 422) consistent across every route.
    """
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(AuthorizationError)
async def authorization_error_handler(_: Request, exc: AuthorizationError) -> JSONResponse:
    """Ownership / permission failures map to 403, never 500."""
    return JSONResponse(status_code=403, content={"detail": str(exc) or "Forbidden"})


@app.middleware("http")
async def no_store_api_responses(request, call_next):
    """Never let browsers heuristically cache API GETs (stale /auth/me after login)."""
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


app.add_middleware(CSRFMiddleware)
if settings.aria_env == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    # Exact allowlist: every non-simple header the frontend (or API
    # consumers) may send. Content-Type (JSON/uploads), Authorization
    # (bearer clients), X-CSRF-Token (cookie double-submit), Idempotency-Key
    # (orchestration/assessment idempotent retries — optional today, but an
    # omission here would fail its preflight the day a client sends it).
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "Idempotency-Key"],
    max_age=600,
)
app.include_router(health_router)
app.include_router(internal_router)
app.include_router(auth_router)
app.include_router(account_router)
app.include_router(contexts_router)
app.include_router(adaptation_router)
app.include_router(memory_router)
app.include_router(notes_router)
app.include_router(progress_router)
app.include_router(planner_router)
app.include_router(notifications_router)
app.include_router(push_router)
app.include_router(orchestration_router)
app.include_router(audio_router)
app.include_router(resources_router)
app.include_router(settings_router)
app.include_router(study_router)
app.include_router(assessments_router)
app.include_router(roadmaps_router)
app.include_router(feedback_router)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"service": "aria-api", "status": "ok"}
