from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_permission
from app.core.config import settings
from app.database.session import get_db
from app.models import PackagePurchase, PayoutSettings, RewardDecision, Role, User, Wallet, WalletTransaction, WithdrawalRequest
from app.schemas.dashboard import (
    DashboardEarningDay,
    DashboardRead,
    DashboardStats,
    DashboardTransaction,
    DashboardUser,
    DashboardWithdrawalRequest,
    DashboardWithdrawalSummary,
    PublicStatsRead,
)
from app.services.packages import current_package_expiry, has_active_package

router = APIRouter(tags=["dashboards"])

_EARNING_TYPES = {
    "OFFER_REWARD_APPROVAL",
    "REFERRAL_REWARD_APPROVAL",
    "DAILY_BONUS_APPROVAL",
    "DAILY_BONUS_REWARD",
    "ACHIEVEMENT_REWARD_APPROVAL",
    "ACHIEVEMENT_REWARD",
}
_REFERRAL_TYPES = {"REFERRAL_REWARD_APPROVAL", "REFERRAL_REWARD_PENDING"}
_APPROVED_STATUSES = {"APPROVED", "COMPLETED"}


@router.get("/public/stats", response_model=PublicStatsRead)
def public_stats(db: Session = Depends(get_db)) -> PublicStatsRead:
    now = datetime.now(timezone.utc)
    registered_users = db.scalar(
        select(func.count(func.distinct(User.id)))
        .join(User.roles)
        .where(Role.name == "USER")
    ) or 0
    total_payouts_bdt = db.scalar(
        select(func.coalesce(func.sum(WithdrawalRequest.payout_amount), Decimal("0"))).where(
            WithdrawalRequest.status == "COMPLETED",
            WithdrawalRequest.payout_currency == "BDT",
        )
    ) or Decimal("0")
    active_packages = db.scalar(
        select(func.count(PackagePurchase.id)).where(
            PackagePurchase.status == "APPROVED",
            PackagePurchase.expires_at > now,
        )
    ) or 0
    decided_offers = db.scalar(
        select(func.count(RewardDecision.id)).where(
            RewardDecision.status.in_(("APPROVED", "REJECTED"))
        )
    ) or 0
    approved_offers = db.scalar(
        select(func.count(RewardDecision.id)).where(
            RewardDecision.status == "APPROVED"
        )
    ) or 0

    return PublicStatsRead(
        registered_users=registered_users,
        total_payouts_bdt=total_payouts_bdt,
        active_packages=active_packages,
        offer_approval_rate=(
            Decimal(approved_offers) * Decimal("100") / Decimal(decided_offers)
            if decided_offers
            else None
        ),
    )


