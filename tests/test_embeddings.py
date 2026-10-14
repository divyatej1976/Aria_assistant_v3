"""Phase 12.8 vector retrieval: embedding factory, cloud provider, dimension."""

import asyncio

from app.ai.providers import CloudEmbeddingProvider, DeterministicEmbeddingProvider
from app.services.study import semantic_scoring_available


def test_embedding_factory_returns_deterministic_without_key(monkeypatch) -> None:
    import app.ai.registry as registry

    class Settings:
        aria_embedding_api_key = None
        aria_embedding_model = "text-embedding-3-small"
        aria_embedding_base_url = None
        aria_embedding_dim = 768

    monkeypatch.setattr(registry, "get_settings", lambda: Settings())
    provider = registry.get_embedding_provider()
    assert isinstance(provider, DeterministicEmbeddingProvider)
    assert provider.dimension == 768


def test_embedding_factory_returns_cloud_with_key(monkeypatch) -> None:
    import app.ai.registry as registry

    class Settings:
        aria_embedding_api_key = "key"
        aria_embedding_model = "text-embedding-3-small"
        aria_embedding_base_url = None
        aria_embedding_dim = 768

    monkeypatch.setattr(registry, "get_settings", lambda: Settings())
    provider = registry.get_embedding_provider()
    assert isinstance(provider, CloudEmbeddingProvider)
    assert provider.dimension == 768


def test_deterministic_embeddings_match_configured_dim() -> None:
    provider = DeterministicEmbeddingProvider(dimension=768)
    vectors = asyncio.run(provider.embed(["two phase locking", "locks"]))
    assert len(vectors) == 2
    assert all(len(vector) == 768 for vector in vectors)
    magnitude = sum(value * value for value in vectors[0]) ** 0.5
    assert abs(magnitude - 1.0) < 1e-6


def test_cloud_embedding_provider_parses_response(monkeypatch) -> None:
    import app.ai.providers as providers

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {"index": 0, "embedding": [0.25] * 768},
                    {"index": 1, "embedding": [0.5] * 768},
                ]
            }

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeClient)
    provider = CloudEmbeddingProvider(
        api_key="key", model="text-embedding-3-small", base_url=None, dimension=768
    )
    vectors = asyncio.run(provider.embed(["a", "b"]))
    assert len(vectors) == 2
    assert all(len(vector) == 768 for vector in vectors)
    assert vectors[0][0] == 0.25


def test_semantic_scoring_available_true_for_cloud_provider() -> None:
    assert semantic_scoring_available(
        CloudEmbeddingProvider(api_key="k", model="m", base_url=None, dimension=768)
    ) is True
    assert semantic_scoring_available(DeterministicEmbeddingProvider()) is False


def test_cloud_embedding_rejects_dimension_mismatch(monkeypatch) -> None:
    """Embeddings-flag gate: a provider returning the wrong dimension must fail
    loudly instead of silently corrupting pgvector retrieval."""
    import pytest

    import app.ai.providers as providers

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"index": 0, "embedding": [0.25] * 1536}]}

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(providers.httpx, "AsyncClient", FakeClient)
    provider = CloudEmbeddingProvider(
        api_key="key", model="text-embedding-3-small", base_url=None, dimension=768
    )
    with pytest.raises(ValueError, match="dimension"):
        asyncio.run(provider.embed(["a"]))
