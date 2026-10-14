import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.db.models import Learner
from app.schemas.auth import (
    EmailVerifyConfirm,
    LearnerResponse,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    SessionRecord,
    SessionResponse,
)
from app.security.csrf import clear_auth_cookies, set_auth_cookies
from app.security.dependencies import CurrentLearner, CurrentSession
from app.security.passwords import hash_password, verify_password
from app.security.rate_limit import rate_limited
from app.security.secrets import get_session_secret
from app.security.tokens import create_session_token
from app.services.account import (
    change_password,
    create_learner_session,
    list_active_sessions,
    revoke_session,
    update_profile,
)
from app.services.account_actions import (
    confirm_email_verification,
    confirm_password_reset,
    request_email_verification,
    request_password_reset,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
Db = Annotated[Session, Depends(get_db)]


def _auth_rate_limit():
    settings = get_settings()
    return rate_limited(
        settings.aria_rate_limit_requests, settings.aria_rate_limit_window_seconds
    )


def learner_response(learner: Learner) -> LearnerResponse:
    return LearnerResponse(
        id=str(learner.id),
        email=learner.email,
        display_name=learner.display_name,
        verified=learner.verified_at is not None,
    )


def issue_token(
    response: Response,
    db: Session,
    *,
    learner: Learner,
    device_label: str | None,
    expose_token: bool = True,
) -> SessionResponse:
    session = create_learner_session(db, learner_id=learner.id, device_label=device_label)
    db.commit()
    db.refresh(session)
    token = create_session_token(session_id=session.id, secret=get_session_secret())
    set_auth_cookies(response, token)
    return SessionResponse(
        access_token=token if expose_token else None, learner_id=str(learner.id)
    )


@router.post(
    "/register",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_auth_rate_limit())],
)
def register(
    request: RegisterRequest,
    response: Response,
    db: Db,
    bearer: bool = Query(default=True),
) -> SessionResponse:
    email = request.email.lower()
    if db.scalar(select(Learner).where(Learner.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    learner_id = uuid4()
    learner = Learner(
        id=learner_id, owner_id=learner_id, email=email, display_name=request.display_name
    )
    learner.password_hash = hash_password(request.password)
    db.add(learner)
    db.flush()
    # kick off email verification right away (provider logs when SMTP unset)
    from app.services.account_actions import request_email_verification

    try:
        request_email_verification(db, owner_id=learner.id)
    except Exception:
        logger = logging.getLogger(__name__)
        logger.exception("post-registration verification email failed")
    return issue_token(
        response, db, learner=learner, device_label=request.device_label, expose_token=bearer
    )


@router.post(
    "/login",
    response_model=SessionResponse,
    dependencies=[Depends(_auth_rate_limit())],
)
def login(
    request: LoginRequest,
    response: Response,
    db: Db,
    bearer: bool = Query(default=True),
) -> SessionResponse:
    learner = db.scalar(select(Learner).where(Learner.email == request.email.lower()))
    if (
        learner is None
        or learner.password_hash is None
        or not verify_password(request.password, learner.password_hash)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return issue_token(
        response, db, learner=learner, device_label=request.device_label, expose_token=bearer
    )


@router.get("/me", response_model=LearnerResponse)
def me(learner: CurrentLearner) -> LearnerResponse:
    return learner_response(learner)


@router.post("/signout")
def signout(session: CurrentSession, response: Response, db: Db) -> dict[str, str]:
    revoke_session(db, session_id=session.id, owner_id=session.owner_id)
    db.commit()
    clear_auth_cookies(response)
    return {"detail": "Signed out"}


@router.patch("/profile", response_model=LearnerResponse)
def profile(request: ProfileUpdateRequest, learner: CurrentLearner, db: Db) -> LearnerResponse:
    updated = update_profile(
        db, learner, email=request.email, display_name=request.display_name
    )
    return learner_response(updated)


@router.post("/password")
def password(
    request: PasswordChangeRequest, learner: CurrentLearner, session: CurrentSession, db: Db
) -> dict[str, str]:
    change_password(
        db,
        learner,
        current_password=request.current_password,
        new_password=request.new_password,
        current_session_id=session.id,
    )
    return {"detail": "Password changed"}


@router.get("/sessions", response_model=list[SessionRecord])
def sessions(learner: CurrentLearner, session: CurrentSession, db: Db) -> list[SessionRecord]:
    active = list_active_sessions(db, owner_id=learner.id, current_session_id=session.id)
    return [
        SessionRecord(
            id=str(item.id),
            device_label=item.device_label,
            is_current=item.id == session.id,
            created_at=item.created_at,
        )
        for item in active
    ]


@router.post("/sessions/{session_id}/revoke")
def revoke(
    session_id: UUID, learner: CurrentLearner, session: CurrentSession, db: Db
) -> dict[str, str]:
    if session_id == session.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use sign-out to end the current session",
        )
    if not revoke_session(db, session_id=session_id, owner_id=learner.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    db.commit()
    return {"detail": "Session signed out"}


@router.post("/password-reset/request", dependencies=[Depends(_auth_rate_limit())])
def password_reset_request(request: PasswordResetRequest, db: Db) -> dict[str, str]:
    request_password_reset(db, email=request.email)
    return {"detail": "If that email is registered, a reset link has been sent"}


@router.post("/password-reset/confirm", dependencies=[Depends(_auth_rate_limit())])
def password_reset_confirm(request: PasswordResetConfirm, db: Db) -> dict[str, str]:
    try:
        confirm_password_reset(
            db,
            email=request.email,
            token=request.token,
            new_password=request.new_password,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"detail": "Password updated. All devices signed out."}


@router.post("/verify-email/request", dependencies=[Depends(_auth_rate_limit())])
def email_verify_request(learner: CurrentLearner, db: Db) -> dict[str, str]:
    request_email_verification(db, owner_id=learner.id)
    return {"detail": "If your email is not yet verified, a verification link has been sent"}


@router.post("/verify-email/confirm", dependencies=[Depends(_auth_rate_limit())])
def email_verify_confirm(request: EmailVerifyConfirm, db: Db) -> dict[str, str]:
    try:
        confirm_email_verification(db, email=request.email, token=request.token)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"detail": "Email verified"}
