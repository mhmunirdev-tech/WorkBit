from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OfferwallMeApiOffer(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str | int
    provider: str = "Offerwall.me"
    name: str = ""
    title: str = ""
    description: str = ""
    image: str | None = None
    reward: Decimal = Field(ge=0)
    payout: Decimal = Field(ge=0)
    devices: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    is_multi_step: bool = False
    url: str

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, value: object) -> str:
        return str(value)

    @model_validator(mode="after")
    def use_name_as_title(self) -> "OfferwallMeApiOffer":
        if not self.title:
            self.title = self.name
        return self


class OfferwallMeApiResponse(BaseModel):
    status: int
    message: str = ""
    data: list[OfferwallMeApiOffer] | None = Field(default_factory=list)


class OfferwallMeOfferRead(BaseModel):
    id: str
    provider: str
    title: str
    description: str
    image_url: str | None
    devices: list[str]
    countries: list[str]
    provider_reward: Decimal
    reward_name: str
    provider_payout_usd: Decimal
    estimated_user_reward_usd: Decimal
    multi_step: bool
    click_url: str


class OfferwallMeOffersRead(BaseModel):
    offers: list[OfferwallMeOfferRead]
    total: int
