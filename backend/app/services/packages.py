from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import DepositRequest, EarningPackage, PackagePurchase, PaymentReference, PayoutSettings, User, Wallet, WalletTransaction
from app.schemas.packages import PackagePurchaseCreate, WalletPackagePurchaseCreate

INITIAL_PACKAGES = (
    ("BASIC", "Basic", "For test update to feature", Decimal("10.00"), 365, 10),
    ("STANDARD", "Standard", "For test", Decimal("50.00"), 730, 20),
    ("PREMIUM", "Premium", "For test", Decimal("100.00"), 1095, 30),
    ("VIP", "VIP", "Package Duration", Decimal("550.00"), 1095, 40),
    ("VIP_PRO", "VIP Pro", "Details", Decimal("1000.00"), 1825, 50),
    ("FOUNDER", "Founder", "Package Duration", Decimal("500.00"), 3650, 60),
)
REFERRAL_COMMISSION_RATE = Decimal("0.05")
REFERRAL_COMMISSION_TYPE = "REFERRAL_REWARD_APPROVAL"
REFERRAL_COMMISSION_PRECISION = Decimal("0.00000001")


def seed_earning_packages(db: Session) -> None:
    for code, name, description, amount, duration_days, sort_order in INITIAL_PACKAGES:
        if db.get(EarningPackage, code) is None:
            db.add(
                EarningPackage(
                    code=code,
                    name=name,
                    description=description,
                    amount=amount,
                    currency="USD",
                    duration_days=duration_days,
                    is_active=True,
                    sort_order=sort_order,
                )
            )
    db.flush()


def package_read(package: EarningPackage) -> dict:
    return {
        "code": package.code,
        "name": package.name,
        "description": package.description,
        "amount": package.amount,
        "currency": package.currency,
        "duration_days": package.duration_days,
        "is_active": package.is_active,
        "sort_order": package.sort_order,
    }


def get_active_package(db: Session, package_code: str) -> EarningPackage:
    package = db.get(EarningPackage, package_code)
    if package is None or not package.is_active:
        raise HTTPException(404, "This earning package is unavailable.")
    return package


def has_active_package(db: Session, user_id: str) -> bool:
    return db.scalar(
        select(PackagePurchase.id)
        .where(
            PackagePurchase.user_id == user_id,
            PackagePurchase.status == "APPROVED",
            PackagePurchase.expires_at > datetime.now(timezone.utc),
        )
        .limit(1)
    ) is not None


def current_package_expiry(db: Session, user_id: str) -> datetime | None:
    return db.scalar(
        select(PackagePurchase.expires_at)
        .where(
            PackagePurchase.user_id == user_id,
            PackagePurchase.status == "APPROVED",
            PackagePurchase.expires_at > datetime.now(timezone.utc),
        )
        .order_by(PackagePurchase.expires_at.desc())
        .limit(1)
    )


def package_purchase_read(purchase: PackagePurchase) -> dict:
    return {
        "id": purchase.id,
        "package_code": purchase.package_code,
        "package_name": purchase.package_name,
        "amount": purchase.amount,
        "duration_days": purchase.duration_days,
        "deposit_amount": purchase.deposit_amount,
        "earning_amount": purchase.earning_amount,
        "currency": purchase.currency,
        "payment_amount_bdt": purchase.payment_amount_bdt,
        "usd_bdt_rate": purchase.usd_bdt_rate,
        "payment_method": purchase.payment_method,
        "payment_reference": purchase.payment_reference,
        "status": purchase.status,
        "admin_note": purchase.admin_note,
        "created_at": purchase.created_at,
        "reviewed_at": purchase.reviewed_at,
        "starts_at": purchase.starts_at,
        "expires_at": purchase.expires_at,
    }


