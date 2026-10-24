from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class FeedbackRequest(BaseModel):
    # report: a problem; answer: thumbs on one reply; experience: 1-5 stars for ARIA overall
    kind: Literal["report", "answer", "experience"]
    rating: Literal["up", "down", "1", "2", "3", "4", "5"] | None = None
    reason: Literal["wrong", "too_long", "too_short", "outdated", "ignored_my_file", "other"] | None = None
    message: str | None = Field(default=None, max_length=4000)
    page: str | None = Field(default=None, max_length=300)
    user_agent: str | None = Field(default=None, max_length=300)
    answer_id: UUID | None = None

    @model_validator(mode="after")
    def complete(self) -> "FeedbackRequest":
        if self.kind == "report" and not (self.message or "").strip():
            raise ValueError("Tell us what went wrong")
        if self.kind == "answer" and (self.rating not in ("up", "down") or self.answer_id is None):
            raise ValueError("An answer rating needs the answer and up or down")
        if self.kind == "experience" and self.rating not in ("1", "2", "3", "4", "5"):
            raise ValueError("Choose 1 to 5 stars")
        return self


class FeedbackResponse(BaseModel):
    id: str
    status: str
