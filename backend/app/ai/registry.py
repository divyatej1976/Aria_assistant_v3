"""Provider factory: the single place the app obtains AI providers.

Call sites with a request context should prefer `get_llm_provider_for_owner`
so a learner-supplied key takes precedence over the global key:
learner key -> global GROQ_API_KEY -> deterministic fallback (None).
Plain `get_llm_provider()` remains the global-only factory.
Returns None when no provider is configured so callers can fall back.
"""

from app.core.config import get_settings


def get_llm_provider():
    settings = get_settings()
    route = (getattr(settings, "aria_llm_provider", None) or "groq").strip().lower()
    api_key = getattr(settings, "aria_llm_api_key", None) or (settings.groq_api_key if route == "groq" else None)
    if not api_key:
        return None
    from app.ai.providers import LiteLLMGroqProvider

    return LiteLLMGroqProvider(api_key=api_key, model=settings.llm_model, route=route)


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
