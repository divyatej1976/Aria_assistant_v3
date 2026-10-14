"""Notifications: exam reminders and the daily digest.

Emails are sent through SMTP when configured, otherwise logged to the console
so the feature is usable in development without credentials. Reminder checks
are triggered on demand via the planner endpoint; a background scheduler
arrives with production hardening.
"""

import logging
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Concept,
    Deadline,
    Learner,
    LearnerConceptState,
    LearnerPreference,
    Note,
    Notification,
    PlannedTask,
    RevisionItem,
)
from app.services.learner_state import STATE_DEVELOPING, STATE_NEEDS_REVIEW, STATE_SUPPORTED
from app.services.progress import learner_timezone

logger = logging.getLogger(__name__)

DIGEST_PREFERENCE_KEY = "digest_last_sent"
EMAIL_PREFERENCE_KEY = "email_reminders"


def get_preference(db: Session, *, owner_id: UUID, key: str) -> str | None:
    preference = db.scalar(
        select(LearnerPreference).where(
            LearnerPreference.owner_id == owner_id, LearnerPreference.key == key
        )
    )
    return preference.value if preference else None


def set_preference(db: Session, *, owner_id: UUID, key: str, value: str) -> None:
    preference = db.scalar(
        select(LearnerPreference).where(
            LearnerPreference.owner_id == owner_id, LearnerPreference.key == key
        )
    )
    if preference is None:
        db.add(LearnerPreference(owner_id=owner_id, key=key, value=value))
    else:
        preference.value = value
        db.add(preference)


class SmtpEmailProvider:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        from_addr: str,
        use_tls: bool,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.use_tls = use_tls

    def send(self, *, recipient: str, subject: str, body: str) -> str:
        message = EmailMessage()
        message["From"] = self.from_addr
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(self.host, self.port, timeout=15) as server:
            if self.use_tls:
                server.starttls()
            if self.username:
                server.login(self.username, self.password)
            server.send_message(message)
        return "delivered"


class LogEmailProvider:
    def send(self, *, recipient: str, subject: str, body: str) -> str:
        # Never log message bodies: password-reset / verify links carry
        # signed single-use tokens. Metadata only.
        logger.info("email to=%s subject=%s body_len=%d", recipient, subject, len(body))
        return "logged"


def get_email_provider():
    settings = get_settings()
    if settings.smtp_host:
        return SmtpEmailProvider(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            from_addr=settings.smtp_from,
            use_tls=settings.smtp_use_tls,
        )
    return LogEmailProvider()


def email_enabled(db: Session, *, owner_id: UUID) -> bool:
    return get_preference(db, owner_id=owner_id, key=EMAIL_PREFERENCE_KEY) != "off"


def create_notification(
    db: Session, *, owner_id: UUID, ntype: str, title: str, body: str
) -> Notification:
    notification = Notification(
        owner_id=owner_id, ntype=ntype, title=title, body=body
    )
    db.add(notification)
    return notification


def list_notifications(db: Session, *, owner_id: UUID) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.owner_id == owner_id)
            .order_by(Notification.created_at.desc())
            .limit(50)
        )
    )


def mark_all_notifications_read(db: Session, *, owner_id: UUID) -> int:
    unread = db.scalars(
        select(Notification).where(
            Notification.owner_id == owner_id, Notification.read_at.is_(None)
        )
    ).all()
    for notification in unread:
        notification.read_at = datetime.now(UTC)
        db.add(notification)
    db.commit()
    return len(unread)


def dispatch_notification(
    db: Session, *, owner_id: UUID, ntype: str, title: str, body: str, send_email: bool = False
) -> dict[str, int]:
    """In-app + web push (and optionally email) delivery for a new notification."""
    create_notification(db, owner_id=owner_id, ntype=ntype, title=title, body=body)
    db.commit()
    from app.services.push import send_push

    push = send_push(db, owner_id=owner_id, title=title, body=body)
    result = {
        "push_sent": push["sent"],
        "push_logged": push["logged"],
        "push_failed": push["failed"],
        "push_removed": push["removed"],
        "email_sent": 0,
        "email_logged": 0,
        "email_failed": 0,
    }
    if send_email:
        learner = db.get(Learner, owner_id)
        if learner is not None and email_enabled(db, owner_id=owner_id):
            status = _send_email(
                get_email_provider(), email=learner.email, subject=title, body=body
            )
            key = f"email_{status}"
            if key in result:
                result[key] += 1
    return result


