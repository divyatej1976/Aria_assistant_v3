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

    def send(self, *, recipient: str, subject: str, body: str) -> None:
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


class LogEmailProvider:
    def send(self, *, recipient: str, subject: str, body: str) -> None:
        logger.info("email to=%s subject=%s body=%s", recipient, subject, body)


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


def check_reminders(db: Session, *, owner_id: UUID) -> dict[str, int]:
    provider = get_email_provider()
    learner = db.scalar(select(Learner).where(Learner.id == owner_id))
    email = learner.email if learner else None
    send_email = email is not None and email_enabled(db, owner_id=owner_id)
    now = datetime.now(UTC)

    notifications_created = 0
    emails_sent = 0

    deadlines = db.scalars(
        select(Deadline).where(
            Deadline.owner_id == owner_id, Deadline.status == "ACTIVE"
        )
    ).all()
    for deadline in deadlines:
        days_left = (deadline.due_at.date() - now.date()).days
        if (
            deadline.reminder_sent_days_before is None
            and 0 <= days_left <= deadline.reminder_days_before
        ):
            progress = syllabus_progress(db, owner_id=owner_id, context_id=deadline.context_id)
            study_next = what_to_study(db, owner_id=owner_id, context_id=deadline.context_id)
            subject, body = build_exam_message(deadline, progress, study_next, days_left)
            create_notification(
                db, owner_id=owner_id, ntype="deadline", title=subject, body=body
            )
            notifications_created += 1
            if send_email:
                provider.send(recipient=email, subject=subject, body=body)
                emails_sent += 1
            deadline.reminder_sent_days_before = days_left
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
            if send_email:
                provider.send(recipient=email, subject=subject, body=body)
                emails_sent += 1
            set_preference(db, owner_id=owner_id, key=DIGEST_PREFERENCE_KEY, value=today)

    db.commit()
    return {"notifications_created": notifications_created, "emails_sent": emails_sent}
