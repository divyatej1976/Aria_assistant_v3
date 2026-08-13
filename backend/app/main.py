from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.account import router as account_router
from app.api.routes.adaptation import router as adaptation_router
from app.api.routes.assessments import router as assessments_router
from app.api.routes.audio import router as audio_router
from app.api.routes.auth import router as auth_router
from app.api.routes.contexts import router as contexts_router
from app.api.routes.health import router as health_router
from app.api.routes.memory import router as memory_router
from app.api.routes.notes import router as notes_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.orchestration import router as orchestration_router
from app.api.routes.planner import router as planner_router
from app.api.routes.progress import router as progress_router
from app.api.routes.resources import router as resources_router
from app.api.routes.study import router as study_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.request_context import RequestContextMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    yield


settings = get_settings()
app = FastAPI(title="ARIA API", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(account_router)
app.include_router(contexts_router)
app.include_router(adaptation_router)
app.include_router(memory_router)
app.include_router(notes_router)
app.include_router(progress_router)
app.include_router(planner_router)
app.include_router(notifications_router)
app.include_router(orchestration_router)
app.include_router(audio_router)
app.include_router(resources_router)
app.include_router(study_router)
app.include_router(assessments_router)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"service": "aria-api", "status": "ok"}
