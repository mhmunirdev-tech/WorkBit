from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PackagePurchaseCreate(BaseModel):
    package_code: str = Field(min_length=1, max_length=32, pattern=r"^[A-Z0-9_]+$")
    payment_method: str = Field(pattern=r"^(BKASH|NAGAD)$")
    payment_reference: str = Field(min_length=5, max_length=120)

    @field_validator("payment_reference")
    @classmethod
    def normalize_reference(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5 or any(ord(character) < 32 for character in normalized):
            raise ValueError("Enter a valid payment transaction reference.")
        return normalized.upper()

class WalletPackagePurchaseCreate(BaseModel):
    package_code: str = Field(min_length=1, max_length=32, pattern=r"^[A-Z0-9_]+$")


class EarningPackageUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=1000)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    duration_days: int = Field(gt=0, le=36500)
    is_active: bool
    sort_order: int = Field(ge=0, le=10000)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Package title cannot be empty.")
        return value

    @field_validator("description")
    @classmethod
    def trim_description(cls, value: str) -> str:
        return value.strip()


class EarningPackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str
    amount: Decimal
    currency: str
    duration_days: int
    is_active: bool
    sort_order: int


class PublicPackageRead(BaseModel):
    code: str
    name: str
    description: str
    amount: Decimal
    currency: str
    duration_days: int


class PackagePurchaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    package_code: str
    package_name: str
    amount: Decimal
    duration_days: int = 30
    deposit_amount: Decimal = Decimal("0")
    earning_amount: Decimal = Decimal("0")
    currency: str
    payment_amount_bdt: Decimal | None = None
    usd_bdt_rate: Decimal | None = None
    payment_method: str
    payment_reference: str
    status: str
    admin_note: str | None
    created_at: datetime
    reviewed_at: datetime | None
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class AdminPackagePurchaseRead(PackagePurchaseRead):
    user_id: str
    user_name: str
    user_email: str


class PackageReview(BaseModel):
    note: str | None = Field(default=None, max_length=500)
