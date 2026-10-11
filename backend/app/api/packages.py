from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_permission
from app.database.session import get_db
from app.models import EarningPackage, PackagePurchase, User
from app.schemas.packages import (
    AdminPackagePurchaseRead,
    EarningPackageRead,
    EarningPackageUpdate,
    PackagePurchaseCreate,
    PackagePurchaseRead,
    PackageReview,
    PublicPackageRead,
    WalletPackagePurchaseCreate,
)
from app.services.packages import package_read, package_purchase_read, package_service

router = APIRouter(tags=["packages"])


@router.get("/public/packages", response_model=list[PublicPackageRead])
def public_package_catalog(db: Session = Depends(get_db)) -> list[dict]:
    packages = db.scalars(
        select(EarningPackage)
        .where(EarningPackage.is_active.is_(True))
        .order_by(EarningPackage.sort_order, EarningPackage.code)
    ).all()
    return [package_read(package) for package in packages]


@router.get("/admin/packages", response_model=list[EarningPackageRead])
def list_earning_packages(
    _: User = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> list[EarningPackage]:
    return list(
        db.scalars(
            select(EarningPackage).order_by(EarningPackage.sort_order, EarningPackage.code)
        ).all()
    )


@router.put("/admin/packages/{package_code}", response_model=EarningPackageRead)
def update_earning_package(
    package_code: str,
    data: EarningPackageUpdate,
    _: User = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> EarningPackage:
    package = db.get(EarningPackage, package_code)
    if package is None:
        raise HTTPException(404, "Earning package not found.")
    for field, value in data.model_dump().items():
        setattr(package, field, value)
    db.commit()
    db.refresh(package)
    return package


def _admin_purchase_read(purchase: PackagePurchase) -> dict:
    return {
        **package_purchase_read(purchase),
        "user_id": purchase.user_id,
        "user_name": purchase.user.full_name,
        "user_email": purchase.user.email,
    }


@router.get("/packages")
def package_catalog(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return package_service.catalog(db, user)


@router.post(
    "/package-purchases",
    response_model=PackagePurchaseRead,
    status_code=201,
)
def create_package_purchase(
    data: PackagePurchaseCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PackagePurchase:
    return package_service.create_purchase(db, user, data)


@router.post(
    "/package-purchases/wallet",
    response_model=PackagePurchaseRead,
    status_code=201,
)
def create_wallet_package_purchase(
    data: WalletPackagePurchaseCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PackagePurchase:
    return package_service.purchase_with_wallet(db, user, data)


@router.get(
    "/admin/package-purchases",
    response_model=list[AdminPackagePurchaseRead],
)
def list_package_purchases(
    _: User = Depends(require_permission("withdrawals.review")),
    db: Session = Depends(get_db),
) -> list[dict]:
    return [_admin_purchase_read(item) for item in package_service.list_for_admin(db)]


def _review_package_purchase(
    purchase_id: str,
    data: PackageReview,
    admin: User,
    db: Session,
    status: str,
) -> dict:
    purchase = package_service.review(db, purchase_id, admin, status, data.note)
    return _admin_purchase_read(purchase)


@router.post(
    "/admin/package-purchases/{purchase_id}/approve",
    response_model=AdminPackagePurchaseRead,
)
def approve_package_purchase(
    purchase_id: str,
    data: PackageReview,
    admin: User = Depends(require_permission("withdrawals.review")),
    db: Session = Depends(get_db),
) -> dict:
    return _review_package_purchase(purchase_id, data, admin, db, "APPROVED")


@router.post(
    "/admin/package-purchases/{purchase_id}/reject",
    response_model=AdminPackagePurchaseRead,
)
def reject_package_purchase(
    purchase_id: str,
    data: PackageReview,
    admin: User = Depends(require_permission("withdrawals.review")),
    db: Session = Depends(get_db),
) -> dict:
    return _review_package_purchase(purchase_id, data, admin, db, "REJECTED")
