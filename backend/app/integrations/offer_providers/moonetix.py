from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from uuid import UUID

from app.core.config import settings

MOONETIX_SLUG = "moonetix"
MOONETIX_WALL_ORIGIN = "https://wall.moonetix.com"
HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
SIGNED_AMOUNT_PATTERN = re.compile(r"^-?\d{1,10}(?:\.\d{1,8})?$")
AMOUNT_PATTERN = re.compile(r"^\d{1,10}(?:\.\d{1,8})?$")


class MoonetixConfigurationError(RuntimeError):
    pass


class MoonetixCallbackError(ValueError):
    pass


@dataclass(frozen=True)
class MoonetixCallback:
    user_id: str
    transaction_id: str
    status: str
    reward: Decimal
    payout_usd: Decimal
    amount_usd: Decimal
    offer_id: str
    offer_name: str
    country: str


class MoonetixAdapter:
    def credentials(self) -> tuple[str, str, str]:
        app_id = (settings.moonetix_app_id or "").strip()
        link_salt = (settings.moonetix_link_hash_salt or "").strip()
        postback_secret = (settings.moonetix_postback_secret or "").strip()
        if not settings.moonetix_enabled:
            raise MoonetixConfigurationError("Moonetix integration is disabled.")
        if not app_id or not link_salt:
            raise MoonetixConfigurationError(
                "Moonetix App ID and link hash salt are not configured."
            )
        if not postback_secret:
            raise MoonetixConfigurationError(
                "Moonetix postback secret is not configured."
            )
        currency = settings.moonetix_currency_name.strip().upper()
        if not currency or len(currency) > 16:
            raise MoonetixConfigurationError("Moonetix currency name is invalid.")
        if (
            not settings.moonetix_exchange_rate.is_finite()
            or settings.moonetix_exchange_rate <= 0
        ):
            raise MoonetixConfigurationError("Moonetix exchange rate is invalid.")
        return app_id, link_salt, postback_secret

    def build_wall_url(self, user_id: str) -> str:
        app_id, link_salt, _ = self.credentials()
        try:
            user_id = str(UUID(str(user_id)))
        except ValueError as error:
            raise MoonetixConfigurationError("WorkBit user ID must be a UUID.") from error
        signature = hmac.new(
            link_salt.encode("utf-8"),
            user_id.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return (
            f"{MOONETIX_WALL_ORIGIN}/{app_id}?"
            + urlencode({"user_id": user_id, "hash": signature})
        )

    def verify_callback(self, values: dict[str, str]) -> MoonetixCallback:
        _, _, postback_secret = self.credentials()
        user_id = values.get("user_id", "")
        transaction_id = values.get("transaction_id", "")
        reward_text = values.get("reward", "")
        payout_text = values.get("payout", "")
        status = values.get("status", "")
        signature = values.get("hash", "")

        if not user_id or len(user_id) > 36:
            raise MoonetixCallbackError("Invalid callback user ID.")
        try:
            user_id = str(UUID(user_id))
        except ValueError as error:
            raise MoonetixCallbackError("Invalid callback user ID.") from error
        if not transaction_id or len(transaction_id) > 128:
            raise MoonetixCallbackError("Invalid callback transaction ID.")
        if status not in {"1", "2"}:
            raise MoonetixCallbackError("Invalid callback status.")
        if not SIGNED_AMOUNT_PATTERN.fullmatch(reward_text):
            raise MoonetixCallbackError("Invalid callback reward.")
        if not AMOUNT_PATTERN.fullmatch(payout_text):
            raise MoonetixCallbackError("Invalid callback payout.")
        if not HASH_PATTERN.fullmatch(signature):
            raise MoonetixCallbackError("Missing or malformed callback signature.")

        message = f"{transaction_id}:{user_id}:{reward_text}:{status}"
        expected_signature = hmac.new(
            postback_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, signature.lower()):
            raise MoonetixCallbackError("Invalid callback signature.")

        try:
            reward = Decimal(reward_text)
            payout_usd = Decimal(payout_text)
        except InvalidOperation as error:
            raise MoonetixCallbackError("Invalid callback amount.") from error
        if (
            not reward.is_finite()
            or reward <= 0
            or not payout_usd.is_finite()
            or payout_usd <= 0
        ):
            raise MoonetixCallbackError("Callback amounts must be positive.")

        amount_usd = payout_usd
        if settings.moonetix_currency_name.strip().upper() != "USD":
            converted = reward / settings.moonetix_exchange_rate
            amount_usd = min(payout_usd, converted.quantize(Decimal("0.00000001")))

        if amount_usd <= 0 or amount_usd > Decimal("9999999999.99999999"):
            raise MoonetixCallbackError("Callback amount is out of range.")

        return MoonetixCallback(
            user_id=user_id,
            transaction_id=transaction_id,
            status=status,
            reward=reward,
            payout_usd=payout_usd,
            amount_usd=amount_usd,
            offer_id=(values.get("offer_id") or values.get("offerid") or "moonetix")[:128],
            offer_name=(values.get("offer_name") or values.get("offername") or "")[:255],
            country=(values.get("country") or "")[:2].upper(),
        )


moonetix_adapter = MoonetixAdapter()
