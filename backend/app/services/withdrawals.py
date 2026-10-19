from __future__ import annotations

import base64
import binascii
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AdminLog, PayoutSettings, User, UserPayoutAccount, Wallet, WalletTransaction, WithdrawalRequest

OUTSTANDING_STATUSES = {"PENDING", "PROCESSING"}
AAD_PREFIX = b"workbit-withdrawal-destination:v1:"
PAYOUT_ACCOUNT_AAD_PREFIX = b"workbit-payout-account:v1:"


def _cipher() -> AESGCM:
    encoded_key = settings.withdrawal_encryption_key
    if not encoded_key:
        raise HTTPException(503, "Withdrawal requests are not configured.")
    try:
        key = base64.b64decode(encoded_key.encode("ascii"), altchars=b"-_", validate=True)
    except (binascii.Error, UnicodeEncodeError, ValueError) as error:
        logging.error("withdrawal encryption key is not valid URL-safe base64")
        raise HTTPException(503, "Withdrawal requests are unavailable due to a key configuration error.") from error
    if len(key) != 32:
        logging.error("withdrawal encryption key must decode to exactly 32 bytes")
        raise HTTPException(503, "Withdrawal requests are unavailable due to a key configuration error.")
    return AESGCM(key)


def _encrypt_destination(user_id: str, destination: str) -> str:
    nonce = os.urandom(12)
    ciphertext = _cipher().encrypt(nonce, destination.encode("utf-8"), AAD_PREFIX + user_id.encode())
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def _decrypt_destination(withdrawal: WithdrawalRequest) -> str:
    try:
        payload = base64.urlsafe_b64decode(withdrawal.destination_ciphertext.encode("ascii"))
        if len(payload) < 29:
            raise ValueError("Encrypted destination is truncated.")
        return _cipher().decrypt(
            payload[:12],
            payload[12:],
            AAD_PREFIX + withdrawal.user_id.encode(),
        ).decode("utf-8")
    except (InvalidTag, UnicodeDecodeError, ValueError) as error:
        logging.exception("withdrawal destination could not be decrypted withdrawal_id=%s", withdrawal.id)
        raise HTTPException(503, "Payout details are unavailable for secure processing.") from error


def _encrypt_payout_account(user_id: str, method: str, destination: str) -> str:
    nonce = os.urandom(12)
    aad = PAYOUT_ACCOUNT_AAD_PREFIX + user_id.encode() + b":" + method.encode()
    ciphertext = _cipher().encrypt(nonce, destination.encode("utf-8"), aad)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def _decrypt_payout_account(account: UserPayoutAccount) -> str:
    try:
        payload = base64.urlsafe_b64decode(account.destination_ciphertext.encode("ascii"))
        if len(payload) < 29:
            raise ValueError("Encrypted payout account is truncated.")
        aad = PAYOUT_ACCOUNT_AAD_PREFIX + account.user_id.encode() + b":" + account.method.encode()
        return _cipher().decrypt(payload[:12], payload[12:], aad).decode("utf-8")
    except (InvalidTag, UnicodeDecodeError, ValueError) as error:
        logging.exception("payout account could not be decrypted account_id=%s", account.id)
        raise HTTPException(503, "Saved payout details are unavailable for secure processing.") from error


def _request_read(withdrawal: WithdrawalRequest) -> dict:
    return {
        "id": withdrawal.id,
        "amount": withdrawal.amount,
        "currency": withdrawal.currency,
        "payout_amount": withdrawal.payout_amount,
        "payout_currency": withdrawal.payout_currency,
        "exchange_rate": withdrawal.exchange_rate,
        "method": withdrawal.method,
        "destination_hint": withdrawal.destination_hint,
        "status": withdrawal.status,
        "payment_transaction_id": withdrawal.payment_transaction_id,
        "paid_at": withdrawal.paid_at,
        "admin_note": withdrawal.admin_note,
        "created_at": withdrawal.created_at,
        "updated_at": withdrawal.updated_at,
    }


def _audit(
    db: Session,
    admin: User,
    action: str,
    withdrawal: WithdrawalRequest,
    request: Request,
    metadata: dict | None = None,
) -> None:
    db.add(
        AdminLog(
            admin_id=admin.id,
            action=action,
            target_type="withdrawal",
            target_id=withdrawal.id,
            metadata_json=json.dumps(metadata or {}),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:512] or None,
        )
    )


