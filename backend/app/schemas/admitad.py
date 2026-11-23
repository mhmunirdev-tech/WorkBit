from pydantic import BaseModel, ConfigDict, Field


class AdmitadTokenResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    access_token: str = Field(min_length=1)
    token_type: str = "bearer"
    expires_in: int = Field(gt=0)


class AdmitadAction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = ""
    type: str = ""
    payment_size: str = ""


class AdmitadCampaign(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    status: str = ""
    connection_status: str = ""
    allow_deeplink: bool = False
    site_url: str | None = None
    description: str = ""
    image: str | None = None
    currency: str = ""
    actions: list[AdmitadAction] = Field(default_factory=list)
    action_countries: list[str] = Field(default_factory=list)
    allow_actions_all_countries: bool = False


class AdmitadMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    count: int = Field(default=0, ge=0)


class AdmitadCampaignList(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    results: list[AdmitadCampaign] = Field(default_factory=list)
    meta: AdmitadMeta = Field(default_factory=AdmitadMeta, alias="_meta")


class AdmitadDeeplink(BaseModel):
    model_config = ConfigDict(extra="ignore")

    link: str = Field(min_length=1)
    is_affiliate_product: bool | None = None


class AdmitadCampaignRead(BaseModel):
    id: int
    name: str
    description: str
    image_url: str | None
    currency: str
    actions: list[AdmitadAction]


class AdmitadCampaignsRead(BaseModel):
    campaigns: list[AdmitadCampaignRead]
    total: int = Field(ge=0)
