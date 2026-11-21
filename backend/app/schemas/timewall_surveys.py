from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TimeWallApiSurvey(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=128)
    loi: int = Field(ge=0)
    usd_rate: Decimal = Field(gt=0)
    currency_amount: Decimal = Field(gt=0)
    link: str = Field(min_length=1, max_length=2048)


class TimeWallApiResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool
    prescreener_required: bool = False
    currency: str = Field(min_length=1, max_length=16)
    surveys: list[TimeWallApiSurvey] = Field(default_factory=list)


class TimeWallSurveyRead(BaseModel):
    id: str
    title: str
    estimated_time_minutes: int
    provider_currency_amount: Decimal
    provider_currency: str
    estimated_user_reward_usd: Decimal
    entry_url: str


class TimeWallSurveysRead(BaseModel):
    surveys: list[TimeWallSurveyRead]
    total: int
    currency: str
    usd_bdt_rate: Decimal | None = None
