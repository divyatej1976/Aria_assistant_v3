from datetime import UTC, date, datetime

from pydantic import BaseModel, field_validator


class HeatmapDay(BaseModel):
    date: str
    count: int


class ConsistencyResponse(BaseModel):
    current_streak: int
    longest_streak: int
    active_this_week: int
    active_this_month: int
    today_active: bool
    heatmap: list[HeatmapDay]


class BadgeResponse(BaseModel):
    code: str
    label: str
    earned: bool
    earned_at: datetime | None

    @field_validator("earned_at")
    @classmethod
    def assume_utc(cls, value: datetime | None) -> datetime | None:
        # SQLite returns naive UTC; without an offset browsers read it as local time (wrong day).
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


class ActivityResponse(BaseModel):
    id: str
    activity_type: str
    occurred_on: date
    created_at: datetime
