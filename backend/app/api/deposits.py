from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_permission
from app.database.session import get_db
from app.models import DepositRequest, User
from app.schemas.deposits import AdminDepositRead, DepositCreate, DepositRead, DepositReview
from app.services.deposits import deposit_read, deposit_service

router = APIRouter(tags=["deposits"])


def _admin_read(deposit: DepositRequest) -> dict:
    return {
        **deposit_read(deposit),
        "user_id": deposit.user_id,
        "user_name": deposit.user.full_name,
        "user_email": deposit.user.email,
    }


@router.get("/deposits", response_model=list[DepositRead])
def list_user_deposits(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return [deposit_read(item) for item in deposit_service.list_for_user(db, user)]


@router.post("/deposits", response_model=DepositRead, status_code=201)
def create_deposit(
    data: DepositCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> DepositRequest:
    return deposit_service.create(db, user, data)


@router.get("/admin/deposits", response_model=list[AdminDepositRead])
def list_admin_deposits(
    _: User = Depends(require_permission("withdrawals.view")),
    db: Session = Depends(get_db),
) -> list[dict]:
    return [_admin_read(item) for item in deposit_service.list_for_admin(db)]


def _review(
    deposit_id: str,
    status: str,
    data: DepositReview,
    admin: User,
    db: Session,
) -> dict:
    return _admin_read(deposit_service.review(db, deposit_id, admin, status, data.note))


@router.post("/admin/deposits/{deposit_id}/approve", response_model=AdminDepositRead)
def approve_deposit(
    deposit_id: str,
    data: DepositReview,
    admin: User = Depends(require_permission("withdrawals.review")),
    db: Session = Depends(get_db),
) -> dict:
    return _review(deposit_id, "APPROVED", data, admin, db)


@router.post("/admin/deposits/{deposit_id}/reject", response_model=AdminDepositRead)
def reject_deposit(
    deposit_id: str,
    data: DepositReview,
    admin: User = Depends(require_permission("withdrawals.review")),
    db: Session = Depends(get_db),
) -> dict:
    return _review(deposit_id, "REJECTED", data, admin, db)
