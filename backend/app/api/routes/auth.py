from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.dependencies import get_db
from app.db.models import Learner
from app.schemas.auth import (
    LearnerResponse,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    SessionRecord,
    SessionResponse,
)
from app.security.dependencies import CurrentLearner, CurrentSession
from app.security.passwords import hash_password, verify_password
from app.security.tokens import create_session_token
from app.services.account import (
    change_password,
    create_learner_session,
    list_active_sessions,
    revoke_session,
    update_profile,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
Db = Annotated[Session, Depends(get_db)]


def learner_response(learner: Learner) -> LearnerResponse:
    return LearnerResponse(
        id=str(learner.id), email=learner.email, display_name=learner.display_name
    )


def issue_token(db: Session, *, learner: Learner, device_label: str | None) -> SessionResponse:
    session = create_learner_session(db, learner_id=learner.id, device_label=device_label)
    db.commit()
    db.refresh(session)
    settings = get_settings()
    secret = settings.supabase_jwt_secret or "development-only-change-me"
    token = create_session_token(session_id=session.id, secret=secret)
    return SessionResponse(access_token=token, learner_id=str(learner.id))


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Db) -> SessionResponse:
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
    return issue_token(db, learner=learner, device_label=request.device_label)


@router.post("/login", response_model=SessionResponse)
def login(request: LoginRequest, db: Db) -> SessionResponse:
    learner = db.scalar(select(Learner).where(Learner.email == request.email.lower()))
    if (
        learner is None
        or learner.password_hash is None
        or not verify_password(request.password, learner.password_hash)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return issue_token(db, learner=learner, device_label=request.device_label)


@router.get("/me", response_model=LearnerResponse)
def me(learner: CurrentLearner) -> LearnerResponse:
    return learner_response(learner)


@router.post("/signout")
def signout(session: CurrentSession, db: Db) -> dict[str, str]:
    revoke_session(db, session_id=session.id, owner_id=session.owner_id)
    db.commit()
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