class PackageService:
    def catalog(self, db: Session, user: User) -> dict:
        latest_purchase = db.scalar(
            select(PackagePurchase)
            .where(PackagePurchase.user_id == user.id)
            .order_by(PackagePurchase.created_at.desc())
            .limit(1)
        )
        wallet = user.wallet or db.scalar(select(Wallet).where(Wallet.user_id == user.id))
        expiry = current_package_expiry(db, user.id)
        payout_settings = db.get(PayoutSettings, "default")
        exchange_rate = payout_settings.usd_bdt_rate if payout_settings else None
        packages = [
            package_read(package)
            for package in db.scalars(
                select(EarningPackage)
                .where(EarningPackage.is_active.is_(True))
                .order_by(EarningPackage.sort_order, EarningPackage.code)
            ).all()
        ]
        for package in packages:
            package["payment_amount_bdt"] = (
                (package["amount"] * exchange_rate).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
                if exchange_rate is not None and exchange_rate > 0
                else None
            )
        return {
            "packages": packages,
            "payment_instructions": {
                "BKASH": settings.package_bkash_number,
                "NAGAD": settings.package_nagad_number,
            },
            "usd_bdt_rate": exchange_rate,
            "package_active": has_active_package(db, user.id),
            "package_expires_at": expiry,
            "wallet_balance": wallet.available_balance if wallet else Decimal("0"),
            "deposit_balance": wallet.deposit_balance if wallet else Decimal("0"),
            "earning_balance": wallet.available_balance - wallet.deposit_balance if wallet else Decimal("0"),
            "latest_purchase": package_purchase_read(latest_purchase) if latest_purchase else None,
        }

    def create_purchase(
        self,
        db: Session,
        user: User,
        data: PackagePurchaseCreate,
    ) -> PackagePurchase:
        if user.status != "ACTIVE" or not user.email_verified:
            raise HTTPException(403, "Verify and activate your account before buying a package.")
        pending = db.scalar(
            select(PackagePurchase.id)
            .where(PackagePurchase.user_id == user.id, PackagePurchase.status == "PENDING")
            .limit(1)
        )
        if pending:
            raise HTTPException(409, "You already have a package payment waiting for review.")
        package = get_active_package(db, data.package_code)
        payout_settings = db.get(PayoutSettings, "default")
        exchange_rate = payout_settings.usd_bdt_rate if payout_settings else None
        if exchange_rate is None or exchange_rate <= 0:
            raise HTTPException(
                503,
                "Package payments are unavailable until WorkBit configures the USD to BDT exchange rate.",
            )
        payment_account = (
            settings.package_bkash_number
            if data.payment_method == "BKASH"
            else settings.package_nagad_number
        ).strip()
        if not payment_account:
            raise HTTPException(
                503,
                f"{data.payment_method.title()} package payments are temporarily unavailable.",
            )
        reused_deposit = db.scalar(
            select(DepositRequest.id).where(
                DepositRequest.payment_method == data.payment_method,
                DepositRequest.payment_reference == data.payment_reference,
            ).limit(1)
        )
        if reused_deposit:
            raise HTTPException(409, "This payment reference has already been submitted.")
        purchase = PackagePurchase(
            user_id=user.id,
            package_code=data.package_code,
            package_name=package.name,
            amount=package.amount,
            duration_days=package.duration_days,
            currency=package.currency,
            payment_amount_bdt=(package.amount * exchange_rate).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            ),
            usd_bdt_rate=exchange_rate,
            payment_method=data.payment_method,
            payment_reference=data.payment_reference,
            status="PENDING",
        )
        db.add(purchase)
        try:
            db.flush()
            db.add(
                PaymentReference(
                    payment_method=data.payment_method,
                    payment_reference=data.payment_reference,
                    request_type="PACKAGE",
                    request_id=purchase.id,
                )
            )
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(409, "This payment reference has already been submitted.") from error
        db.refresh(purchase)
        return purchase

    def list_for_admin(self, db: Session) -> list[PackagePurchase]:
        return db.scalars(
            select(PackagePurchase)
            .order_by(
                (PackagePurchase.status == "PENDING").desc(),
                PackagePurchase.created_at.desc(),
            )
            .limit(500)
        ).all()

    def purchase_with_wallet(
        self,
        db: Session,
        user: User,
        data: WalletPackagePurchaseCreate,
    ) -> PackagePurchase:
        raise HTTPException(
            410,
            "Wallet purchases are no longer available. Choose a package and submit its manual payment.",
        )

    def review(
        self,
        db: Session,
        purchase_id: str,
        admin: User,
        status: str,
        note: str | None,
    ) -> PackagePurchase:
        purchase = db.scalar(
            select(PackagePurchase)
            .where(PackagePurchase.id == purchase_id)
            .with_for_update()
        )
        if purchase is None:
            raise HTTPException(404, "Package purchase not found.")
        if purchase.status != "PENDING":
            raise HTTPException(409, "Only pending package payments can be reviewed.")
        purchase.status = status
        purchase.admin_note = note.strip() if note and note.strip() else None
        purchase.reviewed_by = admin.id
        purchase.reviewed_at = datetime.now(timezone.utc)
        if status == "APPROVED":
            self._set_package_term(db, purchase)
            self._credit_referral_commission(db, purchase)
        db.commit()
        db.refresh(purchase)
        return purchase

    @staticmethod
    def _credit_referral_commission(db: Session, purchase: PackagePurchase) -> None:
        referred_user = db.get(User, purchase.user_id)
        if referred_user is None or referred_user.referred_by is None:
            return

        existing_commission = db.scalar(
            select(WalletTransaction.id).where(
                WalletTransaction.type == REFERRAL_COMMISSION_TYPE,
                WalletTransaction.reference_type == "package_purchase",
                WalletTransaction.reference_id == purchase.id,
            )
        )
        if existing_commission:
            return

        referrer_wallet = db.scalar(
            select(Wallet)
            .where(Wallet.user_id == referred_user.referred_by)
            .with_for_update()
        )
        if referrer_wallet is None:
            raise HTTPException(409, "The referring account wallet is unavailable.")
        if referrer_wallet.currency.upper() != purchase.currency.upper():
            raise HTTPException(409, "The package currency does not match the referring account wallet.")

        commission = (purchase.amount * REFERRAL_COMMISSION_RATE).quantize(
            REFERRAL_COMMISSION_PRECISION,
            rounding=ROUND_HALF_UP,
        )
        if commission <= 0:
            return

        before = referrer_wallet.available_balance
        referrer_wallet.available_balance += commission
        referrer_wallet.lifetime_earned += commission
        db.add(
            WalletTransaction(
                wallet_id=referrer_wallet.id,
                user_id=referrer_wallet.user_id,
                type=REFERRAL_COMMISSION_TYPE,
                amount=commission,
                currency=referrer_wallet.currency,
                status="APPROVED",
                reference_type="package_purchase",
                reference_id=purchase.id,
                description=f"5% referral commission for {purchase.package_name} package",
                metadata_json=json.dumps(
                    {
                        "purchase_id": purchase.id,
                        "referred_user_id": purchase.user_id,
                        "package_amount": str(purchase.amount),
                        "commission_rate": str(REFERRAL_COMMISSION_RATE),
                    }
                ),
                balance_before=before,
                balance_after=referrer_wallet.available_balance,
            )
        )

    @staticmethod
    def _set_package_term(db: Session, purchase: PackagePurchase) -> None:
        now = datetime.now(timezone.utc)
        prior_expiry = db.scalar(
            select(PackagePurchase.expires_at)
            .where(
                PackagePurchase.user_id == purchase.user_id,
                PackagePurchase.status == "APPROVED",
                PackagePurchase.id != purchase.id,
                PackagePurchase.expires_at > now,
            )
            .order_by(PackagePurchase.expires_at.desc())
            .limit(1)
        )
        starts_at = prior_expiry if prior_expiry and prior_expiry > now else now
        purchase.starts_at = starts_at
        purchase.expires_at = starts_at + timedelta(days=purchase.duration_days)


package_service = PackageService()
