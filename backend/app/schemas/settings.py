from typing import Literal

from pydantic import BaseModel, Field


class LLMKeyUpsertRequest(BaseModel):
    # Plaintext only in the request body; never persisted or returned.
    key: str = Field(min_length=20, max_length=200)
    model: str | None = Field(default=None, max_length=128)


class LLMKeyStatusResponse(BaseModel):
    configured: bool
    # Local decryptability/configuration only; no provider health claim.
    usable: bool = False
    issue: str | None = None
    provider: str | None = None
    model: str | None = None
    # Redacted hint ("...last4"); the full key is never returned.
    hint: str | None = None


class CapabilityResponse(BaseModel):
    credential_source: Literal["learner", "global", "none"]
    tutor_configured: bool
    provider_verified: bool = False
    model: str
    allowed_models: list[str]
    personal_keys_enabled: bool
    personal_key: LLMKeyStatusResponse
    speech_to_text_configured: bool
    cloud_speech_configured: bool
    audio_credential_scope: Literal["deployment"] = "deployment"