@router.get("/dashboard", response_model=DashboardRead)
def dashboard(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> DashboardRead:
    wallet = user.wallet
    now = datetime.now(timezone.utc)
    today = now.date()
    cutoff = datetime.combine(today - timedelta(days=89), time.min, timezone.utc)

    transactions = db.execute(
        select(WalletTransaction.created_at, WalletTransaction.amount)
        .where(
            WalletTransaction.user_id == user.id,
            WalletTransaction.currency == wallet.currency,
            WalletTransaction.created_at >= cutoff,
            WalletTransaction.type.in_(_EARNING_TYPES),
            WalletTransaction.status.in_(_APPROVED_STATUSES),
            WalletTransaction.amount > 0,
        )
        .order_by(WalletTransaction.created_at.desc())
    ).all()
    earning_totals: dict[date, Decimal] = {}
    today_earnings = Decimal("0")
    week_earnings = Decimal("0")
    month_earnings = Decimal("0")
    for created_at, amount in transactions:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        transaction_date = created_at.astimezone(timezone.utc).date()
        earning_totals[transaction_date] = (
            earning_totals.get(transaction_date, Decimal("0")) + amount
        )
        if transaction_date == today:
            today_earnings += amount
        if transaction_date >= today - timedelta(days=6):
            week_earnings += amount
        if transaction_date >= today - timedelta(days=29):
            month_earnings += amount

    referral_earnings = db.scalar(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
            WalletTransaction.user_id == user.id,
            WalletTransaction.currency == wallet.currency,
            WalletTransaction.type.in_(_REFERRAL_TYPES),
            WalletTransaction.status.in_(_APPROVED_STATUSES),
        )
    ) or Decimal("0")
    pending_referral_earnings = db.scalar(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
            WalletTransaction.user_id == user.id,
            WalletTransaction.currency == wallet.currency,
            WalletTransaction.type.in_(_REFERRAL_TYPES),
            WalletTransaction.status == "PENDING",
        )
    ) or Decimal("0")

    recent_transactions = db.scalars(
        select(WalletTransaction)
        .where(WalletTransaction.user_id == user.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(6)
    ).all()
    latest_withdrawal = db.scalar(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.user_id == user.id)
        .order_by(WithdrawalRequest.created_at.desc())
        .limit(1)
    )
    latest_package_purchase = db.scalar(
        select(PackagePurchase)
        .where(PackagePurchase.user_id == user.id)
        .order_by(PackagePurchase.created_at.desc())
        .limit(1)
    )
    pending_withdrawal = (
        latest_withdrawal
        if latest_withdrawal and latest_withdrawal.status in {"PENDING", "PROCESSING"}
        else None
    )
    payout_settings = db.get(PayoutSettings, "default")
    referral_count = db.scalar(
        select(func.count(User.id)).where(User.referred_by == user.id)
    ) or 0
    completed_package_purchases = (
        select(PackagePurchase.user_id)
        .where(
            PackagePurchase.status == "APPROVED",
            PackagePurchase.amount > 0,
            PackagePurchase.expires_at > now,
        )
        .distinct()
    )
    active_referral_count = db.scalar(
        select(func.count(User.id)).where(
            User.referred_by == user.id,
            User.status == "ACTIVE",
            User.email_verified.is_(True),
            User.id.in_(completed_package_purchases),
        )
    ) or 0
    completed_offers = db.scalar(
        select(func.count(RewardDecision.id)).where(
            RewardDecision.user_id == user.id,
            RewardDecision.status == "APPROVED",
        )
    ) or 0

    return DashboardRead(
        available_balance=wallet.available_balance,
        withdrawable_balance=wallet.available_balance - wallet.deposit_balance,
        deposit_balance=wallet.deposit_balance,
        earning_balance=wallet.available_balance - wallet.deposit_balance,
        pending_balance=wallet.pending_balance,
        lifetime_earned=wallet.lifetime_earned,
        lifetime_withdrawn=wallet.lifetime_withdrawn,
        currency=wallet.currency,
        package_active=has_active_package(db, user.id),
        package_purchase_status=(
            latest_package_purchase.status if latest_package_purchase else None
        ),
        package_expires_at=current_package_expiry(db, user.id),
        user=DashboardUser(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            country=user.country,
            status=user.status,
            email_verified=user.email_verified,
            avatar_url=user.profile.avatar_url if user.profile else None,
            referral_code=user.referral_code,
            referral_url=(
                f"{settings.frontend_origin.rstrip('/')}/register"
                f"?referral={user.referral_code}"
            ),
            created_at=user.created_at,
        ),
        stats=DashboardStats(
            completed_offers=completed_offers,
            referrals=referral_count,
            active_referrals=active_referral_count,
            today_earnings=today_earnings,
            week_earnings=week_earnings,
            month_earnings=month_earnings,
            referral_earnings=referral_earnings,
            pending_referral_earnings=pending_referral_earnings,
        ),
        earnings_chart=[
            DashboardEarningDay(
                date=(today - timedelta(days=offset)).isoformat(),
                amount=earning_totals.get(
                    today - timedelta(days=offset), Decimal("0")
                ),
            )
            for offset in range(89, -1, -1)
        ],
        recent_transactions=[
            DashboardTransaction(
                id=transaction.id,
                type=transaction.type,
                amount=transaction.amount,
                currency=transaction.currency,
                status=transaction.status,
                description=transaction.description,
                created_at=transaction.created_at,
            )
            for transaction in recent_transactions
        ],
        withdrawal_summary=DashboardWithdrawalSummary(
            enabled=bool(
                settings.withdrawal_encryption_configured
                and payout_settings
                and payout_settings.usd_bdt_rate
                and payout_settings.usd_bdt_rate > 0
            ),
            minimum_amount=settings.withdrawal_minimum_amount,
            usd_bdt_rate=payout_settings.usd_bdt_rate if payout_settings else None,
            pending_request=(
                DashboardWithdrawalRequest(
                    id=pending_withdrawal.id,
                    amount=pending_withdrawal.amount,
                    currency=pending_withdrawal.currency,
                    payout_amount=pending_withdrawal.payout_amount,
                    payout_currency=pending_withdrawal.payout_currency,
                    status=pending_withdrawal.status,
                    created_at=pending_withdrawal.created_at,
                )
                if pending_withdrawal
                else None
            ),
            last_request=(
                DashboardWithdrawalRequest(
                    id=latest_withdrawal.id,
                    amount=latest_withdrawal.amount,
                    currency=latest_withdrawal.currency,
                    payout_amount=latest_withdrawal.payout_amount,
                    payout_currency=latest_withdrawal.payout_currency,
                    status=latest_withdrawal.status,
                    created_at=latest_withdrawal.created_at,
                )
                if latest_withdrawal
                else None
            ),
        ),
    )


@router.get("/admin/dashboard")
def admin_dashboard(_: User = Depends(require_permission("users.view")), db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(User)) or 0
    active = db.scalar(select(func.count()).select_from(User).where(User.status == "ACTIVE")) or 0
    pending = db.scalar(select(func.count()).select_from(User).where(User.status == "PENDING_VERIFICATION")) or 0
    balance = db.scalar(select(func.coalesce(func.sum(Wallet.available_balance), Decimal("0")))) or Decimal("0")
    platform_ad_revenue = db.scalar(
        select(func.coalesce(func.sum(RewardDecision.platform_share), Decimal("0"))).where(
            RewardDecision.status == "APPROVED",
            RewardDecision.currency == "USD",
        )
    ) or Decimal("0")
    registered_user_amount = db.scalar(
        select(func.coalesce(func.sum(PackagePurchase.amount), Decimal("0"))).where(
            PackagePurchase.status == "APPROVED",
            PackagePurchase.currency == "USD",
            PackagePurchase.payment_method != "WALLET",
        )
    ) or Decimal("0")
    return {
        "total_users": total,
        "active_users": active,
        "pending_verification": pending,
        "total_wallet_balance": str(balance),
        "platform_ad_revenue": str(platform_ad_revenue),
        "registered_user_amount": str(registered_user_amount),
        "currency": "USD",
    }
