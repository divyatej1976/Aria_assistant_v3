"""Runtime secret resolution with fail-fast production guardrails."""

from app.core.config import get_settings

DEV_FALLBACK_SECRET = "development-only-change-me"


def get_session_secret() -> str:
    """Return the session signing secret, refusing to fall back in production.

    `ARIA_SESSION_SECRET` takes precedence, then `SUPABASE_JWT_SECRET` for
    backwards compatibility. Outside production a well-known development value
    is used so local runs and tests work without configuration; in production
    a missing secret is a hard startup/request error instead of a silent risk.
    """
    settings = get_settings()
    secret = settings.aria_session_secret or settings.supabase_jwt_secret
    if secret:
        return secret
    if settings.aria_env != "production":
        return DEV_FALLBACK_SECRET
    raise RuntimeError(
        "ARIA_SESSION_SECRET (or legacy SUPABASE_JWT_SECRET) must be set when ARIA_ENV=production"
    )
