from pydantic import BaseModel, Field


class LLMKeyUpsertRequest(BaseModel):
    # Plaintext only in the request body; never persisted or returned.
    key: str = Field(min_length=20, max_length=200)
    model: str | None = Field(default=None, max_length=128)


class LLMKeyStatusResponse(BaseModel):
    configured: bool
    provider: str | None = None
    model: str | None = None
    # Redacted hint ("...last4"); the full key is never returned.
    hint: str | None = None
