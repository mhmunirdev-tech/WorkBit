from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import DepositRequest, PackagePurchase, PaymentReference, PayoutSettings, User, Wallet, WalletTransaction
from app.schemas.deposits import DepositCreate
from app.services.packages import has_active_package

MINIMUM_DEPOSIT_BDT = Decimal("100.00")
WALLET_PRECISION = Decimal("0.00000001")


def deposit_read(deposit: DepositRequest) -> dict:
    return {
        "id": deposit.id,
        "amount_bdt": deposit.amount_bdt,
        "amount": deposit.amount,
        "currency": deposit.currency,
        "exchange_rate": deposit.exchange_rate,
        "payment_method": deposit.payment_method,
        "payment_reference": deposit.payment_reference,
        "status": deposit.status,
        "admin_note": deposit.admin_note,
        "created_at": deposit.created_at,
        "reviewed_at": deposit.reviewed_at,
    }


class DepositService:
    def create(self, db: Session, user: User, data: DepositCreate) -> DepositRequest:
        if user.status != "ACTIVE" or not user.email_verified:
            raise HTTPException(403, "Verify your email before depositing funds.")
        if has_active_package(db, user.id):
            raise HTTPException(409, "Deposits are available only when you do not have an active earning package.")
        pending_package = db.scalar(
            select(PackagePurchase.id).where(
                PackagePurchase.user_id == user.id,
                PackagePurchase.status == "PENDING",
            ).limit(1)
        )
        if pending_package:
            raise HTTPException(409, "Wait for your pending package payment to be reviewed before depositing.")
        pending_deposit = db.scalar(
            select(DepositRequest.id).where(
                DepositRequest.user_id == user.id,
                DepositRequest.status == "PENDING",
            ).limit(1)
        )
        if pending_deposit:
            raise HTTPException(409, "You already have a deposit waiting for review.")
        if data.amount_bdt < MINIMUM_DEPOSIT_BDT:
            raise HTTPException(400, "The minimum deposit is BDT 100.")
        payout_settings = db.get(PayoutSettings, "default")
        exchange_rate = payout_settings.usd_bdt_rate if payout_settings else None
        if exchange_rate is None or exchange_rate <= 0:
            raise HTTPException(503, "Deposits are unavailable until WorkBit configures the USD to BDT exchange rate.")
        duplicate_package_reference = db.scalar(
            select(PackagePurchase.id).where(
                PackagePurchase.payment_method == data.payment_method,
                PackagePurchase.payment_reference == data.payment_reference,
            ).limit(1)
        )
        if duplicate_package_reference:
            raise HTTPException(409, "This payment reference has already been submitted.")
        deposit = DepositRequest(
            user_id=user.id,
            amount_bdt=data.amount_bdt,
            amount=(data.amount_bdt / exchange_rate).quantize(WALLET_PRECISION, rounding=ROUND_HALF_UP),
            currency="USD",
            exchange_rate=exchange_rate,
            payment_method=data.payment_method,
            payment_reference=data.payment_reference,
            status="PENDING",
        )
        db.add(deposit)
        try:
            db.flush()
            db.add(
                PaymentReference(
                    payment_method=data.payment_method,
                    payment_reference=data.payment_reference,
                    request_type="DEPOSIT",
                    request_id=deposit.id,
                )
            )
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(409, "This payment reference has already been submitted.") from error
        db.refresh(deposit)
        return deposit

    def list_for_user(self, db: Session, user: User) -> list[DepositRequest]:
        return db.scalars(
            select(DepositRequest)
            .where(DepositRequest.user_id == user.id)
            .order_by(DepositRequest.created_at.desc())
        ).all()

    def list_for_admin(self, db: Session) -> list[DepositRequest]:
        return db.scalars(
            select(DepositRequest)
            .order_by(
                (DepositRequest.status == "PENDING").desc(),
                DepositRequest.created_at.desc(),
            )
            .limit(500)
        ).all()

    def review(
        self,
        db: Session,
        deposit_id: str,
        admin: User,
        status: str,
        note: str | None,
    ) -> DepositRequest:
        deposit = db.scalar(
            select(DepositRequest)
            .where(DepositRequest.id == deposit_id)
            .with_for_update()
        )
        if deposit is None:
            raise HTTPException(404, "Deposit request not found.")
        if deposit.status != "PENDING":
            raise HTTPException(409, "Only pending deposits can be reviewed.")
        if status == "APPROVED":
            if has_active_package(db, deposit.user_id):
                raise HTTPException(409, "The user has an active earning package; reject this deposit request instead.")
            wallet = db.scalar(
                select(Wallet).where(Wallet.user_id == deposit.user_id).with_for_update()
            )
            if wallet is None:
                raise HTTPException(409, "The user's wallet is unavailable.")
            before = wallet.available_balance
            wallet.available_balance += deposit.amount
            wallet.deposit_balance += deposit.amount
            db.add(
                WalletTransaction(
                    wallet_id=wallet.id,
                    user_id=deposit.user_id,
                    type="DEPOSIT_APPROVAL",
                    amount=deposit.amount,
                    currency=deposit.currency,
                    status="APPROVED",
                    reference_type="deposit_request",
                    reference_id=deposit.id,
                    description=f"{deposit.payment_method} wallet deposit approved",
                    metadata_json=(
                        f'{{"amount_bdt":"{deposit.amount_bdt}",'
                        f'"exchange_rate":"{deposit.exchange_rate}"}}'
                    ),
                    balance_before=before,
                    balance_after=wallet.available_balance,
                )
            )
        elif status != "REJECTED":
            raise HTTPException(400, "Unsupported deposit review action.")

        deposit.status = status
        deposit.admin_note = note.strip() if note and note.strip() else None
        deposit.reviewed_by = admin.id
        deposit.reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(deposit)
        return deposit


deposit_service = DepositService()
