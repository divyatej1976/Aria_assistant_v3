from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.dependencies import get_db
from app.db.models import Learner, LearnerSession
from app.security.tokens import SessionTokenError, read_session_token

bearer = HTTPBearer(auto_error=False)


def get_current_session(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> LearnerSession:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    settings = get_settings()
    secret = settings.supabase_jwt_secret or "development-only-change-me"
    try:
        session_id = read_session_token(credentials.credentials, secret=secret)
    except SessionTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    session = db.get(LearnerSession, session_id)
    if session is None or session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has been signed out"
        )
    return session


def get_current_learner(
    session: Annotated[LearnerSession, Depends(get_current_session)],
    db: Annotated[Session, Depends(get_db)],
) -> Learner:
    learner = db.get(Learner, session.owner_id)
    if learner is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Learner not found")
    return learner


CurrentLearner = Annotated[Learner, Depends(get_current_learner)]
CurrentSession = Annotated[LearnerSession, Depends(get_current_session)]