def mark_notification_read(
    db: Session, *, owner_id: UUID, notification_id: UUID
) -> Notification | None:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.owner_id == owner_id,
        )
    )
    if notification is not None and notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.add(notification)
        db.commit()
    return notification


def syllabus_progress(db: Session, *, owner_id: UUID, context_id: UUID) -> dict[str, int]:
    supported = db.scalar(
        select(func.count(LearnerConceptState.id))
        .join(Concept, Concept.id == LearnerConceptState.concept_id)
        .where(
            LearnerConceptState.owner_id == owner_id,
            Concept.context_id == context_id,
            LearnerConceptState.state == STATE_SUPPORTED,
        )
    ) or 0
    total_concepts = db.scalar(
        select(func.count(Concept.id)).where(
            Concept.owner_id == owner_id, Concept.context_id == context_id
        )
    ) or 0
    tasks_done = db.scalar(
        select(func.count(PlannedTask.id)).where(
            PlannedTask.owner_id == owner_id,
            PlannedTask.context_id == context_id,
            PlannedTask.status == "DONE",
        )
    ) or 0
    tasks_total = db.scalar(
        select(func.count(PlannedTask.id)).where(
            PlannedTask.owner_id == owner_id, PlannedTask.context_id == context_id
        )
    ) or 0
    return {
        "supported": supported,
        "total_concepts": total_concepts,
        "tasks_done": tasks_done,
        "tasks_total": tasks_total,
    }


def what_to_study(db: Session, *, owner_id: UUID, context_id: UUID, limit: int = 5) -> list[str]:
    rows = db.execute(
        select(Concept.name, LearnerConceptState.state)
        .join(LearnerConceptState, LearnerConceptState.concept_id == Concept.id)
        .where(
            LearnerConceptState.owner_id == owner_id,
            Concept.context_id == context_id,
            LearnerConceptState.state.in_((STATE_NEEDS_REVIEW, STATE_DEVELOPING)),
        )
        .order_by(Concept.name)
        .limit(limit)
    ).all()
    return [name for name, _state in rows]


def due_revision_titles(db: Session, *, owner_id: UUID, limit: int = 5) -> list[str]:
    rows = db.execute(
        select(Note.title)
        .join(RevisionItem, RevisionItem.note_id == Note.id)
        .where(
            RevisionItem.owner_id == owner_id,
            RevisionItem.next_review_at <= datetime.now(UTC),
        )
        .order_by(RevisionItem.next_review_at)
        .limit(limit)
    ).all()
    return [title for title, in rows]


def build_exam_message(
    deadline: "Deadline",
    progress: dict[str, int],
    study_next: list[str],
    days_left: int,
) -> tuple[str, str]:
    concepts = f"{progress['supported']} of {progress['total_concepts']} concepts supported"
    tasks = f"{progress['tasks_done']} of {progress['tasks_total']} planned tasks done"
    subject = f"ARIA: {deadline.title} in {days_left} day{'s' if days_left != 1 else ''}"
    body = (
        f"Your {deadline.title} is in {days_left} day(s).\n\n"
        f"Syllabus so far: {concepts}; {tasks}.\n"
    )
    if study_next:
        body += "Study next:\n" + "\n".join(f"- {item}" for item in study_next) + "\n"
    return subject, body


def build_digest_message(
    missed: list[PlannedTask], revisions: list[str]
) -> tuple[str, str]:
    lines: list[str] = []
    if missed:
        lines.append("Missed planned work:")
        lines.extend(f"- {task.title}" for task in missed)
    if revisions:
        lines.append("Revision due:")
        lines.extend(f"- {title}" for title in revisions)
    return "ARIA: Your learning digest", "\n".join(lines) + "\n"