class WithdrawalService:
    def list_payout_accounts(self, db: Session, user: User) -> list[UserPayoutAccount]:
        return db.scalars(
            select(UserPayoutAccount)
            .where(UserPayoutAccount.user_id == user.id)
            .order_by(UserPayoutAccount.method)
        ).all()

    def save_payout_account(
        self,
        db: Session,
        user: User,
        method: str,
        destination: str,
        account_id: str | None = None,
    ) -> UserPayoutAccount:
        db.scalar(select(User.id).where(User.id == user.id).with_for_update())
        account = None
        if account_id is not None:
            account = db.scalar(
                select(UserPayoutAccount).where(
                    UserPayoutAccount.id == account_id,
                    UserPayoutAccount.user_id == user.id,
                    UserPayoutAccount.method == method,
                )
            )
            if account is None:
                raise HTTPException(404, "Saved payout account not found.")
            for existing in self.list_payout_accounts(db, user):
                if (
                    existing.id != account.id
                    and existing.method == method
                    and _decrypt_payout_account(existing) == destination
                ):
                    raise HTTPException(409, "This payout number is already saved.")
        else:
            count = db.scalar(
                select(func.count())
                .select_from(UserPayoutAccount)
                .where(
                    UserPayoutAccount.user_id == user.id,
                    UserPayoutAccount.method == method,
                )
            )
            if count >= 2:
                raise HTTPException(409, f"You can save up to two {method.title()} accounts.")
            for existing in self.list_payout_accounts(db, user):
                if existing.method == method and _decrypt_payout_account(existing) == destination:
                    raise HTTPException(409, "This payout number is already saved.")
            account = UserPayoutAccount(user_id=user.id, method=method)
        account.destination_ciphertext = _encrypt_payout_account(user.id, method, destination)
        account.destination_hint = f"••••{destination[-4:]}"
        account.updated_at = datetime.now(timezone.utc)
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    def delete_payout_account(self, db: Session, user: User, account_id: str) -> None:
        account = db.scalar(
            select(UserPayoutAccount).where(
                UserPayoutAccount.id == account_id,
                UserPayoutAccount.user_id == user.id,
            )
        )
        if account is None:
            raise HTTPException(404, "Saved payout account not found.")
        db.delete(account)
        db.commit()

    def validate_request(
        self,
        db: Session,
        user: User,
        amount: Decimal,
        account_id: str,
        payment_method: str,
        lock_wallet: bool = False,
    ) -> tuple[Wallet, Decimal, UserPayoutAccount, str]:
        if user.status != "ACTIVE" or not user.email_verified:
            raise HTTPException(403, "Verify your email and activate your account before requesting a withdrawal.")
        wallet_query = select(Wallet).where(Wallet.user_id == user.id)
        if lock_wallet:
            wallet_query = wallet_query.with_for_update()
        wallet = db.scalar(wallet_query)
        if wallet is None:
            raise HTTPException(409, "Your wallet is unavailable.")
        payout_settings = db.get(PayoutSettings, "default")
        exchange_rate = payout_settings.usd_bdt_rate if payout_settings else None
        if exchange_rate is None or exchange_rate <= 0:
            raise HTTPException(503, "Withdrawals are unavailable until WorkBit configures the USD to BDT exchange rate.")
        if wallet.currency.upper() != "USD":
            raise HTTPException(409, "Mobile banking payouts are currently available for USD wallets only.")
        minimum_withdrawal = payout_settings.minimum_withdrawal_usd
        if amount < minimum_withdrawal:
            raise HTTPException(400, f"The minimum request is {minimum_withdrawal} USD.")

        outstanding = db.scalar(
            select(WithdrawalRequest.id)
            .where(
                WithdrawalRequest.user_id == user.id,
                WithdrawalRequest.status.in_(OUTSTANDING_STATUSES),
            )
            .limit(1)
        )
        if outstanding:
            raise HTTPException(409, "You already have a withdrawal being reviewed.")
        withdrawable_balance = wallet.available_balance - wallet.deposit_balance
        if amount > withdrawable_balance:
            raise HTTPException(400, "The requested amount exceeds your withdrawable earnings balance.")

        account = db.scalar(
            select(UserPayoutAccount).where(
                UserPayoutAccount.id == account_id,
                UserPayoutAccount.user_id == user.id,
                UserPayoutAccount.method == payment_method,
            )
        )
        if account is None:
            raise HTTPException(400, "Choose one of your saved payout accounts.")
        return wallet, exchange_rate, account, _decrypt_payout_account(account)

    def create(
        self,
        db: Session,
        user: User,
        amount: Decimal,
        account_id: str,
        payment_method: str,
    ) -> WithdrawalRequest:
        wallet, exchange_rate, _account, destination = self.validate_request(
            db, user, amount, account_id, payment_method, lock_wallet=True
        )

        encrypted_destination = _encrypt_destination(user.id, destination)
        before = wallet.available_balance
        wallet.available_balance -= amount
        withdrawal = WithdrawalRequest(
            user_id=user.id,
            amount=amount,
            currency=wallet.currency,
            payout_amount=(amount * exchange_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            payout_currency="BDT",
            exchange_rate=exchange_rate,
            method=payment_method,
            destination_ciphertext=encrypted_destination,
            destination_hint=f"••••{destination[-4:]}",
            status="PENDING",
        )
        db.add(withdrawal)
        db.flush()
        db.add(
            WalletTransaction(
                wallet_id=wallet.id,
                user_id=user.id,
                type="WITHDRAWAL_REQUEST",
                amount=-amount,
                currency=wallet.currency,
                status="APPROVED",
                reference_type="withdrawal",
                reference_id=withdrawal.id,
                description="Withdrawal request reserved",
                metadata_json=json.dumps({"withdrawal_id": withdrawal.id}),
                balance_before=before,
                balance_after=wallet.available_balance,
            )
        )
        db.commit()
        db.refresh(withdrawal)
        return withdrawal

    def list_for_user(self, db: Session, user: User) -> list[WithdrawalRequest]:
        return db.scalars(
            select(WithdrawalRequest)
            .where(WithdrawalRequest.user_id == user.id)
            .order_by(WithdrawalRequest.created_at.desc())
        ).all()

    def list_for_admin(self, db: Session) -> list[WithdrawalRequest]:
        return db.scalars(
            select(WithdrawalRequest)
            .order_by(WithdrawalRequest.created_at.desc())
        ).all()

    def admin_detail(
        self,
        db: Session,
        withdrawal_id: str,
        admin: User,
        request: Request,
    ) -> dict:
        withdrawal = db.get(WithdrawalRequest, withdrawal_id)
        if withdrawal is None:
            raise HTTPException(404, "Withdrawal request not found.")
        _audit(db, admin, "WITHDRAWAL_DESTINATION_VIEWED", withdrawal, request)
        db.commit()
        return {
            **_request_read(withdrawal),
            "user_id": withdrawal.user_id,
            "user_email": withdrawal.user.email,
            "user_name": withdrawal.user.full_name,
            "destination": _decrypt_destination(withdrawal),
            "reviewed_by": withdrawal.reviewed_by,
            "reviewed_at": withdrawal.reviewed_at,
        }

    def review(
        self,
        db: Session,
        withdrawal_id: str,
        admin: User,
        request: Request,
        action: str,
        note: str | None,
        transaction_id: str | None = None,
    ) -> WithdrawalRequest:
        withdrawal = db.scalar(
            select(WithdrawalRequest)
            .where(WithdrawalRequest.id == withdrawal_id)
            .with_for_update()
        )
        if withdrawal is None:
            raise HTTPException(404, "Withdrawal request not found.")
        if action == "approve":
            if withdrawal.status != "PENDING":
                raise HTTPException(409, "Only pending withdrawals can be approved.")
            wallet = db.scalar(
                select(Wallet).where(Wallet.user_id == withdrawal.user_id).with_for_update()
            )
            if wallet is None:
                raise HTTPException(409, "The user's wallet is unavailable.")
            wallet.lifetime_withdrawn += withdrawal.amount
            withdrawal.status = "PAID"
            withdrawal.paid_at = datetime.now(timezone.utc)
        elif action == "reject":
            if withdrawal.status not in OUTSTANDING_STATUSES:
                raise HTTPException(409, "Only outstanding withdrawals can be rejected.")
            wallet = db.scalar(
                select(Wallet).where(Wallet.user_id == withdrawal.user_id).with_for_update()
            )
            if wallet is None:
                raise HTTPException(409, "The user's wallet is unavailable.")
            before = wallet.available_balance
            wallet.available_balance += withdrawal.amount
            db.add(
                WalletTransaction(
                    wallet_id=wallet.id,
                    user_id=withdrawal.user_id,
                    type="WITHDRAWAL_RELEASE",
                    amount=withdrawal.amount,
                    currency=withdrawal.currency,
                    status="APPROVED",
                    reference_type="withdrawal",
                    reference_id=withdrawal.id,
                    description="Rejected withdrawal funds released",
                    metadata_json=json.dumps({"withdrawal_id": withdrawal.id}),
                    balance_before=before,
                    balance_after=wallet.available_balance,
                )
            )
            withdrawal.status = "REJECTED"
        elif action == "complete":
            if withdrawal.status != "PROCESSING":
                raise HTTPException(409, "Only processing withdrawals can be completed.")
            if not transaction_id:
                raise HTTPException(422, "A payment transaction ID is required to mark a withdrawal as paid.")
            wallet = db.scalar(
                select(Wallet).where(Wallet.user_id == withdrawal.user_id).with_for_update()
            )
            if wallet is None:
                raise HTTPException(409, "The user's wallet is unavailable.")
            wallet.lifetime_withdrawn += withdrawal.amount
            withdrawal.status = "PAID"
            withdrawal.payment_transaction_id = transaction_id
            withdrawal.paid_at = datetime.now(timezone.utc)
        else:
            raise HTTPException(400, "Unsupported withdrawal action.")

        withdrawal.admin_note = note.strip() if note else None
        withdrawal.reviewed_by = admin.id
        withdrawal.reviewed_at = datetime.now(timezone.utc)
        withdrawal.updated_at = withdrawal.reviewed_at
        _audit(
            db,
            admin,
            f"WITHDRAWAL_{action.upper()}",
            withdrawal,
            request,
            {
                "status": withdrawal.status,
                "amount": str(withdrawal.amount),
                "payment_transaction_id": withdrawal.payment_transaction_id,
            },
        )
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            if action == "complete" and transaction_id:
                raise HTTPException(409, "This payment transaction ID has already been used for this payment method.") from error
            raise
        db.refresh(withdrawal)
        return withdrawal


withdrawal_service = WithdrawalService()
