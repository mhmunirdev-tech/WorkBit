from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class FraudEventRead(BaseModel):
    id: str
    user_id: str | None
    user_email: str | None
    event_type: str
    risk_level: str
    status: str
    reason: str
    evidence: dict[str, object]
    ip_fingerprint: str | None
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime


class FraudOverviewRead(BaseModel):
    open_medium: int
    open_high: int
    under_review: int
    confirmed: int
    events_today: int


class FraudEventReview(BaseModel):
    status: Literal["UNDER_REVIEW", "CLEARED", "CONFIRMED"]
    note: str = Field(min_length=3, max_length=500)

    @field_validator("note", mode="before")
    @classmethod
    def trim_note(cls, value):
        return value.strip() if isinstance(value, str) else value


class FraudAccountAction(BaseModel):
    status: Literal["PENDING_REVIEW", "SUSPENDED", "BANNED", "ACTIVE"]
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value):
        return value.strip() if isinstance(value, str) else value


class FraudAppealCodeRequest(BaseModel):
    email: EmailStr


class FraudAppealSubmit(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")
    statement: str = Field(min_length=20, max_length=1000)

    @field_validator("statement", mode="before")
    @classmethod
    def trim_statement(cls, value):
        return value.strip() if isinstance(value, str) else value
