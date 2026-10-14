import hashlib
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.ai.speech_audio import assemble_wav, speech_segments

logger = logging.getLogger(__name__)


def estimate_tokens(chars: int, *, margin: float = 1.25) -> int:
    """Heuristic token estimate for accounting when usage metadata is absent.

    Ceiling division (~4 chars/token) plus a 25% safety margin, floored at 1.
    This is a heuristic, not a guaranteed upper bound: real tokenizers can
    exceed one token per four characters (short text, code, symbols, URLs,
    non-English or adversarial input), so estimated spend may still
    undercount. For a hard spending cap, prefer provider-reported usage or a
    pre-request reservation; only use this fallback to avoid zero-accounting.
    Callers should prefer reported usage whenever the provider supplies it.
    """
    import math

    return max(1, math.ceil(max(0, chars) / 4 * margin))


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
    """Small local embedding fallback for development and deterministic tests.

    Produces `aria_embedding_dim`-dimensional unit vectors so the dimension is
    stable whether or not a cloud embedding provider is configured.
    These vectors are hash-based (SHA256) and NOT semantically meaningful;
    they are intentionally excluded from semantic/pgvector retrieval
    (see `study.semantic_scoring_available`).
    """

    def __init__(self, *, dimension: int | None = None) -> None:
        from app.core.config import get_settings

        self.dimension = dimension or get_settings().aria_embedding_dim

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimension
            for token in text.lower().split():
                digest = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:8], "big")
                vector[digest % self.dimension] += 1.0
            magnitude = sum(value * value for value in vector) ** 0.5 or 1.0
            normalized = [value / magnitude for value in vector]
            if len(normalized) != self.dimension:
                msg = f"Embedding dimension {len(normalized)} != expected {self.dimension}"
                raise ValueError(msg)
            vectors.append(normalized)
        return vectors


class CloudEmbeddingProvider:
    """OpenAI-compatible embeddings endpoint (configurable base URL/model)."""

    def __init__(
        self, *, api_key: str, model: str, base_url: str | None, dimension: int
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.dimension = dimension

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        payload: dict = {"model": self.model, "input": list(texts)}
        if self.model.startswith("text-embedding"):
            payload["dimensions"] = self.dimension
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            data = response.json()
        ordered = sorted(data["data"], key=lambda item: item["index"])
        # Strict rejection: provider must return exactly `dimension` floats.
        # Truncating a 1536-d response to 768 would silently corrupt retrieval.
        for item in ordered:
            raw = item["embedding"]
            if len(raw) != self.dimension:
                msg = f"Embedding dimension {len(raw)} != expected {self.dimension} (model {self.model})"
                raise ValueError(msg)
        return [item["embedding"] for item in ordered]


class CloudTTSProvider:
    def __init__(self, *, api_key: str, model: str = "tts-1", voice: str = "nova") -> None:
        self.api_key = api_key
        self.model = model
        self.voice = voice

    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        parts: list[bytes] = []
        for segment in speech_segments(text):
            response = httpx.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model, "voice": self.voice,
                    "input": segment, "response_format": "wav",
                },
                timeout=60,
            )
            response.raise_for_status()
            parts.append(response.content)
        data, duration = assemble_wav(parts)
        return data, "audio/wav", duration


