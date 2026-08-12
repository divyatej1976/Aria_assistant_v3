import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    resource_id: str
    content: str
    source_title: str
    score: float


class LLMProvider(Protocol):
    async def generate_text(self, *, system: str, user: str) -> str:
        """Generate a learner-facing response."""

    async def generate_structured(self, *, prompt: str, schema: type) -> object:
        """Generate validated structured output through the configured provider."""


class EmbeddingProvider(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Create embeddings without exposing provider-specific SDK types."""


class StorageProvider(Protocol):
    async def create_upload_url(self, *, key: str, content_type: str) -> str:
        """Create a scoped upload URL."""


class EmailProvider(Protocol):
    async def send(self, *, recipient: str, subject: str, body: str) -> None:
        """Send transactional email through a replaceable provider."""


class NotificationProvider(Protocol):
    async def send(self, *, recipient_id: str, title: str, body: str) -> None:
        """Send a notification without coupling domain logic to a vendor."""


class DeterministicEmbeddingProvider:
    """Small local embedding fallback for development and deterministic tests."""

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * 32
            for token in text.lower().split():
                vector[hash(token) % len(vector)] += 1.0
            magnitude = sum(value * value for value in vector) ** 0.5 or 1.0
            vectors.append([value / magnitude for value in vector])
        return vectors


class LiteLLMGroqProvider:
    def __init__(self, *, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _log_call(self, *, kind: str, started: float, response: object) -> None:
        duration_ms = int((time.monotonic() - started) * 1000)
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
        logger.info(
            "ai_call kind=%s model=%s duration_ms=%d prompt_tokens=%s completion_tokens=%s",
            kind,
            self.model,
            duration_ms,
            prompt_tokens,
            completion_tokens,
        )

    async def generate_text(self, *, system: str, user: str) -> str:
        from litellm import acompletion

        started = time.monotonic()
        response = await acompletion(
            model=f"groq/{self.model}",
            api_key=self.api_key,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        self._log_call(kind="generate_text", started=started, response=response)
        return response.choices[0].message.content or ""

    async def generate_structured(self, *, prompt: str, schema: type) -> object:
        from litellm import acompletion

        started = time.monotonic()
        response = await acompletion(
            model=f"groq/{self.model}",
            api_key=self.api_key,
            messages=[
                {"role": "system", "content": "You produce only valid JSON matching the schema."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        self._log_call(kind="generate_structured", started=started, response=response)
        text = response.choices[0].message.content or ""
        return schema.model_validate_json(text)
