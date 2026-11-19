from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MoonetixApiGoal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    reward: Decimal = Field(ge=0)
    payout_usd: Decimal = Field(ge=0)


class MoonetixApiOffer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    category: str = "other"
    description: str = ""
    goals: list[MoonetixApiGoal] = Field(default_factory=list)
    reward: Decimal = Field(ge=0)
    reward_before_bonus: Decimal | None = None
    payout_usd: Decimal = Field(ge=0)
    payout_type: str = "fixed"
    reward_max: Decimal | None = None
    payout_max_usd: Decimal | None = None
    thumbnail_url: str | None = None
    start_url: str


class MoonetixApiResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool
    currency: str = ""
    bonus_percent: Decimal | None = None
    history_url: str | None = None
    error: str | None = None
    message: str | None = None
    offers: list[MoonetixApiOffer] = Field(default_factory=list)


class MoonetixGoalRead(BaseModel):
    name: str
    reward: Decimal
    payout_usd: Decimal


class MoonetixOfferRead(BaseModel):
    id: str
    title: str
    category: str
    description: str
    goals: list[MoonetixGoalRead]
    reward: Decimal
    reward_max: Decimal | None
    reward_name: str
    payout_usd: Decimal
    estimated_user_reward_usd: Decimal
    estimated_user_reward_max_usd: Decimal | None
    is_variable: bool
    image_url: str | None
    start_url: str


class MoonetixOffersRead(BaseModel):
    offers: list[MoonetixOfferRead]
    total: int
    currency: str
    usd_bdt_rate: Decimal | None = None
    history_url: str | None = None
