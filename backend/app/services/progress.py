"""Learning progress: meaningful activity, consistency, streaks, and badges.

Activity and consistency can be celebrated, but they must never be confused
with mastery. Streaks are derived only from qualifying learning activities.
"""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    LearnerBadge,
    LearnerConceptState,
    LearnerPreference,
    LearningActivity,
)
from app.services.learner_state import STATE_SUPPORTED

MEANINGFUL_TYPES = frozenset({"assessment", "study", "revision", "planned_task"})

BADGE_CATALOG = [
    ("first_assessment", "First assessment"),
    ("first_study", "First study session"),
    ("first_revision", "First revision"),
    ("first_planned_task", "First planned task completed"),
    ("streak_3", "3-day learning streak"),
    ("streak_7", "7-day learning streak"),
    ("streak_30", "30-day learning streak"),
    ("concept_supported", "First strong concept"),
]

HEATMAP_DAYS = 182


def learner_timezone(db: Session, *, owner_id: UUID) -> ZoneInfo:
    preference = db.scalar(
        select(LearnerPreference).where(
            LearnerPreference.owner_id == owner_id, LearnerPreference.key == "timezone"
        )
    )
    name = preference.value if preference else "UTC"
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def local_today(db: Session, *, owner_id: UUID) -> date:
    return datetime.now(learner_timezone(db, owner_id=owner_id)).date()


def record_activity(
    db: Session,
    *,
    owner_id: UUID,
    activity_type: str,
    source_id: UUID | None = None,
    occurred_on: date | None = None,
) -> None:
    if activity_type not in MEANINGFUL_TYPES:
        return
    day = occurred_on or local_today(db, owner_id=owner_id)
    existing = db.scalar(
        select(LearningActivity.id).where(
            LearningActivity.owner_id == owner_id,
            LearningActivity.activity_type == activity_type,
            LearningActivity.occurred_on == day,
            LearningActivity.source_id == source_id,
        )
    )
    if existing is None:
        db.add(
            LearningActivity(
                owner_id=owner_id,
                activity_type=activity_type,
                occurred_on=day,
                source_id=source_id,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            # Concurrent request recorded the same activity first: the
            # (owner, type, day, source) unique constraint caught the race.
            db.rollback()


def _activity_days(db: Session, *, owner_id: UUID) -> set[date]:
    rows = db.execute(
        select(LearningActivity.occurred_on)
        .where(LearningActivity.owner_id == owner_id)
        .distinct()
    )
    return {row[0] for row in rows}


def activity_count(db: Session, *, owner_id: UUID, day: date) -> int:
    return db.scalar(
        select(func.count(LearningActivity.id)).where(
            LearningActivity.owner_id == owner_id,
            LearningActivity.occurred_on == day,
        )
    ) or 0


def consistency(
    db: Session, *, owner_id: UUID, today: date | None = None
) -> dict[str, object]:
    tz = learner_timezone(db, owner_id=owner_id)
    today = today or datetime.now(tz).date()
    days = _activity_days(db, owner_id=owner_id)

    current = 0
    cursor = today if today in days else today - timedelta(days=1)
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)

    ordered = sorted(days)
    longest = 0
    run = 0
    previous: date | None = None
    for day in ordered:
        run = run + 1 if previous is not None and (day - previous).days == 1 else 1
        longest = max(longest, run)
        previous = day

    active_week = sum(1 for offset in range(7) if (today - timedelta(days=offset)) in days)
    active_month = sum(1 for offset in range(30) if (today - timedelta(days=offset)) in days)

    heatmap = [
        {
            "date": (today - timedelta(days=offset)).isoformat(),
            "count": activity_count(db, owner_id=owner_id, day=today - timedelta(days=offset)),
        }
        for offset in range(HEATMAP_DAYS)
    ]
    heatmap.reverse()

    return {
        "current_streak": current,
        "longest_streak": longest,
        "active_this_week": active_week,
        "active_this_month": active_month,
        "today_active": today in days,
        "heatmap": heatmap,
    }


def sync_badges(
    db: Session, *, owner_id: UUID, today: date | None = None
) -> None:
    stats = consistency(db, owner_id=owner_id, today=today)
    types = set(
        db.scalars(
            select(LearningActivity.activity_type).where(
                LearningActivity.owner_id == owner_id
            )
        )
    )
    supported = db.scalar(
        select(func.count(LearnerConceptState.id)).where(
            LearnerConceptState.owner_id == owner_id,
            LearnerConceptState.state == STATE_SUPPORTED,
        )
    )
    now = datetime.now(UTC)

    def earn(code: str, label: str) -> None:
        existing = db.scalar(
            select(LearnerBadge.id).where(
                LearnerBadge.owner_id == owner_id, LearnerBadge.code == code
            )
        )
        if existing is None:
            db.add(LearnerBadge(owner_id=owner_id, code=code, label=label, earned_at=now))

    if "assessment" in types:
        earn("first_assessment", "First assessment")
    if "study" in types:
        earn("first_study", "First study session")
    if "revision" in types:
        earn("first_revision", "First revision")
    if "planned_task" in types:
        earn("first_planned_task", "First planned task completed")
    for threshold in (3, 7, 30):
        if stats["longest_streak"] >= threshold:
            earn(f"streak_{threshold}", f"{threshold}-day learning streak")
    if (supported or 0) > 0:
        earn("concept_supported", "First strong concept")
    db.commit()


def badges(
    db: Session, *, owner_id: UUID, today: date | None = None
) -> list[dict[str, object]]:
    sync_badges(db, owner_id=owner_id, today=today)
    earned = {
        badge.code: badge
        for badge in db.scalars(
            select(LearnerBadge).where(LearnerBadge.owner_id == owner_id)
        )
    }
    return [
        {
            "code": code,
            "label": label,
            "earned": code in earned,
            "earned_at": earned[code].earned_at if code in earned else None,
        }
        for code, label in BADGE_CATALOG
    ]


def activity_timeline(
    db: Session, *, owner_id: UUID, limit: int = 30
) -> list[LearningActivity]:
    return list(
        db.scalars(
            select(LearningActivity)
            .where(LearningActivity.owner_id == owner_id)
            .order_by(LearningActivity.created_at.desc())
            .limit(limit)
        )
    )
