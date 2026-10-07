import base64
import binascii
from pathlib import Path
from decimal import Decimal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore")
    environment: str = "development"
    database_url: str
    direct_url: str | None = None
    redis_url: str | None = None
    secret_key: str = "development-only-change-me"
    session_secret: str = "development-only-change-me"
    frontend_origin: str = "http://localhost:3000"
    session_cookie_name: str = "workbit_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 7
    token_ttl_minutes: int = 30
    email_provider: str = "resend"
    email_api_key: str | None = None
    email_from_address: str | None = None
    enable_mock_rewards: bool = False
    withdrawal_minimum_amount: Decimal = Field(default=Decimal("5.00"), gt=0, max_digits=18, decimal_places=8)
    withdrawal_encryption_key: str | None = None

    @property
    def withdrawal_encryption_configured(self) -> bool:
        if not self.withdrawal_encryption_key:
            return False
        try:
            key = base64.b64decode(
                self.withdrawal_encryption_key.encode("ascii"),
                altchars=b"-_",
                validate=True,
            )
        except (binascii.Error, UnicodeEncodeError, ValueError):
            return False
        return len(key) == 32


settings = Settings()