class LocalTTSProvider:
    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        data = self._espeak_ng(text)
        if data is None:
            data = self._pyttsx3(text)
        if not data:
            raise RuntimeError("No audio was produced")
        data, duration = assemble_wav([data])
        return data, "audio/wav", duration

    def _espeak_ng(self, text: str) -> bytes | None:
        """Headless synthesis via espeak-ng, which writes WAV without an audio
        device. This is the container-safe path; pyttsx3 needs an audio backend
        (ALSA/pulseaudio) that slim containers do not provide."""
        import os
        import shutil
        import subprocess
        import tempfile

        binary = shutil.which("espeak-ng") or shutil.which("espeak")
        if not binary:
            return None
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "speech.wav")
            try:
                # Generated Markdown can start with a dash. Keep learner text
                # on stdin so it is never interpreted as a command option.
                proc = subprocess.run(
                    [binary, "-b", "1", "-w", path, "--stdin"],
                    input=text.encode("utf-8"),
                    capture_output=True,
                    timeout=60,
                )
            except (subprocess.TimeoutExpired, OSError):
                return None
            if proc.returncode != 0 or not os.path.exists(path):
                return None
            with open(path, "rb") as handle:
                return handle.read()

    def _pyttsx3(self, text: str) -> bytes:
        import os
        import tempfile

        try:
            import pyttsx3
        except ImportError as exc:
            raise RuntimeError(
                "Local text-to-speech requires espeak-ng or the pyttsx3 dependency"
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
        return data


def _audio_upload_filename(content_type: str) -> str:
    media_type = content_type.split(";", 1)[0].strip().lower()
    extension = {
        "audio/webm": "webm", "video/webm": "webm",
        "audio/wav": "wav", "audio/x-wav": "wav",
        "audio/mpeg": "mp3", "audio/mp3": "mp3",
        "audio/mp4": "mp4", "video/mp4": "mp4", "audio/m4a": "m4a",
        "audio/ogg": "ogg", "audio/opus": "opus",
        "audio/flac": "flac", "audio/x-flac": "flac",
    }.get(media_type, "webm")
    return f"audio.{extension}"


class CloudSTTProvider:
    def __init__(self, *, api_key: str, model: str = "whisper-1") -> None:
        self.api_key = api_key
        self.model = model

    def transcribe(self, *, audio: bytes, content_type: str) -> str:
        response = httpx.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            files={"file": (_audio_upload_filename(content_type), audio, content_type)},
            data={"model": self.model},
            timeout=60,
        )
        response.raise_for_status()
        return response.json().get("text", "").strip()


class GroqTTSProvider:
    """Groq OpenAI-compatible /audio/speech (canopylabs orpheus models).

    The Groq org must accept the model's terms in the Groq console once;
    until then calls fail with model_terms_required and the TTS chain falls
    through to the next provider instead of failing the artifact outright.
    """

    def __init__(self, *, api_key: str, model: str, voice: str) -> None:
        self.api_key = api_key
        self.model = model
        self.voice = voice

    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        parts: list[bytes] = []
        for segment in speech_segments(text):
            response = httpx.post(
                "https://api.groq.com/openai/v1/audio/speech",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model, "voice": self.voice,
                    "input": segment, "response_format": "wav",
                },
                timeout=120,
            )
            response.raise_for_status()
            parts.append(response.content)
        data, duration = assemble_wav(parts)
        return data, "audio/wav", duration


class GroqSTTProvider:
    """Groq OpenAI-compatible /audio/transcriptions (whisper-large-v3)."""

    def __init__(self, *, api_key: str, model: str = "whisper-large-v3") -> None:
        self.api_key = api_key
        self.model = model

    def transcribe(self, *, audio: bytes, content_type: str) -> str:
        response = httpx.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            files={"file": (_audio_upload_filename(content_type), audio, content_type)},
            data={"model": self.model},
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("text", "").strip()


class ChainedTTSProvider:
    """Try providers in order; the first success wins.

    Production containers have no audio device for the local pyttsx3
    fallback, and a cloud model can be blocked account-side (e.g. Groq model
    terms acceptance). Chaining keeps audio generation working while the
    preferred cloud voice comes online without code changes.
    """

    def __init__(self, providers: list) -> None:
        self.providers = providers

    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        for provider in self.providers:
            try:
                return provider.generate(text=text)
            except Exception as exc:  # noqa: BLE001 - chain reports every failure
                logger.warning(
                    "tts provider failed provider=%s error_type=%s",
                    type(provider).__name__, type(exc).__name__,
                )
        raise RuntimeError("all TTS providers failed")


