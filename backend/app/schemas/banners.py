from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DashboardBannerCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(default="", max_length=500)
    image_url: str = Field(min_length=1, max_length=1024)
    link_url: str | None = Field(default=None, max_length=1024)
    is_active: bool = False
    sort_order: int = Field(default=0, ge=0, le=10000)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Text cannot contain only whitespace.")
        return value

    @field_validator("content")
    @classmethod
    def trim_content(cls, value: str) -> str:
        return value.strip()

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Banner image must use a secure HTTPS URL.")
        return value

    @field_validator("link_url")
    @classmethod
    def validate_link_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if value.startswith("/") and not value.startswith("//") and "\\" not in value:
            return value
        parsed = urlsplit(value)
        if parsed.scheme == "https" and parsed.netloc:
            return value
        raise ValueError("Link must be a site path or secure HTTPS URL.")


class DashboardBannerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: str
    image_url: str
    link_url: str | None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
