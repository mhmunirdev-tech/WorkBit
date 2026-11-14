import base64
import binascii
from pathlib import Path
from decimal import Decimal

from pydantic import Field, model_validator
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
    fraud_registration_shared_ip_threshold: int = Field(default=2, ge=1, le=100)
    fraud_registration_window_minutes: int = Field(default=60, gt=0, le=1440)
    fraud_login_medium_attempt_threshold: int = Field(default=5, ge=2, le=1000)
    fraud_login_high_attempt_threshold: int = Field(default=20, ge=3, le=10000)
    fraud_login_window_minutes: int = Field(default=15, gt=0, le=1440)
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
    offerwall_me_enabled: bool = False
    offerwall_me_postback_enabled: bool = False
    offerwall_me_public_api_key: str | None = None
    offerwall_me_api_token: str | None = None
    offerwall_me_secret_key: str | None = None
    offerwall_me_currency_name: str = "Points"
    offerwall_me_exchange_rate: Decimal = Field(default=Decimal("1000"), gt=0)
    cpx_research_enabled: bool = False
    cpx_research_postback_enabled: bool = False
    cpx_research_app_id: str = "37861"
    cpx_research_secure_hash: str | None = None
    bitlabs_enabled: bool = False
    bitlabs_api_key: str | None = None
    bitlabs_postback_secret: str | None = None
    bitlabs_callback_url: str | None = None
    theoremreach_enabled: bool = False
    theoremreach_surveys_api_enabled: bool = False
    theoremreach_api_key: str | None = None
    theoremreach_secret_key: str | None = None
    theoremreach_partner_id: str | None = None
    theoremreach_placement_id: str | None = None
    theoremreach_callback_url: str | None = None
    theoremreach_currency_name_singular: str = "Credit"
    theoremreach_currency_name_plural: str = "Credits"
    theoremreach_exchange_rate: Decimal = Field(default=Decimal("10"), ge=10)
    theoremreach_decimals_to_display: int = Field(default=2, ge=0, le=8)
    bitcotasks_enabled: bool = False
    bitcotasks_postback_enabled: bool = False
    bitcotasks_api_key: str | None = None
    bitcotasks_secret_key: str | None = None
    bitcotasks_currency_name: str = "Points"
    bitcotasks_exchange_rate: Decimal | None = Field(default=None, gt=0)
    enable_mock_rewards: bool = False
    package_bkash_number: str = "01839299096"
    package_nagad_number: str = "01811914794"
    withdrawal_minimum_amount: Decimal = Field(default=Decimal("5.00"), gt=0, max_digits=18, decimal_places=8)
    withdrawal_encryption_key: str | None = None

    @model_validator(mode="after")
    def validate_fraud_thresholds(self):
        if self.fraud_login_high_attempt_threshold <= self.fraud_login_medium_attempt_threshold:
            raise ValueError(
                "FRAUD_LOGIN_HIGH_ATTEMPT_THRESHOLD must exceed "
                "FRAUD_LOGIN_MEDIUM_ATTEMPT_THRESHOLD."
            )
        return self

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
