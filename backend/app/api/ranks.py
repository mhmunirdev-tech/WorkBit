from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.database.session import get_db
from app.models import PackagePurchase, Profile, RankTier, User, WalletTransaction
from app.schemas.ranks import (
    CurrentRankRead,
    RankMemberRead,
    RankTierRead,
    RanksRead,
)

router = APIRouter(tags=["ranks"])

def rank_for_value(
    value: Decimal,
    tiers: list[RankTier],
) -> tuple[str, str | None, Decimal | None]:
    current_index = max(
        index
        for index, tier in enumerate(tiers)
        if value >= tier.threshold
    )
    name = tiers[current_index].name
    if current_index == len(tiers) - 1:
        return name, None, None
    next_tier = tiers[current_index + 1]
    return name, next_tier.name, next_tier.threshold


@router.get("/ranks", response_model=RanksRead)
def ranks(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> RanksRead:
    tiers = db.scalars(select(RankTier).order_by(RankTier.sort_order, RankTier.id)).all()
    if (
        not tiers
        or tiers[0].threshold > 0
        or any(
            current.threshold >= following.threshold
            for current, following in zip(tiers, tiers[1:])
        )
    ):
        raise HTTPException(503, "Rank tiers are not configured correctly.")
    approved_ad_rewards = (
        select(
            WalletTransaction.user_id.label("user_id"),
            func.sum(WalletTransaction.amount).label("value"),
        )
        .where(
            WalletTransaction.type.in_(("OFFER_REWARD_APPROVAL", "OFFER_REWARD_RELEASE")),
            WalletTransaction.status == "APPROVED",
            WalletTransaction.currency == "USD",
            WalletTransaction.amount > 0,
        )
        .group_by(WalletTransaction.user_id)
        .subquery()
    )
    completed_package_purchases = (
        select(
            PackagePurchase.user_id.label("user_id"),
            func.sum(PackagePurchase.amount).label("value"),
        )
        .where(
            PackagePurchase.status == "APPROVED",
            PackagePurchase.currency == "USD",
            PackagePurchase.amount > 0,
        )
        .group_by(PackagePurchase.user_id)
        .subquery()
    )
    referral_counts = (
        select(
            User.referred_by.label("user_id"),
            func.count(User.id).label("count"),
        )
        .where(User.referred_by.is_not(None))
        .group_by(User.referred_by)
        .subquery()
    )
    qualifying_value = (
        func.coalesce(approved_ad_rewards.c.value, 0)
        + func.coalesce(completed_package_purchases.c.value, 0)
    ).label("qualifying_value")

    current_value = Decimal(
        str(
            db.execute(
                select(qualifying_value)
                .select_from(User)
                .outerjoin(approved_ad_rewards, approved_ad_rewards.c.user_id == User.id)
                .outerjoin(
                    completed_package_purchases,
                    completed_package_purchases.c.user_id == User.id,
                )
                .where(User.id == user.id)
            ).scalar_one()
            or 0
        )
    )
    leaderboard_rows = db.execute(
        select(
            User.id,
            User.full_name,
            User.created_at,
            Profile.avatar_url,
            qualifying_value,
            func.coalesce(referral_counts.c.count, 0).label("referrals"),
        )
        .outerjoin(Profile, Profile.user_id == User.id)
        .outerjoin(approved_ad_rewards, approved_ad_rewards.c.user_id == User.id)
        .outerjoin(
            completed_package_purchases,
            completed_package_purchases.c.user_id == User.id,
        )
        .outerjoin(referral_counts, referral_counts.c.user_id == User.id)
        .where(User.status == "ACTIVE", User.email_verified.is_(True))
        .order_by(qualifying_value.desc(), User.created_at.asc(), User.id.asc())
    ).all()

    leaderboard: list[RankMemberRead] = []
    current_position: int | None = None
    for position, row in enumerate(leaderboard_rows, start=1):
        value = Decimal(str(row.qualifying_value or 0))
        rank, _, _ = rank_for_value(value, tiers)
        if row.id == user.id:
            current_position = position
        leaderboard.append(
            RankMemberRead(
                position=position,
                full_name=row.full_name,
                avatar_url=row.avatar_url,
                rank=rank,
                qualifying_value=value,
                referrals=row.referrals,
            )
        )

    current_rank, next_rank, next_threshold = rank_for_value(current_value, tiers)
    return RanksRead(
        currency="USD",
        tiers=[
            RankTierRead(name=name, threshold=threshold)
            for name, threshold in ((tier.name, tier.threshold) for tier in tiers)
        ],
        current_user=CurrentRankRead(
            full_name=user.full_name,
            avatar_url=user.profile.avatar_url if user.profile else None,
            position=current_position,
            rank=current_rank,
            qualifying_value=current_value,
            next_rank=next_rank,
            next_threshold=next_threshold,
            amount_to_next=(
                max(next_threshold - current_value, Decimal("0"))
                if next_threshold is not None
                else Decimal("0")
            ),
        ),
        leaderboard=leaderboard,
    )
