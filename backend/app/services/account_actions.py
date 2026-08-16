"""Account actions: password reset and email verification via signed tokens."""

import hashlib
import logging
from datetime import UTC, datetime
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.models import Learner, LearnerSession
from app.security.passwords import hash_password
from app.security.secrets import get_session_secret
from app.security.tokens import (
    SessionTokenError,
    create_action_token,
    read_action_token,
)

logger = logging.getLogger(__name__)

PASSWORD_RESET_PURPOSE = "password_reset"
EMAIL_VERIFY_PURPOSE = "email_verify"
RESET_TTL_SECONDS = 3600  # 1 hour


def _public_url() -> str:
    return get_settings().aria_public_url.rstrip("/")


def _binding(learner: Learner) -> str:
    # Ties a password-reset token to the current password hash so the token is
    # single-use: once the password changes, the old token no longer validates.
    return hashlib.sha256((learner.password_hash or "").encode()).hexdigest()


def _send_email(provider, *, recipient: str, subject: str, body: str) -> None:
    try:
        provider.send(recipient=recipient, subject=subject, body=body)
    except Exception:
        logger.exception("account email delivery failed to=%s subject=%s", recipient, subject)


def request_password_reset(db: Session, *, email: str, provider=None) -> None:
    """Send a password-reset link if the email is registered. Never reveals existence."""
    from app.services.notifications import get_email_provider

    learner = db.scalar(select(Learner).where(Learner.email == email.lower()))
    if learner is None or learner.password_hash is None:
        return
    token = create_action_token(
        secret=get_session_secret(),
        purpose=PASSWORD_RESET_PURPOSE,
        email=learner.email,
        ttl_seconds=RESET_TTL_SECONDS,
        binding=_binding(learner),
    )
    link = (
        f"{_public_url()}/reset-password?email={quote(learner.email)}&token={quote(token)}"
    )
    body = (
        "A password reset was requested for your ARIA account.\n\n"
        f"Reset link: {link}\n\n"
        "This link expires in 1 hour. If you did not request this, ignore this email."
    )
    _send_email(
        provider or get_email_provider(),
        recipient=learner.email,
        subject="ARIA: Reset your password",
        body=body,
    )


def confirm_password_reset(
    db: Session, *, email: str, token: str, new_password: str
) -> None:
    learner = db.scalar(select(Learner).where(Learner.email == email.lower()))
    if learner is None or learner.password_hash is None:
        raise ValidationError("Account not found")
    try:
        read_action_token(
            token,
            secret=get_session_secret(),
            purpose=PASSWORD_RESET_PURPOSE,
            email=email,
            binding=_binding(learner),
        )
    except SessionTokenError as exc:
        raise ValidationError(str(exc)) from exc
    learner.password_hash = hash_password(new_password)
    db.add(learner)
    db.execute(
        update(LearnerSession)
        .where(LearnerSession.owner_id == learner.id, LearnerSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    db.commit()


def request_email_verification(db: Session, *, owner_id: UUID, provider=None) -> None:
    from app.services.notifications import get_email_provider

    learner = db.get(Learner, owner_id)
    if learner is None or learner.verified_at is not None:
        return
    token = create_action_token(
        secret=get_session_secret(),
        purpose=EMAIL_VERIFY_PURPOSE,
        email=learner.email,
        ttl_seconds=RESET_TTL_SECONDS,
    )
    link = f"{_public_url()}/verify-email?email={quote(learner.email)}&token={quote(token)}"
    body = (
        "Verify your ARIA email address by opening:\n\n"
        f"{link}\n\n"
        "This link expires in 1 hour."
    )
    _send_email(
        provider or get_email_provider(),
        recipient=learner.email,
        subject="ARIA: Verify your email",
        body=body,
    )


def confirm_email_verification(db: Session, *, email: str, token: str) -> None:
    learner = db.scalar(select(Learner).where(Learner.email == email.lower()))
    if learner is None:
        raise ValidationError("Account not found")
    if learner.verified_at is not None:
        return
    try:
        read_action_token(
            token,
            secret=get_session_secret(),
            purpose=EMAIL_VERIFY_PURPOSE,
            email=email,
        )
    except SessionTokenError as exc:
        raise ValidationError(str(exc)) from exc
    learner.verified_at = datetime.now(UTC)
    db.add(learner)
    db.commit()
