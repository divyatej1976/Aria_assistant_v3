from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.models import (
    AdaptationDecision,
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AttemptAnswer,
    Concept,
    ConversationMessage,
    Evaluation,
    Evidence,
    Goal,
    Learner,
    LearnerConceptState,
    LearnerSession,
    LearningContext,
    Resource,
    ResourceChunk,
    StudySession,
)
from app.security.passwords import hash_password, verify_password

_DATA_TABLES = (
    AdaptationDecision,
    LearnerConceptState,
    Evidence,
    Evaluation,
    AttemptAnswer,
    AssessmentAttempt,
    AssessmentQuestion,
    Assessment,
    ConversationMessage,
    StudySession,
    ResourceChunk,
    Resource,
    Concept,
    LearningContext,
    Goal,
)


def create_learner_session(
    db: Session, *, learner_id: UUID, device_label: str | None
) -> LearnerSession:
    session = LearnerSession(owner_id=learner_id, device_label=device_label)
    db.add(session)
    db.flush()
    return session


def revoke_session(db: Session, *, session_id: UUID, owner_id: UUID) -> bool:
    result = db.execute(
        update(LearnerSession)
        .where(LearnerSession.id == session_id, LearnerSession.owner_id == owner_id)
        .values(revoked_at=datetime.now(UTC))
    )
    return result.rowcount > 0


def list_active_sessions(
    db: Session, *, owner_id: UUID, current_session_id: UUID
) -> list[LearnerSession]:
    return list(
        db.scalars(
            select(LearnerSession)
            .where(LearnerSession.owner_id == owner_id, LearnerSession.revoked_at.is_(None))
            .order_by(LearnerSession.created_at)
        )
    )


def update_profile(
    db: Session, learner: Learner, *, email: str | None, display_name: str | None
) -> Learner:
    if email is not None and email != learner.email:
        existing = db.scalar(select(Learner).where(Learner.email == email))
        if existing is not None and existing.id != learner.id:
            raise ValidationError("Email is already registered")
        learner.email = email
    if display_name is not None:
        learner.display_name = display_name
    db.add(learner)
    db.commit()
    db.refresh(learner)
    return learner


def change_password(
    db: Session,
    learner: Learner,
    *,
    current_password: str,
    new_password: str,
    current_session_id: UUID,
) -> None:
    if learner.password_hash is None or not verify_password(
        current_password, learner.password_hash
    ):
        raise ValidationError("Current password is incorrect")
    learner.password_hash = hash_password(new_password)
    db.add(learner)
    db.execute(
        update(LearnerSession)
        .where(
            LearnerSession.owner_id == learner.id,
            LearnerSession.id != current_session_id,
            LearnerSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    db.commit()


def reset_learner_data(db: Session, *, owner_id: UUID) -> None:
    for table in _DATA_TABLES:
        db.execute(delete(table).where(table.owner_id == owner_id))
    db.execute(
        update(LearnerSession)
        .where(LearnerSession.owner_id == owner_id)
        .values(revoked_at=datetime.now(UTC))
    )
    db.commit()
