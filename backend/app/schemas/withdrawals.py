from datetime import datetime
from decimal import Decimal
from typing import Literal
import re

from pydantic import BaseModel, Field, field_validator, model_validator


class WithdrawalCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=8)
    destination: str = Field(min_length=6, max_length=512)
    payment_method: Literal["BKASH", "NAGAD", "MANUAL"] = "MANUAL"

    @model_validator(mode="after")
    def clean_mobile_banking_destination(self):
        value = self.destination
        normalized = value.strip()
        if len(normalized) < 6 or any(ord(character) < 32 for character in normalized):
            raise ValueError("Enter a valid payout destination.")
        if self.payment_method in {"BKASH", "NAGAD"}:
            digits = re.sub(r"[\s()+-]", "", normalized)
            if digits.startswith("+8801") and len(digits) == 14:
                normalized = "0" + digits[4:]
            elif digits.startswith("8801") and len(digits) == 13:
                normalized = "0" + digits[3:]
            elif digits.startswith("01") and len(digits) == 11:
                normalized = digits
            else:
                raise ValueError("Enter a valid Bangladesh mobile banking number.")
            if normalized[2] not in "3456789":
                raise ValueError("Enter a valid Bangladesh mobile banking number.")
        self.destination = normalized
        return self


class WithdrawalRead(BaseModel):
    id: str
    amount: Decimal
    currency: str
    payout_amount: Decimal | None = None
    payout_currency: str | None = None
    exchange_rate: Decimal | None = None
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


class PayoutSettingsRead(BaseModel):
    usd_bdt_rate: Decimal | None
    minimum_withdrawal_usd: Decimal


class PayoutSettingsUpdate(BaseModel):
    usd_bdt_rate: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
