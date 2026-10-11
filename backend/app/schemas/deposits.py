from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DepositCreate(BaseModel):
    amount_bdt: Decimal = Field(ge=100, max_digits=12, decimal_places=2)
    payment_method: Literal["BKASH", "NAGAD"]
    payment_reference: str = Field(min_length=5, max_length=120)

    @field_validator("payment_reference")
    @classmethod
    def normalize_reference(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5 or any(ord(character) < 32 for character in normalized):
            raise ValueError("Enter a valid payment transaction reference.")
        return normalized.upper()


class DepositRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    amount_bdt: Decimal
    amount: Decimal
    currency: str
    exchange_rate: Decimal
    payment_method: str
    payment_reference: str
    status: str
    admin_note: str | None
    created_at: datetime
    reviewed_at: datetime | None


class AdminDepositRead(DepositRead):
    user_id: str
    user_name: str
    user_email: str


class DepositReview(BaseModel):
    note: str | None = Field(default=None, max_length=500)
