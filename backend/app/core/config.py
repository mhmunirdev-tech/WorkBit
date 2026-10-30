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
    admin_session_cookie_name: str = "workbit_admin_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 7
    token_ttl_minutes: int = 30
    email_verification_otp_ttl_minutes: int = Field(default=10, gt=0, le=60)
    email_provider: str | None = None
    resend_api_key: str | None = None
    brevo_api_key: str | None = None
    email_from_address: str | None = None
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None
    offerwall_gg_enabled: bool = False
    offerwall_gg_public_key: str | None = None
    offerwall_gg_secret_key: str | None = None
    offerwall_gg_currency_name: str = "USD"
    bitlabs_enabled: bool = False
    bitlabs_api_key: str | None = None
    bitlabs_postback_secret: str | None = None
    bitlabs_callback_url: str | None = None
    theoremreach_enabled: bool = False
    theoremreach_api_key: str | None = None
    theoremreach_secret_key: str | None = None
    theoremreach_partner_id: str | None = None
    theoremreach_placement_id: str | None = None
    theoremreach_callback_url: str | None = None
    theoremreach_currency_name_singular: str = "Credit"
    theoremreach_currency_name_plural: str = "Credits"
    theoremreach_exchange_rate: Decimal = Field(default=Decimal("10"), ge=10)
    theoremreach_decimals_to_display: int = Field(default=2, ge=0, le=8)
    enable_mock_rewards: bool = False
    package_bkash_number: str = "01839299096"
    package_nagad_number: str = "01811914794"
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
