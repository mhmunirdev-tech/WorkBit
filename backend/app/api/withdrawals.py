import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_permission
from app.core.config import settings
from app.database.session import get_db
from app.models import AdminLog, PayoutSettings, User, WithdrawalRequest
from app.schemas.withdrawals import (
    AdminWithdrawalRead,
    PayoutSettingsRead,
    PayoutSettingsUpdate,
    WithdrawalCreate,
    WithdrawalDecision,
    WithdrawalPayment,
    WithdrawalRead,
)
from app.services.withdrawals import _request_read, withdrawal_service

router = APIRouter(tags=["withdrawals"])


@router.get("/withdrawals", response_model=list[WithdrawalRead])
def list_user_withdrawals(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return [_request_read(item) for item in withdrawal_service.list_for_user(db, user)]


@router.post("/withdrawals", response_model=WithdrawalRead, status_code=201)
def create_withdrawal(
    data: WithdrawalCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> WithdrawalRequest:
    return withdrawal_service.create(db, user, data.amount, data.destination, data.payment_method)


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
