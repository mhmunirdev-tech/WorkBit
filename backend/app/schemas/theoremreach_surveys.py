from decimal import Decimal

from pydantic import BaseModel, Field


class TheoremReachSurveyApiItem(BaseModel):
    campaign_id: int = Field(gt=0)
    quota_id: int | None = None
    quota_ids: list[int] = Field(default_factory=list)
    rank: int = 0
    loi: int | None = Field(default=None, ge=0)
    cpi: Decimal = Field(gt=0)
    incidence: Decimal | None = Field(default=None, ge=0)
    entry_link: str


class TheoremReachSurveyApiResponse(BaseModel):
    surveys: list[TheoremReachSurveyApiItem]


class TheoremReachSurveyRead(BaseModel):
    id: str
    survey_id: int
    title: str
    rank: int
    estimated_time_minutes: int | None
    incidence: Decimal | None
    user_reward_usd: Decimal
    entry_url: str


class TheoremReachSurveysRead(BaseModel):
    surveys: list[TheoremReachSurveyRead]
