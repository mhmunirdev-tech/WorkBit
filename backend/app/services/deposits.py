from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DepositRequest, User, Wallet, WalletTransaction
from app.schemas.deposits import DepositCreate
from app.services.packages import has_active_package


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
        raise HTTPException(
            410,
            "Standalone deposits are no longer available. Choose a package and submit its manual payment.",
        )

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
