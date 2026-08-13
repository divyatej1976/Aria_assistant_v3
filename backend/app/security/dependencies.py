from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models import Learner, LearnerSession
from app.security.csrf import SESSION_COOKIE
from app.security.secrets import get_session_secret
from app.security.tokens import SessionTokenError, read_session_token

bearer = HTTPBearer(auto_error=False)


def get_current_session(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> LearnerSession:
    token: str | None = None
    if credentials is not None:
        token = credentials.credentials
    else:
        token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    secret = get_session_secret()
    try:
        session_id = read_session_token(token, secret=secret)
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
