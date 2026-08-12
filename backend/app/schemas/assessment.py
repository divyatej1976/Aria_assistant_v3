from datetime import datetime

from pydantic import BaseModel, Field


class AssessmentCreateRequest(BaseModel):
    context_id: str
    format: str = Field(default="mcq", min_length=2, max_length=64)
    question_count: int = Field(default=5, ge=1, le=20)
    difficulty: str = Field(default="medium", max_length=32)
    mode: str = Field(default="BASELINE", max_length=32)
    concept_ids: list[str] = Field(default_factory=list)


class AssessmentQuestionResponse(BaseModel):
    id: str
    position: int
    prompt: str
    options: list[str]
    concept_id: str | None


class AssessmentResponse(BaseModel):
    id: str
    format: str
    mode: str
    status: str
    questions: list[AssessmentQuestionResponse]


class AssessmentSummary(BaseModel):
    id: str
    context_id: str
    format: str
    mode: str
    status: str
    question_count: int
    created_at: datetime


class AttemptStartResponse(BaseModel):
    attempt_id: str
    assessment_id: str
    questions: list[AssessmentQuestionResponse]


class AnswerSaveRequest(BaseModel):
    answers: dict[str, str]


class AttemptSubmitRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    answers: dict[str, str] = Field(default_factory=dict)


class QuestionEvaluation(BaseModel):
    question_id: str
    selected_option: str | None
    correct: bool
    correct_option: str


class AttemptResultResponse(BaseModel):
    attempt_id: str
    evaluation_id: str
    score: int
    total: int
    status: str
    details: list[QuestionEvaluation]
