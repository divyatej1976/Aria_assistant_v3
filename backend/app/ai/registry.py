"""Provider factory: the single place the app obtains AI providers.

Call sites with a request context should prefer `get_llm_provider_for_owner`
so a learner-supplied key takes precedence over the global key:
learner key -> global GROQ_API_KEY -> deterministic fallback (None).
Plain `get_llm_provider()` remains the global-only factory.
Returns None when no provider is configured so callers can fall back.
"""

from app.core.config import get_settings


def main_route() -> str:
    return (getattr(get_settings(), "aria_llm_provider", None) or "groq").strip().lower()


def provider_key(route: str) -> str | None:
    """The key for a provider: ARIA_LLM_API_KEY for the main one, else that provider's own key."""
    settings = get_settings()
    own = {"groq": settings.groq_api_key, "openai": getattr(settings, "openai_api_key", None),
           "gemini": getattr(settings, "gemini_api_key", None)}.get(route)
    if route == main_route():
        return getattr(settings, "aria_llm_api_key", None) or own
    return own


def fallback_target(route: str) -> tuple[str, str, str] | None:
    """(route, key, model) of the backup provider for `route`, or None."""
    settings = get_settings()
    choice = (getattr(settings, "aria_llm_fallback_provider", "auto") or "auto").strip().lower()
    if choice == "none":
        return None
    backup = {"openai": "gemini", "gemini": "openai", "groq": "openai"}.get(route) if choice == "auto" else choice
    if not backup or backup == route:
        return None
    key = provider_key(backup)
    model = {"openai": getattr(settings, "aria_openai_fallback_model", "gpt-5-mini"),
             "gemini": getattr(settings, "aria_gemini_fallback_model", "gemini-2.5-flash")}.get(backup)
    return (backup, key, model) if key and model else None


def get_llm_provider():
    settings = get_settings()
    route = main_route()
    api_key = provider_key(route)
    if not api_key:
        return None
    from app.ai.providers import LiteLLMGroqProvider

    return LiteLLMGroqProvider(api_key=api_key, model=settings.llm_model, route=route,
                               fallback=fallback_target(route))


def get_llm_provider_for_owner(db, *, owner_id):
    """Owner-aware factory. Falls back to the global provider on any error."""
    try:
        from app.services.llm_keys import get_llm_provider_for_owner as _for_owner

        return _for_owner(db, owner_id=owner_id)
    except Exception:
        return get_llm_provider()


def get_embedding_provider():
    settings = get_settings()
    if settings.aria_embedding_api_key:
        from app.ai.providers import CloudEmbeddingProvider

        return CloudEmbeddingProvider(
            api_key=settings.aria_embedding_api_key,
            model=settings.aria_embedding_model,
            base_url=settings.aria_embedding_base_url,
            dimension=settings.aria_embedding_dim,
        )
    from app.ai.providers import DeterministicEmbeddingProvider

    return DeterministicEmbeddingProvider(dimension=settings.aria_embedding_dim)
