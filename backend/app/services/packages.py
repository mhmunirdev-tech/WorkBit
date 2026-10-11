from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

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
        return {
            "packages": [
                package_read(package)
                for package in db.scalars(
                    select(EarningPackage)
                    .where(EarningPackage.is_active.is_(True))
                    .order_by(EarningPackage.sort_order, EarningPackage.code)
                ).all()
            ],
            "payment_instructions": {
                "BKASH": settings.package_bkash_number,
                "NAGAD": settings.package_nagad_number,
            },
            "usd_bdt_rate": payout_settings.usd_bdt_rate if payout_settings else None,
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
        pending_deposit = db.scalar(
            select(DepositRequest.id).where(
                DepositRequest.user_id == user.id,
                DepositRequest.status == "PENDING",
            ).limit(1)
        )
        if pending_deposit:
            raise HTTPException(409, "Wait for your pending deposit to be reviewed before buying a package.")
        package = get_active_package(db, data.package_code)
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
        if user.status != "ACTIVE" or not user.email_verified:
            raise HTTPException(403, "Verify your email before buying a package.")
        pending_deposit = db.scalar(
            select(DepositRequest.id).where(
                DepositRequest.user_id == user.id,
                DepositRequest.status == "PENDING",
            ).limit(1)
        )
        if pending_deposit:
            raise HTTPException(409, "Wait for your pending deposit to be reviewed before buying a package.")
        package = get_active_package(db, data.package_code)
        wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id).with_for_update())
        if wallet is None:
            raise HTTPException(409, "Your wallet is unavailable.")
        cost = package.amount
        if wallet.available_balance < cost:
            raise HTTPException(400, "Your combined deposit and earnings balance is not enough for this package.")
        deposit_used = min(wallet.deposit_balance, cost)
        earning_used = cost - deposit_used
        wallet.deposit_balance -= deposit_used
        wallet.available_balance -= cost
        purchase = PackagePurchase(
            user_id=user.id,
            package_code=data.package_code,
            package_name=package.name,
            amount=cost,
            duration_days=package.duration_days,
            deposit_amount=deposit_used,
            earning_amount=earning_used,
            currency=wallet.currency,
            payment_method="WALLET",
            payment_reference=f"WALLET-{uuid4().hex.upper()}",
            status="APPROVED",
            reviewed_at=datetime.now(timezone.utc),
        )
        db.add(purchase)
        db.flush()
        db.add(WalletTransaction(
            wallet_id=wallet.id,
            user_id=user.id,
            type="PACKAGE_PURCHASE",
            amount=-cost,
            currency=wallet.currency,
            status="APPROVED",
            reference_type="package_purchase",
            reference_id=purchase.id,
            description=f"{package.name} package purchased from wallet",
            metadata_json=f'{{"deposit_amount":"{deposit_used}","earning_amount":"{earning_used}"}}',
            balance_before=wallet.available_balance + cost,
            balance_after=wallet.available_balance,
        ))
        self._set_package_term(db, purchase)
        db.commit()
        db.refresh(purchase)
        return purchase

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
        db.commit()
        db.refresh(purchase)
        return purchase

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
