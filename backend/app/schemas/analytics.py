from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PageViewCreate(BaseModel):
    visitor_id: UUID
    path: str = Field(min_length=1, max_length=256)
    event_type: Literal["PAGE_VIEW", "VISITOR_PING"] = "PAGE_VIEW"

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        if not value.startswith("/") or value.startswith("//") or "?" in value or "#" in value:
            raise ValueError("Enter a valid page path.")
        return value


class RecentLoginFailure(BaseModel):
    login_type: str | None
    email_masked: str | None
    ip_fingerprint: str | None
    created_at: datetime


class DailyAnalytics(BaseModel):
    date: date
    unique_visitors: int
    page_views: int
    failed_logins: int


class AdminAnalyticsRead(BaseModel):
    active_visitors: int
    unique_visitors_today: int
    page_views_today: int
    failed_logins_24h: int
    recent_failed_logins: list[RecentLoginFailure]
    daily: list[DailyAnalytics]
