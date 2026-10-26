from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OfferwallGGCurrency(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    per_usd: Decimal = Field(alias="perUsd", gt=0)


class OfferwallGGApiOffer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    external_id: str = Field(alias="externalId")
    provider: str
    name: str
    description: str = ""
    requirements: str = ""
    image: str | None = None
    categories: list[str] = Field(default_factory=list)
    devices: list[str] = Field(default_factory=list)
    reward: Decimal = Field(ge=0)
    reward_is_variable: bool = Field(alias="rewardIsVariable", default=False)
    reward_up_to: bool = Field(alias="rewardUpTo", default=False)
    payment_model: str = Field(alias="paymentModel", default="")
    featured: bool = False
    click_url: str = Field(alias="clickUrl")


class OfferwallGGPagination(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(ge=1)
    pages: int = Field(ge=0)
    total: int = Field(ge=0)
    per_page: int = Field(alias="perPage", ge=1)


class OfferwallGGApiData(BaseModel):
    offers: list[OfferwallGGApiOffer]
    pagination: OfferwallGGPagination
    currency: OfferwallGGCurrency


class OfferwallGGApiResponse(BaseModel):
    success: bool
    data: OfferwallGGApiData


class OfferwallGGOfferRead(BaseModel):
    id: int
    provider: str
    title: str
    description: str
    requirements: str
    image_url: str | None
    categories: list[str]
    devices: list[str]
    reward_usd: Decimal
    user_reward_usd: Decimal
    reward_is_variable: bool
    reward_up_to: bool
    payment_model: str
    featured: bool
    click_url: str


class OfferwallGGOffersRead(BaseModel):
    offers: list[OfferwallGGOfferRead]
    page: int
    pages: int
    total: int
