from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "aria-api"}


@router.get("/ready")
async def readiness() -> dict[str, str]:
    # Database/provider probes will be added once runtime dependencies are wired.
    return {"status": "ready", "service": "aria-api"}
