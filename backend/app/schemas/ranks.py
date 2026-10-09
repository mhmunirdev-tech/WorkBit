from decimal import Decimal

from pydantic import BaseModel


class RankTierRead(BaseModel):
    name: str
    threshold: Decimal


class RankMemberRead(BaseModel):
    position: int
    full_name: str
    avatar_url: str | None
    rank: str
    qualifying_value: Decimal
    referrals: int


class CurrentRankRead(BaseModel):
    full_name: str
    avatar_url: str | None
    position: int | None
    rank: str
    qualifying_value: Decimal
    next_rank: str | None
    next_threshold: Decimal | None
    amount_to_next: Decimal


class RanksRead(BaseModel):
    currency: str
    tiers: list[RankTierRead]
    current_user: CurrentRankRead
    leaderboard: list[RankMemberRead]
