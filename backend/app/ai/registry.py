"""Provider factory: the single place the app obtains AI providers.

Call sites use `get_llm_provider()` instead of instantiating providers
directly, so governance (budget, metrics, versioning) stays centralized.
Returns None when the provider is not configured so callers can fall back.
"""

from app.core.config import get_settings


def get_llm_provider():
    settings = get_settings()
    if not settings.groq_api_key:
        return None
    from app.ai.providers import LiteLLMGroqProvider

    return LiteLLMGroqProvider(api_key=settings.groq_api_key, model=settings.llm_model)


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
