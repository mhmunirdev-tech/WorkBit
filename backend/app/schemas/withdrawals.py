from datetime import datetime
from decimal import Decimal
from typing import Literal
import re

from pydantic import BaseModel, Field, field_validator


class WithdrawalCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=8)
    account_id: str = Field(min_length=36, max_length=36)
    payment_method: Literal["BKASH", "NAGAD"]
    code: str = Field(pattern=r"^\d{6}$")


class PayoutAccountOtpRequest(BaseModel):
    method: Literal["BKASH", "NAGAD"]
    destination: str = Field(min_length=6, max_length=32)
    account_id: str | None = Field(default=None, min_length=36, max_length=36)

    @field_validator("destination")
    @classmethod
    def clean_mobile_banking_destination(cls, value: str) -> str:
        return normalize_mobile_banking_destination(value)


class PayoutAccountCreate(PayoutAccountOtpRequest):
    code: str = Field(pattern=r"^\d{6}$")


class WithdrawalOtpRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=8)
    account_id: str = Field(min_length=36, max_length=36)


def normalize_mobile_banking_destination(value: str) -> str:
    normalized = value.strip()
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
    return normalized


class PayoutAccountRead(BaseModel):
    id: str
    method: Literal["BKASH", "NAGAD"]
    destination_hint: str
    updated_at: datetime


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
    payment_transaction_id: str | None = None
    paid_at: datetime | None = None
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


class WithdrawalPayment(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=128)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("transaction_id")
    @classmethod
    def clean_transaction_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or any(ord(character) < 32 for character in normalized):
            raise ValueError("Enter a valid payment transaction ID.")
        return normalized


class PayoutSettingsRead(BaseModel):
    usd_bdt_rate: Decimal | None
    minimum_withdrawal_usd: Decimal


class PayoutSettingsUpdate(BaseModel):
    usd_bdt_rate: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
