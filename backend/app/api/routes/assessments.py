from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.assessment.formats import format_registry
from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.db.models import (
    Assessment,
    AssessmentQuestion,
    LearningContext,
)
from app.schemas.assessment import (
    AnswerSaveRequest,
    AssessmentCreateRequest,
    AssessmentQuestionResponse,
    AssessmentResponse,
    AssessmentSummary,
    AttemptResultResponse,
    AttemptStartResponse,
    AttemptSubmitRequest,
    QuestionEvaluation,
)
from app.security.dependencies import CurrentLearner
from app.services.adaptation import run_learner_loop
from app.services.assessment import (
    create_assessment,
    get_owned_assessment,
    list_assessment_questions,
    save_answers,
    start_attempt,
    submit_attempt,
)
from app.services.progress import record_activity

router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])
Db = Annotated[Session, Depends(get_db)]


def get_owned_context(db: Session, *, context_id: UUID, owner_id: UUID) -> LearningContext:
    context = db.scalar(
        select(LearningContext).where(
            LearningContext.id == context_id, LearningContext.owner_id == owner_id
        )
    )
    if context is None:
        raise HTTPException(status_code=404, detail="Learning context not found")
    return context


def get_assessment(db: Session, *, assessment_id: UUID, owner_id: UUID) -> Assessment:
    assessment = get_owned_assessment(db, owner_id=owner_id, assessment_id=assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


def question_response(question: AssessmentQuestion) -> AssessmentQuestionResponse:
    return AssessmentQuestionResponse(
        id=str(question.id),
        position=question.position,
        prompt=question.prompt,
        options=question.options,
        concept_id=str(question.concept_id) if question.concept_id else None,
    )


def assessment_response(
    db: Session, assessment: Assessment
) -> AssessmentResponse:
    questions = list_assessment_questions(
        db, assessment_id=assessment.id, owner_id=assessment.owner_id
    )
    return AssessmentResponse(
        id=str(assessment.id),
        format=assessment.format,
        mode=assessment.mode,
        status=assessment.status,
        questions=[question_response(item) for item in questions],
    )


def summary_response(db: Session, assessment: Assessment) -> AssessmentSummary:
    count = db.scalar(
        select(func.count(AssessmentQuestion.id)).where(
            AssessmentQuestion.assessment_id == assessment.id
        )
    )
    return AssessmentSummary(
        id=str(assessment.id),
        context_id=str(assessment.context_id),
        format=assessment.format,
        mode=assessment.mode,
        status=assessment.status,
        question_count=count or 0,
        created_at=assessment.created_at,
    )


@router.get("/formats")
def list_formats() -> list[dict[str, str]]:
    return [definition.__dict__ for definition in format_registry.list()]


@router.get("", response_model=list[AssessmentSummary])
def list_assessments(
    learner: CurrentLearner, db: Db, context_id: UUID
) -> list[AssessmentSummary]:
    get_owned_context(db, context_id=context_id, owner_id=learner.id)
    assessments = db.scalars(
        select(Assessment)
        .where(Assessment.owner_id == learner.id, Assessment.context_id == context_id)
        .order_by(Assessment.created_at)
    ).all()
    return [summary_response(db, assessment) for assessment in assessments]


@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment_detail(
    assessment_id: UUID, learner: CurrentLearner, db: Db
) -> AssessmentResponse:
    assessment = get_assessment(db, assessment_id=assessment_id, owner_id=learner.id)
    return assessment_response(db, assessment)


@router.post("", response_model=AssessmentResponse, status_code=201)
async def create(
    request: AssessmentCreateRequest, learner: CurrentLearner, db: Db
) -> AssessmentResponse:
    get_owned_context(db, context_id=request.context_id, owner_id=learner.id)
    try:
        assessment = await create_assessment(
            db,
            owner_id=learner.id,
            context_id=request.context_id,
            format_name=request.format,
            question_count=request.question_count,
            difficulty=request.difficulty,
            mode=request.mode,
            concept_ids=request.concept_ids,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return assessment_response(db, assessment)


@router.post("/{assessment_id}/attempts", response_model=AttemptStartResponse, status_code=201)
def start(
    assessment_id: UUID, learner: CurrentLearner, db: Db
) -> AttemptStartResponse:
    assessment = get_assessment(db, assessment_id=assessment_id, owner_id=learner.id)
    attempt = start_attempt(db, owner_id=learner.id, assessment_id=assessment.id)
    questions = list_assessment_questions(
        db, assessment_id=assessment.id, owner_id=learner.id
    )
    return AttemptStartResponse(
        attempt_id=str(attempt.id),
        assessment_id=str(assessment.id),
        questions=[question_response(item) for item in questions],
    )


@router.put("/{assessment_id}/attempts/{attempt_id}/answers")
def save_answers_route(
    assessment_id: UUID,
    attempt_id: UUID,
    request: AnswerSaveRequest,
    learner: CurrentLearner,
    db: Db,
) -> dict[str, object]:
    assessment = get_assessment(db, assessment_id=assessment_id, owner_id=learner.id)
    try:
        attempt = save_answers(
            db, owner_id=learner.id, attempt_id=attempt_id, answers=request.answers
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if attempt.assessment_id != assessment.id:
        raise HTTPException(status_code=404, detail="Attempt does not belong to assessment")
    return {"attempt_id": str(attempt.id), "status": attempt.status}


@router.post("/{assessment_id}/attempts/{attempt_id}/submit", response_model=AttemptResultResponse)
def submit(
    assessment_id: UUID,
    attempt_id: UUID,
    request: AttemptSubmitRequest,
    learner: CurrentLearner,
    db: Db,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> AttemptResultResponse:
    assessment = get_assessment(db, assessment_id=assessment_id, owner_id=learner.id)
    key = request.idempotency_key or idempotency_key
    if not key:
        raise HTTPException(
            status_code=422,
            detail="idempotency_key (body or Idempotency-Key header) is required",
        )
    try:
        attempt, evaluation, details = submit_attempt(
            db,
            owner_id=learner.id,
            attempt_id=attempt_id,
            idempotency_key=key,
            answers=request.answers,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if attempt.assessment_id != assessment.id:
        raise HTTPException(status_code=404, detail="Attempt does not belong to assessment")
    run_learner_loop(db, owner_id=learner.id, context_id=assessment.context_id)
    record_activity(db, owner_id=learner.id, activity_type="assessment", source_id=attempt.id)
    return AttemptResultResponse(
        attempt_id=str(attempt.id),
        evaluation_id=str(evaluation.id),
        score=evaluation.score or 0,
        total=int(evaluation.details.get("total", 0)),
        status=evaluation.status,
        details=[QuestionEvaluation(**item) for item in details],
    )
