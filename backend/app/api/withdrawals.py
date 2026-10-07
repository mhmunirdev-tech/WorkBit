from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_permission
from app.database.session import get_db
from app.models import User, WithdrawalRequest
from app.schemas.withdrawals import (
    AdminWithdrawalRead,
    WithdrawalCreate,
    WithdrawalDecision,
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
    return withdrawal_service.create(db, user, data.amount, data.destination)


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
    data: WithdrawalDecision,
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
    data: WithdrawalDecision,
    request: Request,
    admin: User = Depends(require_permission("withdrawals.review")),
    db: Session = Depends(get_db),
) -> dict:
    return _review(withdrawal_id, "complete", data, request, admin, db)
