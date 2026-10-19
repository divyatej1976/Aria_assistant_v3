from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

DEFAULT_QUESTION_COUNT = 10
MAX_QUESTION_COUNT = 50


class AssessmentCreateRequest(BaseModel):
    context_id: UUID
    # mcq | true_false | short_answer | mixed
    format: str = Field(default="mcq", min_length=2, max_length=64)
    question_count: int = Field(default=DEFAULT_QUESTION_COUNT, ge=1, le=MAX_QUESTION_COUNT)
    difficulty: str = Field(default="medium", max_length=32)
    mode: str = Field(default="BASELINE", max_length=32)
    concept_ids: list[UUID] = Field(default_factory=list)
    # What the quiz is about: the shared library, chosen chats, a typed topic, or weak spots.
    source: Literal["library", "chats", "topic", "weak"] = "library"
    session_ids: list[UUID] = Field(default_factory=list, max_length=20)
    topic: str | None = Field(default=None, max_length=300)
    # How it is taken: timer and when answers are revealed.
    timing: Literal["none", "total", "per_question"] = "none"
    time_limit_seconds: int | None = Field(default=None, ge=10, le=4 * 60 * 60)
    reveal: Literal["practice", "exam"] = "practice"

    @model_validator(mode="after")
    def timer_needs_a_limit(self) -> "AssessmentCreateRequest":
        if self.timing != "none" and self.time_limit_seconds is None:
            raise ValueError("Choose how long the timer should run")
        return self

    def settings(self) -> dict:
        return {
            "timing": self.timing,
            "time_limit_seconds": self.time_limit_seconds if self.timing != "none" else None,
            "reveal": self.reveal,
        }


class AssessmentQuestionResponse(BaseModel):
    id: str
    position: int
    prompt: str
    options: list[str]
    concept_id: str | None
    kind: str = "mcq"


class QuizSettings(BaseModel):
    timing: str = "none"
    time_limit_seconds: int | None = None
    reveal: str = "exam"
    source: str = "library"


class AssessmentResponse(BaseModel):
    id: str
    format: str
    mode: str
    status: str
    questions: list[AssessmentQuestionResponse]
    settings: QuizSettings = Field(default_factory=QuizSettings)


class AssessmentScore(BaseModel):
    attempt_id: str
    score: int
    total: int
    completed_at: datetime


class AssessmentSummary(BaseModel):
    id: str
    context_id: str
    format: str
    mode: str
    status: str
    question_count: int
    submitted_attempt_count: int = 0
    completed_scores: list[AssessmentScore] = Field(default_factory=list)
    created_at: datetime
    settings: QuizSettings = Field(default_factory=QuizSettings)
    topic: str | None = None


class AttemptStartResponse(BaseModel):
    attempt_id: str
    assessment_id: str
    questions: list[AssessmentQuestionResponse]
    settings: QuizSettings = Field(default_factory=QuizSettings)


class AnswerCheckRequest(BaseModel):
    question_id: UUID
    answer: str = Field(max_length=2000)


class AnswerCheckResponse(BaseModel):
    correct: bool
    correct_answer: str
    explanation: str | None = None


class AnswerSaveRequest(BaseModel):
    answers: dict[str, str]


class AttemptSubmitRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)
    answers: dict[str, str] = Field(default_factory=dict)


class QuestionEvaluation(BaseModel):
    question_id: str
    selected_option: str | None
    correct: bool
    correct_option: str
    correct_answer: str | None = None
    explanation: str | None = None


class AttemptResultResponse(BaseModel):
    attempt_id: str
    evaluation_id: str
    score: int
    total: int
    status: str
    details: list[QuestionEvaluation]
