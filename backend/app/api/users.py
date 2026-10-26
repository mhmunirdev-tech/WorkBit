from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_permission
from app.database.session import get_db
from app.models import PackagePurchase, Role, User, Wallet
from app.schemas.users import AdminUserListRead, AdminUserRead

router = APIRouter(tags=["admin users"])


def _user_query(search: str | None, status: str | None):
    query = select(User).where(User.roles.any(Role.name == "USER"))
    if search:
        pattern = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(User.full_name).like(pattern),
                func.lower(User.email).like(pattern),
                func.lower(User.phone_number).like(pattern),
            )
        )
    if status and status.upper() != "ALL":
        query = query.where(User.status == status.upper())
    return query


@router.get("/admin/users", response_model=AdminUserListRead)
def list_admin_users(
    search: str | None = Query(default=None, max_length=120),
    status: str | None = Query(default=None, max_length=32),
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=25, ge=1, le=100),
    _: User = Depends(require_permission("users.view")),
    db: Session = Depends(get_db),
) -> AdminUserListRead:
    now = datetime.now(timezone.utc)
    base = _user_query(search, status)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    users = db.scalars(
        base.options(selectinload(User.wallet))
        .order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    user_ids = [user.id for user in users]
    active_packages: dict[str, datetime] = {}
    if user_ids:
        package_rows = db.execute(
            select(PackagePurchase.user_id, PackagePurchase.expires_at)
            .where(
                PackagePurchase.user_id.in_(user_ids),
                PackagePurchase.status == "APPROVED",
                PackagePurchase.expires_at > now,
            )
            .order_by(PackagePurchase.expires_at.desc())
        ).all()
        for user_id, expires_at in package_rows:
            if user_id not in active_packages and expires_at is not None:
                active_packages[user_id] = expires_at

    def user_read(user: User) -> AdminUserRead:
        wallet = user.wallet
        expiry = active_packages.get(user.id)
        return AdminUserRead(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            country=user.country,
            phone_number=user.phone_number,
            status=user.status,
            email_verified=user.email_verified,
            created_at=user.created_at,
            available_balance=wallet.available_balance if wallet else 0,
            pending_balance=wallet.pending_balance if wallet else 0,
            lifetime_earned=wallet.lifetime_earned if wallet else 0,
            lifetime_withdrawn=wallet.lifetime_withdrawn if wallet else 0,
            currency=wallet.currency if wallet else "USD",
            active_package=expiry is not None,
            package_expires_at=expiry,
        )

    user_scope = select(User.id).where(User.roles.any(Role.name == "USER"))
    registered_count = db.scalar(select(func.count()).select_from(user_scope.subquery())) or 0
    active_count = db.scalar(
        select(func.count()).select_from(user_scope.where(User.status == "ACTIVE").subquery())
    ) or 0
    pending_count = db.scalar(
        select(func.count()).select_from(user_scope.where(User.status == "PENDING_VERIFICATION").subquery())
    ) or 0
    suspended_count = db.scalar(
        select(func.count()).select_from(
            user_scope.where(User.status.in_(("SUSPENDED", "BANNED", "PENDING_REVIEW"))).subquery()
        )
    ) or 0
    active_package_count = db.scalar(
        select(func.count(func.distinct(PackagePurchase.user_id)))
        .select_from(PackagePurchase)
        .join(User, User.id == PackagePurchase.user_id)
        .where(
            User.roles.any(Role.name == "USER"),
            User.status == "ACTIVE",
            PackagePurchase.status == "APPROVED",
            PackagePurchase.expires_at > now,
        )
    ) or 0
    total_wallet_balance = db.scalar(
        select(func.coalesce(func.sum(Wallet.available_balance), 0))
        .select_from(Wallet)
        .join(User, User.id == Wallet.user_id)
        .where(User.roles.any(Role.name == "USER"))
    ) or 0

    return AdminUserListRead(
        items=[user_read(user) for user in users],
        total=total,
        registered_count=registered_count,
        page=page,
        page_size=page_size,
        active_count=active_count,
        pending_verification_count=pending_count,
        suspended_count=suspended_count,
        active_package_count=active_package_count,
        total_wallet_balance=total_wallet_balance,
    )
