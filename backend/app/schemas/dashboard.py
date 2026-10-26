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


class PublicStatsRead(BaseModel):
    registered_users: int
    total_payouts_bdt: Decimal
    active_packages: int
    offer_approval_rate: Decimal | None


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
    payout_amount: Decimal | None = None
    payout_currency: str | None = None
    status: str
    created_at: datetime


class DashboardWithdrawalSummary(BaseModel):
    enabled: bool
    minimum_amount: Decimal
    usd_bdt_rate: Decimal | None = None
    pending_request: DashboardWithdrawalRequest | None = None
    last_request: DashboardWithdrawalRequest | None = None


class DashboardRead(BaseModel):
    available_balance: Decimal
    withdrawable_balance: Decimal
    deposit_balance: Decimal
    earning_balance: Decimal
    reversal_debt: Decimal
    pending_balance: Decimal
    lifetime_earned: Decimal
    lifetime_withdrawn: Decimal
    currency: str
    package_active: bool
    package_purchase_status: str | None
    package_expires_at: datetime | None
    user: DashboardUser
    stats: DashboardStats
    earnings_chart: list[DashboardEarningDay]
    recent_transactions: list[DashboardTransaction]
    withdrawal_summary: DashboardWithdrawalSummary
