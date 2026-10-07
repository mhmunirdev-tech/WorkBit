from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class WithdrawalCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=8)
    destination: str = Field(min_length=6, max_length=512)

    @field_validator("destination")
    @classmethod
    def clean_destination(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 6 or any(ord(character) < 32 for character in normalized):
            raise ValueError("Enter a valid payout destination.")
        return normalized


class WithdrawalRead(BaseModel):
    id: str
    amount: Decimal
    currency: str
    method: str
    destination_hint: str
    status: str
    created_at: datetime
    updated_at: datetime


class AdminWithdrawalRead(WithdrawalRead):
    user_id: str
    user_email: str
    user_name: str
    destination: str
    admin_note: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class WithdrawalDecision(BaseModel):
    note: str | None = Field(default=None, max_length=500)