# Default completion limit (tokens) reserved before each owner-scoped
# call when a per-learner budget is active. Configurable via
# ARIA_LLM_COMPLETION_RESERVE_TOKENS. The same limit is sent to the provider.
# Admission and input estimates remain best-effort, not hard spending caps.
DEFAULT_COMPLETION_RESERVE_TOKENS = 512


def completion_reserve_tokens() -> int:
    from app.core.config import get_settings

    return max(
        1, int(getattr(get_settings(), "aria_llm_completion_reserve_tokens", DEFAULT_COMPLETION_RESERVE_TOKENS))
    )


class LiteLLMGroqProvider:
    def __init__(self, *, api_key: str, model: str, owner_id=None) -> None:
        self.api_key = api_key
        self.model = model
        self.owner_id = owner_id

    def _log_call(
        self,
        *,
        kind: str,
        started: float,
        response: object,
        prompt_version: str | None = None,
        prompt_chars: int = 0,
        completion_chars: int = 0,
        account_global: bool = True,
    ) -> tuple[int, int]:
        duration_ms = int((time.monotonic() - started) * 1000)
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
        # Invalid metadata must never produce negative charges or refunds.
        if type(prompt_tokens) is not int or prompt_tokens < 0:
            prompt_tokens = None
        if type(completion_tokens) is not int or completion_tokens < 0:
            completion_tokens = None
        estimated = False
        if prompt_tokens is None or completion_tokens is None:
            # Heuristic estimate (see estimate_tokens) so a response without
            # usage metadata is still accounted instead of bypassing budgets.
            estimated = True
            if prompt_tokens is None:
                prompt_tokens = estimate_tokens(prompt_chars)
            if completion_tokens is None:
                completion_tokens = estimate_tokens(completion_chars)
        logger.info(
            "ai_call kind=%s model=%s prompt_version=%s duration_ms=%d "
            "prompt_tokens=%s completion_tokens=%s estimated=%s",
            kind,
            self.model,
            prompt_version,
            duration_ms,
            prompt_tokens,
            completion_tokens,
            estimated,
        )
        try:
            from app.ai.budget import record_usage
            from app.core.metrics import observe_ai_call

            if account_global:
                record_usage(
                    model=self.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
            # Active budgets reserve/settle in the caller. Without a global
            # reservation, global accounting records the post-call usage here.
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
        return prompt_tokens, completion_tokens

    @staticmethod
    def _completion_chars(response: object) -> int:
        """Account returned usage even when the response has no usable choice."""
        choices = getattr(response, "choices", None)
        if not choices:
            return 0
        content = getattr(getattr(choices[0], "message", None), "content", None)
        return len(content) if isinstance(content, str) else 0

    def _reserve_budgets(self, prompt_chars: int):
        from app.ai.budget import monthly_budget_usd, reserve_usage

        global_reserved = None
        if monthly_budget_usd() > 0:
            global_reserved = (estimate_tokens(prompt_chars), completion_reserve_tokens())
            period = reserve_usage(
                model=self.model, prompt_tokens=global_reserved[0], completion_tokens=global_reserved[1]
            )
            global_reserved = (*global_reserved, period)
        try:
            learner_reserved = self._reserve_learner(prompt_chars)
        except BaseException:
            # No provider call was dispatched; this reservation is refundable.
            self._settle_global(global_reserved, (0, 0))
            raise
        return global_reserved, learner_reserved

    def _settle_global(self, reserved, final):
        if reserved is None or final is None:
            return
        from app.ai.budget import record_usage

        record_usage(model=self.model, prompt_tokens=final[0] - reserved[0],
                     completion_tokens=final[1] - reserved[1],
                     period=reserved[2] if len(reserved) > 2 else None)

    def _reserve_learner(self, prompt_chars: int) -> tuple[int, int, str] | None:
        """Pre-call estimate for per-learner budgets; None when inactive."""
        from app.ai.budget import learner_budget_usd, reserve_learner_usage

        if self.owner_id is None or learner_budget_usd() <= 0:
            return None
        reserved = (
            estimate_tokens(prompt_chars),
            completion_reserve_tokens(),
        )
        period = reserve_learner_usage(
            owner_id=self.owner_id,
            model=self.model,
            prompt_tokens=reserved[0],
            completion_tokens=reserved[1],
        )
        return (*reserved, period)

    def _settle_learner(
        self, reserved: tuple[int, int, str] | None, final: tuple[int, int] | None
    ) -> None:
        from app.ai.budget import record_learner_usage, settle_learner_usage

        if self.owner_id is None:
            return
        if reserved is None:
            # Budget inactive (unlimited): plain post-call recording.
            if final is not None:
                record_learner_usage(
                    owner_id=self.owner_id,
                    model=self.model,
                    prompt_tokens=final[0],
                    completion_tokens=final[1],
                )
            return
        if final is None:
            # A transport failure does not prove the provider performed no
            # work. Keep the provisional reservation instead of refunding
            # potentially billable usage; this can conservatively overcount.
            return
        settle_learner_usage(
            owner_id=self.owner_id,
            model=self.model,
            prompt_tokens_delta=final[0] - reserved[0],
            completion_tokens_delta=final[1] - reserved[1],
            period=reserved[2] if len(reserved) > 2 else None,
        )

    async def generate_text(
        self,
        *,
        system: str,
        user: str,
        prompt_version: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        from litellm import acompletion

        from app.ai.budget import assert_learner_within_budget, assert_within_budget

        assert_within_budget()
        if self.owner_id is not None:
            assert_learner_within_budget(self.owner_id)
        global_reserved, reserved = self._reserve_budgets(len(system) + len(user))
        output_reservation = global_reserved or reserved
        started = time.monotonic()
        final = None
        try:
            response = await acompletion(
                model=f"groq/{self.model}",
                api_key=self.api_key,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=temperature,
                **({"max_tokens": output_reservation[1]} if output_reservation is not None else {}),
                timeout=60,
            )
            final = self._log_call(
                kind="generate_text",
                started=started,
                response=response,
                prompt_version=prompt_version,
                prompt_chars=len(system) + len(user),
                completion_chars=self._completion_chars(response),
                account_global=global_reserved is None,
            )
            text = response.choices[0].message.content or ""
        except Exception:
            # Preserve returned usage even if response extraction fails.
            # Log the model so fallback_used=true is triageable server-side
            # (e.g. invalid model vs bad key vs terms acceptance).
            logger.warning("groq generate_text failed model=%s", self.model, exc_info=True)
            self._settle_learner(reserved, final)
            self._settle_global(global_reserved, final)
            raise
        self._settle_learner(reserved, final)
        self._settle_global(global_reserved, final)
        return text

    async def generate_structured(
        self, *, prompt: str, schema: type, prompt_version: str | None = None
    ) -> object:
        from litellm import acompletion

        from app.ai.budget import assert_learner_within_budget, assert_within_budget

        assert_within_budget()
        if self.owner_id is not None:
            assert_learner_within_budget(self.owner_id)
        system = "You produce only valid JSON matching the schema."
        prompt_chars = len(system) + len(prompt)
        global_reserved, reserved = self._reserve_budgets(prompt_chars)
        output_reservation = global_reserved or reserved
        started = time.monotonic()
        final = None
        try:
            response = await acompletion(
                model=f"groq/{self.model}",
                api_key=self.api_key,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                **({"max_tokens": output_reservation[1]} if output_reservation is not None else {}),
                timeout=60,
            )
            final = self._log_call(
                kind="generate_structured",
                started=started,
                response=response,
                prompt_version=prompt_version,
                prompt_chars=prompt_chars,
                completion_chars=self._completion_chars(response),
                account_global=global_reserved is None,
            )
            text = response.choices[0].message.content or ""
        except Exception:
            # Returned provider usage is chargeable even with malformed choices.
            logger.warning("groq generate_structured failed model=%s", self.model, exc_info=True)
            self._settle_learner(reserved, final)
            self._settle_global(global_reserved, final)
            raise
        self._settle_learner(reserved, final)
        self._settle_global(global_reserved, final)
        return schema.model_validate_json(text)
