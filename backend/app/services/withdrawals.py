from __future__ import annotations

import base64
import binascii
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AdminLog, User, Wallet, WalletTransaction, WithdrawalRequest

OUTSTANDING_STATUSES = {"PENDING", "PROCESSING"}
AAD_PREFIX = b"workbit-withdrawal-destination:v1:"


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


def _request_read(withdrawal: WithdrawalRequest) -> dict:
    return {
        "id": withdrawal.id,
        "amount": withdrawal.amount,
        "currency": withdrawal.currency,
        "method": withdrawal.method,
        "destination_hint": withdrawal.destination_hint,
        "status": withdrawal.status,
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
    def create(
        self,
        db: Session,
        user: User,
        amount: Decimal,
        destination: str,
    ) -> WithdrawalRequest:
        if user.status != "ACTIVE" or not user.email_verified:
            raise HTTPException(403, "Verify your email and activate your account before requesting a withdrawal.")
        if amount < settings.withdrawal_minimum_amount:
            raise HTTPException(400, f"The minimum withdrawal is {settings.withdrawal_minimum_amount} {user.wallet.currency}.")

        encrypted_destination = _encrypt_destination(user.id, destination)
        wallet = db.scalar(
            select(Wallet).where(Wallet.user_id == user.id).with_for_update()
        )
        if wallet is None:
            raise HTTPException(409, "Your wallet is unavailable.")

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
        if amount > wallet.available_balance:
            raise HTTPException(400, "The requested amount exceeds your available balance.")

        before = wallet.available_balance
        wallet.available_balance -= amount
        withdrawal = WithdrawalRequest(
            user_id=user.id,
            amount=amount,
            currency=wallet.currency,
            method="MANUAL",
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
            withdrawal.status = "PROCESSING"
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
            wallet = db.scalar(
                select(Wallet).where(Wallet.user_id == withdrawal.user_id).with_for_update()
            )
            if wallet is None:
                raise HTTPException(409, "The user's wallet is unavailable.")
            wallet.lifetime_withdrawn += withdrawal.amount
            withdrawal.status = "COMPLETED"
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
            {"status": withdrawal.status, "amount": str(withdrawal.amount)},
        )
        db.commit()
        db.refresh(withdrawal)
        return withdrawal


withdrawal_service = WithdrawalService()
