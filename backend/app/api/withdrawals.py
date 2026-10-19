import json
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_permission
from app.core.config import settings
from app.database.session import get_db
from app.models import AdminLog, PayoutSettings, User, UserPayoutAccount, WithdrawalRequest
from app.schemas.withdrawals import (
    AdminWithdrawalRead,
    PayoutSettingsRead,
    PayoutSettingsUpdate,
    WithdrawalCreate,
    WithdrawalDecision,
    WithdrawalPayment,
    WithdrawalOtpRequest,
    WithdrawalRead,
)
from app.services.auth import consume_action_code, issue_action_code
from app.services.email import EmailDeliveryError, email_service
from app.services.rate_limit import enforce_cooldown
from app.services.withdrawals import _request_read, withdrawal_service

router = APIRouter(tags=["withdrawals"])
WITHDRAWAL_OTP_PURPOSE = "WITHDRAWAL_REQUEST"
OTP_RESEND_COOLDOWN_SECONDS = 60


def _withdrawal_code_context(account_id: str, amount: Decimal) -> str:
    return f"{account_id}:{format(amount.normalize(), 'f')}"


@router.get("/withdrawals", response_model=list[WithdrawalRead])
def list_user_withdrawals(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return [_request_read(item) for item in withdrawal_service.list_for_user(db, user)]


@router.post("/withdrawals/otp", status_code=202)
def send_withdrawal_otp(
    data: WithdrawalOtpRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    account = db.get(UserPayoutAccount, data.account_id)
    if account is None or account.user_id != user.id:
        raise HTTPException(404, "Saved payout account not found.")
    withdrawal_service.validate_request(db, user, data.amount, account.id, account.method)
    enforce_cooldown(
        f"withdrawal-otp:{user.id}",
        seconds=OTP_RESEND_COOLDOWN_SECONDS,
        message="Please wait before requesting another confirmation code.",
    )
    context = _withdrawal_code_context(account.id, data.amount)
    code = issue_action_code(db, user, WITHDRAWAL_OTP_PURPOSE, context)
    try:
        email_service.send_security_code(user.email, code, "withdrawal request")
    except EmailDeliveryError as error:
        db.rollback()
        raise HTTPException(503, "The confirmation email could not be delivered. Please try again later.") from error
    db.commit()
    return {"message": "A confirmation code has been sent to your registered email."}


@router.post("/withdrawals", response_model=WithdrawalRead, status_code=201)
def create_withdrawal(
    data: WithdrawalCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> WithdrawalRequest:
    withdrawal_service.validate_request(db, user, data.amount, data.account_id, data.payment_method)
    consume_action_code(
        db,
        user,
        WITHDRAWAL_OTP_PURPOSE,
        _withdrawal_code_context(data.account_id, data.amount),
        data.code,
    )
    return withdrawal_service.create(db, user, data.amount, data.account_id, data.payment_method)


@router.get("/admin/payout-settings", response_model=PayoutSettingsRead)
def get_payout_settings(
    _: User = Depends(require_permission("withdrawals.view")),
    db: Session = Depends(get_db),
) -> dict:
    payout_settings = db.get(PayoutSettings, "default")
    return {
        "usd_bdt_rate": payout_settings.usd_bdt_rate if payout_settings else None,
        "minimum_withdrawal_usd": settings.withdrawal_minimum_amount,
    }


@router.put("/admin/payout-settings", response_model=PayoutSettingsRead)
def update_payout_settings(
    data: PayoutSettingsUpdate,
    request: Request,
    admin: User = Depends(require_permission("withdrawals.review")),
    db: Session = Depends(get_db),
) -> dict:
    payout_settings = db.scalar(
        select(PayoutSettings)
        .where(PayoutSettings.id == "default")
        .with_for_update()
    )
    if payout_settings is None:
        payout_settings = PayoutSettings(id="default")
        db.add(payout_settings)
    payout_settings.usd_bdt_rate = data.usd_bdt_rate
    payout_settings.updated_by = admin.id
    payout_settings.updated_at = datetime.now(timezone.utc)
    db.add(
        AdminLog(
            admin_id=admin.id,
            action="PAYOUT_EXCHANGE_RATE_UPDATED",
            target_type="payout_settings",
            target_id=payout_settings.id,
            metadata_json=json.dumps({"usd_bdt_rate": str(data.usd_bdt_rate)}),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:512] or None,
        )
    )
    db.commit()
    db.refresh(payout_settings)
    return {
        "usd_bdt_rate": payout_settings.usd_bdt_rate,
        "minimum_withdrawal_usd": settings.withdrawal_minimum_amount,
    }


@router.get("/admin/withdrawals", response_model=list[WithdrawalRead])
def list_admin_withdrawals(
    _: User = Depends(require_permission("withdrawals.view")),
    db: Session = Depends(get_db),
) -> list[dict]:
    return [_request_read(item) for item in withdrawal_service.list_for_admin(db)]


@router.get("/admin/withdrawals/{withdrawal_id}", response_model=AdminWithdrawalRead)
def get_admin_withdrawal(
    withdrawal_id: str,
    request: Request,
    admin: User = Depends(require_permission("withdrawals.view")),
    db: Session = Depends(get_db),
) -> dict:
    return withdrawal_service.admin_detail(db, withdrawal_id, admin, request)


def _review(
    withdrawal_id: str,
    action: str,
    data: WithdrawalDecision | WithdrawalPayment,
    request: Request,
    admin: User,
    db: Session,
) -> dict:
    withdrawal = withdrawal_service.review(
        db,
        withdrawal_id,
        admin,
        request,
        action,
        data.note,
        data.transaction_id if isinstance(data, WithdrawalPayment) else None,
    )
    return _request_read(withdrawal)


@router.post("/admin/withdrawals/{withdrawal_id}/approve", response_model=WithdrawalRead)
def approve_withdrawal(
    withdrawal_id: str,
    data: WithdrawalDecision,
    request: Request,
    admin: User = Depends(require_permission("withdrawals.review")),
    db: Session = Depends(get_db),
) -> dict:
    return _review(withdrawal_id, "approve", data, request, admin, db)


@router.post("/admin/withdrawals/{withdrawal_id}/reject", response_model=WithdrawalRead)
def reject_withdrawal(
    withdrawal_id: str,
    data: WithdrawalDecision,
    request: Request,
    admin: User = Depends(require_permission("withdrawals.review")),
    db: Session = Depends(get_db),
) -> dict:
    return _review(withdrawal_id, "reject", data, request, admin, db)


@router.post("/admin/withdrawals/{withdrawal_id}/complete", response_model=WithdrawalRead)
def complete_withdrawal(
    withdrawal_id: str,
    data: WithdrawalPayment,
    request: Request,
    admin: User = Depends(require_permission("withdrawals.review")),
    db: Session = Depends(get_db),
) -> dict:
    return _review(withdrawal_id, "complete", data, request, admin, db)