def _send_email(provider, *, email: str, subject: str, body: str) -> str:
    try:
        return provider.send(recipient=email, subject=subject, body=body)
    except Exception:
        logger.exception("email delivery failed to=%s subject=%s", email, subject)
        return "failed"


def check_reminders_for_all(db: Session) -> dict[str, int]:
    """Run reminder checks for every learner. Used by the background scheduler."""
    totals = {
        "notifications_created": 0,
        "emails_delivered": 0,
        "emails_logged": 0,
        "emails_failed": 0,
    }
    learner_ids = db.scalars(select(Learner.id)).all()
    for owner_id in learner_ids:
        result = check_reminders(db, owner_id=owner_id)
        for key in totals:
            totals[key] += result[key]
    return totals


def check_reminders(
    db: Session, *, owner_id: UUID, provider=None
) -> dict[str, int]:
    provider = provider or get_email_provider()
    learner = db.scalar(select(Learner).where(Learner.id == owner_id))
    email = learner.email if learner else None
    send_email = email is not None and email_enabled(db, owner_id=owner_id)
    tz = learner_timezone(db, owner_id=owner_id)
    now = datetime.now(tz)

    notifications_created = 0
    emails_delivered = 0
    emails_logged = 0
    emails_failed = 0

    def deliver(subject: str, body: str) -> None:
        nonlocal emails_delivered, emails_logged, emails_failed
        if not send_email:
            return
        status = _send_email(provider, email=email, subject=subject, body=body)
        if status == "delivered":
            emails_delivered += 1
        elif status == "logged":
            emails_logged += 1
        else:
            emails_failed += 1

    deadlines = db.scalars(
        select(Deadline).where(
            Deadline.owner_id == owner_id, Deadline.status == "ACTIVE"
        )
    ).all()
    for deadline in deadlines:
        days_left = (deadline.due_at.astimezone(tz).date() - now.date()).days
        if not (0 <= days_left <= deadline.reminder_days_before):
            continue
        sent = deadline.reminder_sent_days_before
        if sent is not None and sent != -1:
            continue
        if sent is None:
            progress = syllabus_progress(db, owner_id=owner_id, context_id=deadline.context_id)
            study_next = what_to_study(db, owner_id=owner_id, context_id=deadline.context_id)
            subject, body = build_exam_message(deadline, progress, study_next, days_left)
            create_notification(
                db, owner_id=owner_id, ntype="deadline", title=subject, body=body
            )
            notifications_created += 1
        else:
            progress = syllabus_progress(db, owner_id=owner_id, context_id=deadline.context_id)
            study_next = what_to_study(db, owner_id=owner_id, context_id=deadline.context_id)
            subject, body = build_exam_message(deadline, progress, study_next, days_left)
        failed_before = emails_failed
        deliver(subject, body)
        deadline.reminder_sent_days_before = -1 if emails_failed > failed_before else days_left
        db.add(deadline)

    today = now.date().isoformat()
    if get_preference(db, owner_id=owner_id, key=DIGEST_PREFERENCE_KEY) != today:
        missed = list(
            db.scalars(
                select(PlannedTask).where(
                    PlannedTask.owner_id == owner_id,
                    PlannedTask.status == "PENDING",
                    PlannedTask.due_at.is_not(None),
                    PlannedTask.due_at < now,
                )
            )
        )
        revisions = due_revision_titles(db, owner_id=owner_id)
        if missed or revisions:
            subject, body = build_digest_message(missed, revisions)
            create_notification(db, owner_id=owner_id, ntype="digest", title=subject, body=body)
            notifications_created += 1
            deliver(subject, body)
            set_preference(db, owner_id=owner_id, key=DIGEST_PREFERENCE_KEY, value=today)

    db.commit()
    return {
        "notifications_created": notifications_created,
        "emails_delivered": emails_delivered,
        "emails_logged": emails_logged,
        "emails_failed": emails_failed,
    }
