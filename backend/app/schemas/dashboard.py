from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class DashboardUser(BaseModel):
    id: str
    full_name: str
    email: str
    country: str
    status: str
    email_verified: bool
    avatar_url: str | None = None
    referral_code: str
    referral_url: str
    created_at: datetime


class DashboardStats(BaseModel):
    completed_offers: int
    referrals: int
    active_referrals: int
    today_earnings: Decimal
    week_earnings: Decimal
    month_earnings: Decimal
    referral_earnings: Decimal
    pending_referral_earnings: Decimal


class DashboardEarningDay(BaseModel):
    date: str
    amount: Decimal


class DashboardTransaction(BaseModel):
    id: str
    type: str
    amount: Decimal
    currency: str
    status: str
    description: str
    created_at: datetime


class DashboardWithdrawalRequest(BaseModel):
    id: str
    amount: Decimal
    currency: str
    status: str
    created_at: datetime


class DashboardWithdrawalSummary(BaseModel):
    enabled: bool
    minimum_amount: Decimal
    pending_request: DashboardWithdrawalRequest | None = None
    last_request: DashboardWithdrawalRequest | None = None


class DashboardRead(BaseModel):
    available_balance: Decimal
    pending_balance: Decimal
    lifetime_earned: Decimal
    lifetime_withdrawn: Decimal
    currency: str
    user: DashboardUser
    stats: DashboardStats
    earnings_chart: list[DashboardEarningDay]
    recent_transactions: list[DashboardTransaction]
    withdrawal_summary: DashboardWithdrawalSummary
