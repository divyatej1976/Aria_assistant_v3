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


class TTSProvider(Protocol):
    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        """Synthesize speech. Returns (audio bytes, content type, duration seconds)."""


class STTProvider(Protocol):
    def transcribe(self, *, audio: bytes, content_type: str) -> str:
        """Transcribe audio to text."""


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


class CloudTTSProvider:
    def __init__(self, *, api_key: str, model: str = "tts-1", voice: str = "nova") -> None:
        self.api_key = api_key
        self.model = model
        self.voice = voice

    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        import httpx

        response = httpx.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "voice": self.voice, "input": text[:4000]},
            timeout=60,
        )
        response.raise_for_status()
        return response.content, "audio/mpeg", max(1, len(text) // 15)


class LocalTTSProvider:
    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        import os
        import tempfile

        try:
            import pyttsx3
        except ImportError as exc:
            raise RuntimeError(
                "Local text-to-speech requires the pyttsx3 dependency"
            ) from exc
        engine = pyttsx3.init()
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            engine.save_to_file(text, path)
            engine.runAndWait()
            with open(path, "rb") as handle:
                data = handle.read()
        finally:
            if os.path.exists(path):
                os.remove(path)
        if not data:
            raise RuntimeError("No audio was produced")
        return data, "audio/wav", max(1, len(text) // 15)


class CloudSTTProvider:
    def __init__(self, *, api_key: str, model: str = "whisper-1") -> None:
        self.api_key = api_key
        self.model = model

    def transcribe(self, *, audio: bytes, content_type: str) -> str:
        import httpx

        response = httpx.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            files={"file": ("audio", audio, content_type)},
            data={"model": self.model},
            timeout=60,
        )
        response.raise_for_status()
        return response.json().get("text", "").strip()


class LiteLLMGroqProvider:
    def __init__(self, *, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _log_call(
        self,
        *,
        kind: str,
        started: float,
        response: object,
        prompt_version: str | None = None,
    ) -> None:
        duration_ms = int((time.monotonic() - started) * 1000)
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
        logger.info(
            "ai_call kind=%s model=%s prompt_version=%s duration_ms=%d "
            "prompt_tokens=%s completion_tokens=%s",
            kind,
            self.model,
            prompt_version,
            duration_ms,
            prompt_tokens,
            completion_tokens,
        )
        try:
            from app.ai.budget import record_usage
            from app.core.metrics import observe_ai_call

            if prompt_tokens is not None and completion_tokens is not None:
                record_usage(
                    model=self.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
            observe_ai_call(
                kind=kind,
                model=self.model,
                prompt_version=prompt_version,
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        except Exception:
            logger.debug("ai metrics update failed", exc_info=True)

    async def generate_text(
        self, *, system: str, user: str, prompt_version: str | None = None
    ) -> str:
        from litellm import acompletion

        from app.ai.budget import assert_within_budget

        assert_within_budget()
        started = time.monotonic()
        response = await acompletion(
            model=f"groq/{self.model}",
            api_key=self.api_key,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        self._log_call(
            kind="generate_text", started=started, response=response, prompt_version=prompt_version
        )
        return response.choices[0].message.content or ""

    async def generate_structured(
        self, *, prompt: str, schema: type, prompt_version: str | None = None
    ) -> object:
        from litellm import acompletion

        from app.ai.budget import assert_within_budget

        assert_within_budget()
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
        self._log_call(
            kind="generate_structured",
            started=started,
            response=response,
            prompt_version=prompt_version,
        )
        text = response.choices[0].message.content or ""
        return schema.model_validate_json(text)
