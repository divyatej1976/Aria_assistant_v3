from datetime import date, datetime

from pydantic import BaseModel


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


class ActivityResponse(BaseModel):
    id: str
    activity_type: str
    occurred_on: date
    created_at: datetime
