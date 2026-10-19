from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.assessment.formats import format_registry
from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.db.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    Concept,
    ConversationMessage,
    Evaluation,
    LearningContext,
)
from app.schemas.assessment import (
    AnswerCheckRequest,
    AnswerCheckResponse,
    AnswerSaveRequest,
    AssessmentCreateRequest,
    AssessmentQuestionResponse,
    AssessmentResponse,
    AssessmentScore,
    AssessmentSummary,
    AttemptResultResponse,
    AttemptStartResponse,
    AttemptSubmitRequest,
    QuestionEvaluation,
    QuizSettings,
)
from app.security.dependencies import CurrentLearner
from app.security.rate_limit import rate_limited
from app.services.adaptation import run_learner_loop
from app.services.assessment import (
    check_answer,
    create_assessment,
    get_owned_assessment,
    get_owned_attempt,
    list_assessment_questions,
    save_answers,
    start_attempt,
    submit_attempt,
)
from app.services.progress import record_activity
from app.services.quiz_summary import summarize_attempt
from app.services.review_planning import apply_daily_review_results

router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])
Db = Annotated[Session, Depends(get_db)]


def _ai_rate_limit():
    settings = get_settings()
    return rate_limited(settings.aria_rate_limit_requests, settings.aria_rate_limit_window_seconds)


def get_owned_context(db: Session, *, context_id: UUID, owner_id: UUID) -> LearningContext:
    context = db.scalar(
        select(LearningContext).where(LearningContext.id == context_id, LearningContext.owner_id == owner_id)
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
        kind=question.kind,
    )


def quiz_settings(assessment: Assessment) -> QuizSettings:
    config = assessment.configuration or {}
    return QuizSettings(
        timing=config.get("timing") or "none",
        time_limit_seconds=config.get("time_limit_seconds"),
        # Quizzes made before reveal modes existed showed answers only at the end.
        reveal=config.get("reveal") or "exam",
        source=config.get("source") or "library",
    )


def assessment_response(db: Session, assessment: Assessment) -> AssessmentResponse:
    questions = list_assessment_questions(db, assessment_id=assessment.id, owner_id=assessment.owner_id)
    return AssessmentResponse(
        id=str(assessment.id),
        format=assessment.format,
        mode=assessment.mode,
        status=assessment.status,
        questions=[question_response(item) for item in questions],
        settings=quiz_settings(assessment),
    )


def summary_response(
    assessment: Assessment,
    *,
    question_count: int = 0,
    submitted_attempt_count: int = 0,
    completed_scores: list[AssessmentScore] | None = None,
    topic: str | None = None,
) -> AssessmentSummary:
    return AssessmentSummary(
        id=str(assessment.id),
        context_id=str(assessment.context_id),
        format=assessment.format,
        mode=assessment.mode,
        status=assessment.status,
        question_count=question_count,
        submitted_attempt_count=submitted_attempt_count,
        completed_scores=completed_scores or [],
        created_at=assessment.created_at,
        settings=quiz_settings(assessment),
        topic=topic,
    )


@router.get("/formats")
def list_formats() -> list[dict[str, str]]:
    return [definition.__dict__ for definition in format_registry.list()]


