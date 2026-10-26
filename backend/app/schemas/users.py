from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class AdminUserRead(BaseModel):
    id: str
    full_name: str
    email: str
    country: str
    phone_number: str | None
    status: str
    email_verified: bool
    created_at: datetime
    available_balance: Decimal
    pending_balance: Decimal
    lifetime_earned: Decimal
    lifetime_withdrawn: Decimal
    currency: str
    active_package: bool
    package_expires_at: datetime | None


class AdminUserListRead(BaseModel):
    items: list[AdminUserRead]
    total: int
    registered_count: int
    page: int
    page_size: int
    active_count: int
    pending_verification_count: int
    suspended_count: int
    active_package_count: int
    total_wallet_balance: Decimal