@router.get("", response_model=list[AssessmentSummary])
def list_assessments(
    learner: CurrentLearner,
    db: Db,
    context_id: UUID,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AssessmentSummary]:
    get_owned_context(db, context_id=context_id, owner_id=learner.id)
    assessments = db.scalars(
        select(Assessment)
        .where(Assessment.owner_id == learner.id, Assessment.context_id == context_id)
        .order_by(Assessment.created_at.desc(), Assessment.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    # One GROUP BY instead of one COUNT per assessment (N+1).
    counts = dict(
        db.execute(
            select(AssessmentQuestion.assessment_id, func.count(AssessmentQuestion.id))
            .where(AssessmentQuestion.assessment_id.in_([item.id for item in assessments]))
            .group_by(AssessmentQuestion.assessment_id)
        ).all()
    )
    submitted = dict(
        db.execute(
            select(AssessmentAttempt.assessment_id, func.count(AssessmentAttempt.id))
            .where(
                AssessmentAttempt.assessment_id.in_([item.id for item in assessments]),
                AssessmentAttempt.owner_id == learner.id,
                AssessmentAttempt.status == "SUBMITTED",
            )
            .group_by(AssessmentAttempt.assessment_id)
        ).all()
    )
    # Name each quiz after the concept most of its questions test (ordered so the top one wins).
    topics: dict[UUID, str] = {}
    for assessment_id, name, _ in db.execute(
        select(AssessmentQuestion.assessment_id, Concept.name, func.count(AssessmentQuestion.id))
        .join(Concept, Concept.id == AssessmentQuestion.concept_id)
        .where(AssessmentQuestion.assessment_id.in_([item.id for item in assessments]))
        .group_by(AssessmentQuestion.assessment_id, Concept.name)
        .order_by(func.count(AssessmentQuestion.id).desc(), Concept.name)
    ).all():
        topics.setdefault(assessment_id, name)
    # Chat and topic quizzes have no concepts: fall back to the typed topic, then the chat's first question.
    from app.services.study import _plain_snippet

    first_chat = {
        item.id: UUID(ids[0]) for item in assessments
        if item.id not in topics and (ids := (item.configuration or {}).get("session_ids"))
    }
    openers: dict[UUID, str] = {}
    for session_id, content in db.execute(
        select(ConversationMessage.study_session_id, ConversationMessage.content)
        .where(ConversationMessage.study_session_id.in_(set(first_chat.values())),
               ConversationMessage.owner_id == learner.id, ConversationMessage.role == "user")
        .order_by(ConversationMessage.position)
    ).all():
        openers.setdefault(session_id, content)
    for item in assessments:
        config = item.configuration or {}
        if item.id in topics:
            continue
        if config.get("topic"):
            topics[item.id] = str(config["topic"])[:60]
        elif item.id in first_chat and first_chat[item.id] in openers:
            topics[item.id] = _plain_snippet(openers[first_chat[item.id]], 60)
    scores: dict[UUID, list[AssessmentScore]] = {}
    ranked = (
        select(
            AssessmentAttempt.assessment_id,
            AssessmentAttempt.id.label("attempt_id"),
            Evaluation.id.label("evaluation_id"),
            func.row_number()
            .over(
                partition_by=AssessmentAttempt.assessment_id,
                order_by=(Evaluation.created_at.desc(), Evaluation.id.desc()),
            )
            .label("score_rank"),
        )
        .join(Evaluation, Evaluation.attempt_id == AssessmentAttempt.id)
        .where(
            AssessmentAttempt.assessment_id.in_([item.id for item in assessments]),
            AssessmentAttempt.owner_id == learner.id,
            Evaluation.owner_id == learner.id,
            AssessmentAttempt.status == "SUBMITTED",
            Evaluation.status == "COMPLETED",
        )
    ).subquery()
    results = db.execute(
        select(ranked.c.assessment_id, ranked.c.attempt_id, Evaluation)
        .join(Evaluation, Evaluation.id == ranked.c.evaluation_id)
        .where(ranked.c.score_rank <= 20)
        .order_by(Evaluation.created_at, Evaluation.id)
    ).all()
    for assessment_id, attempt_id, evaluation in results:
        total = evaluation.details.get("total")
        score = evaluation.score
        if (
            not isinstance(total, int)
            or isinstance(total, bool)
            or total <= 0
            or score is None
            or not 0 <= score <= total
        ):
            continue
        scores.setdefault(assessment_id, []).append(
            AssessmentScore(
                attempt_id=str(attempt_id),
                score=score,
                total=total,
                completed_at=evaluation.created_at,
            )
        )
    return [
        summary_response(
            assessment,
            question_count=counts.get(assessment.id, 0),
            submitted_attempt_count=submitted.get(assessment.id, 0),
            completed_scores=scores.get(assessment.id),
            topic=topics.get(assessment.id),
        )
        for assessment in assessments
    ]


@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment_detail(assessment_id: UUID, learner: CurrentLearner, db: Db) -> AssessmentResponse:
    assessment = get_assessment(db, assessment_id=assessment_id, owner_id=learner.id)
    return assessment_response(db, assessment)


@router.post("", response_model=AssessmentResponse, status_code=201, dependencies=[Depends(_ai_rate_limit())])
async def create(request: AssessmentCreateRequest, learner: CurrentLearner, db: Db) -> AssessmentResponse:
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
            source=request.source,
            session_ids=request.session_ids,
            topic=request.topic,
            settings=request.settings(),
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return assessment_response(db, assessment)


@router.post("/{assessment_id}/attempts", response_model=AttemptStartResponse, status_code=201)
def start(assessment_id: UUID, learner: CurrentLearner, db: Db) -> AttemptStartResponse:
    assessment = get_assessment(db, assessment_id=assessment_id, owner_id=learner.id)
    attempt = start_attempt(db, owner_id=learner.id, assessment_id=assessment.id)
    questions = list_assessment_questions(db, assessment_id=assessment.id, owner_id=learner.id)
    return AttemptStartResponse(
        attempt_id=str(attempt.id),
        assessment_id=str(assessment.id),
        questions=[question_response(item) for item in questions],
        settings=quiz_settings(assessment),
    )


@router.post("/{assessment_id}/attempts/{attempt_id}/check", response_model=AnswerCheckResponse)
def check_answer_route(
    assessment_id: UUID, attempt_id: UUID, request: AnswerCheckRequest, learner: CurrentLearner, db: Db,
) -> AnswerCheckResponse:
    """Practice mode: save one answer and reveal whether it was right."""
    assessment = get_assessment(db, assessment_id=assessment_id, owner_id=learner.id)
    if quiz_settings(assessment).reveal != "practice":
        raise HTTPException(status_code=409, detail="Answers are revealed at the end of this quiz")
    owned_attempt = get_owned_attempt(db, owner_id=learner.id, attempt_id=attempt_id)
    if owned_attempt is None or owned_attempt.assessment_id != assessment.id:
        raise HTTPException(status_code=404, detail="Attempt does not belong to assessment")
    try:
        correct, answer, explanation = check_answer(
            db, owner_id=learner.id, attempt_id=attempt_id, question_id=request.question_id, answer=request.answer,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AnswerCheckResponse(correct=correct, correct_answer=answer, explanation=explanation)


@router.post("/{assessment_id}/attempts/{attempt_id}/summary", dependencies=[Depends(_ai_rate_limit())])
async def summary_route(assessment_id: UUID, attempt_id: UUID, learner: CurrentLearner, db: Db) -> dict[str, str]:
    """A short debrief: what the learner understands, what to practise, what to do next."""
    assessment = get_assessment(db, assessment_id=assessment_id, owner_id=learner.id)
    owned_attempt = get_owned_attempt(db, owner_id=learner.id, attempt_id=attempt_id)
    if owned_attempt is None or owned_attempt.assessment_id != assessment.id:
        raise HTTPException(status_code=404, detail="Attempt does not belong to assessment")
    try:
        return {"summary": await summarize_attempt(db, owner_id=learner.id, attempt_id=attempt_id)}
    except ValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/{assessment_id}/attempts/{attempt_id}/answers")
def save_answers_route(
    assessment_id: UUID,
    attempt_id: UUID,
    request: AnswerSaveRequest,
    learner: CurrentLearner,
    db: Db,
) -> dict[str, object]:
    assessment = get_assessment(db, assessment_id=assessment_id, owner_id=learner.id)
    owned_attempt = get_owned_attempt(db, owner_id=learner.id, attempt_id=attempt_id)
    if owned_attempt is None or owned_attempt.assessment_id != assessment.id:
        raise HTTPException(status_code=404, detail="Attempt does not belong to assessment")
    try:
        attempt = save_answers(db, owner_id=learner.id, attempt_id=attempt_id, answers=request.answers)
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
    owned_attempt = get_owned_attempt(db, owner_id=learner.id, attempt_id=attempt_id)
    if owned_attempt is None or owned_attempt.assessment_id != assessment.id:
        raise HTTPException(status_code=404, detail="Attempt does not belong to assessment")
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
    apply_daily_review_results(
        db,
        owner_id=learner.id,
        assessment_id=assessment.id,
        evaluation_id=evaluation.id,
    )
    record_activity(db, owner_id=learner.id, activity_type="assessment", source_id=attempt.id)
    return AttemptResultResponse(
        attempt_id=str(attempt.id),
        evaluation_id=str(evaluation.id),
        score=evaluation.score or 0,
        total=int(evaluation.details.get("total", 0)),
        status=evaluation.status,
        details=[QuestionEvaluation(**item) for item in details],
    )
