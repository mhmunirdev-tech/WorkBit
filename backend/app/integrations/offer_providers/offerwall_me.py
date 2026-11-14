from __future__ import annotations

import hashlib
import hmac
import re
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urlencode
from uuid import UUID

from app.core.config import settings

OFFERWALL_ME_SLUG = "offerwall-me"
OFFERWALL_ME_ORIGIN = "https://offerwall.me"
SIGNED_AMOUNT_PATTERN = re.compile(r"^-?\d{1,10}(?:\.\d{1,8})?$")
AMOUNT_PATTERN = re.compile(r"^\d{1,10}(?:\.\d{1,8})?$")
HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")


class OfferwallMeConfigurationError(RuntimeError):
    pass


class OfferwallMeCallbackError(ValueError):
    pass


@dataclass(frozen=True)
class OfferwallMeCallback:
    user_id: str
    transaction_id: str
    status: str
    amount_usd: Decimal
    reward: str
    reward_value: str
    payout_usd: Decimal
    offer_name: str
    offer_type: str
    reward_name: str
    country: str


class OfferwallMeAdapter:
    @staticmethod
    def _credentials() -> tuple[str, str]:
        public_api_key = (settings.offerwall_me_public_api_key or "").strip()
        secret_key = settings.offerwall_me_secret_key or ""
        if not public_api_key or len(public_api_key) > 256 or not secret_key:
            raise OfferwallMeConfigurationError(
                "Offerwall.me public API key and private secret are not configured."
            )
        if settings.offerwall_me_currency_name.strip().upper() != "USD":
            raise OfferwallMeConfigurationError(
                "Offerwall.me currency must be configured as USD for WorkBit wallets."
            )
        if (
            not settings.offerwall_me_exchange_rate.is_finite()
            or settings.offerwall_me_exchange_rate <= 0
        ):
            raise OfferwallMeConfigurationError("Offerwall.me exchange rate is invalid.")
        return public_api_key, secret_key

    def build_wall_url(self, user_id: str) -> str:
        if not settings.offerwall_me_enabled:
            raise OfferwallMeConfigurationError("Offerwall.me integration is disabled.")

        public_api_key, secret_key = self._credentials()
        try:
            user_id = str(UUID(user_id))
        except ValueError as error:
            raise OfferwallMeConfigurationError("WorkBit user ID must be a UUID.") from error

        expires = str(int(time.time()) + 3600)
        message = "\n".join(
            ("offerwall-user-v1", public_api_key, user_id, expires)
        )
        signature = hmac.new(
            secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return (
            f"{OFFERWALL_ME_ORIGIN}/offerwall/"
            f"{quote(public_api_key, safe='')}/{quote(user_id, safe='')}?"
            + urlencode(
                {"identityExpires": expires, "identitySignature": signature}
            )
        )

    def verify_callback(self, values: dict[str, str]) -> OfferwallMeCallback:
        _, secret_key = self._credentials()
        user_id = values.get("subId", "")
        transaction_id = values.get("transId", "")
        reward_text = values.get("reward", "")
        rate_text = values.get("reward_value", "").strip()
        payout_text = values.get("payout", "").strip()
        signature = values.get("signature", "").strip()
        status = values.get("status", "").strip()

        if (
            user_id != user_id.strip()
            or transaction_id != transaction_id.strip()
            or reward_text != reward_text.strip()
        ):
            raise OfferwallMeCallbackError("Malformed signed callback fields.")
        if not user_id or len(user_id) > 36:
            raise OfferwallMeCallbackError("Invalid callback user ID.")
        try:
            user_id = str(UUID(user_id))
        except ValueError as error:
            raise OfferwallMeCallbackError("Invalid callback user ID.") from error
        if not transaction_id or len(transaction_id) > 128:
            raise OfferwallMeCallbackError("Invalid callback transaction ID.")
        if status not in {"1", "2"}:
            raise OfferwallMeCallbackError("Invalid callback status.")
        if not SIGNED_AMOUNT_PATTERN.fullmatch(reward_text):
            raise OfferwallMeCallbackError("Invalid callback reward.")
        if not AMOUNT_PATTERN.fullmatch(rate_text):
            raise OfferwallMeCallbackError("Invalid callback exchange rate.")
        if not SIGNED_AMOUNT_PATTERN.fullmatch(payout_text):
            raise OfferwallMeCallbackError("Invalid callback payout.")
        if not HASH_PATTERN.fullmatch(signature):
            raise OfferwallMeCallbackError("Missing or malformed callback signature.")

        expected_signature = hashlib.md5(
            f"{values.get('subId', '')}{transaction_id}{reward_text}{secret_key}".encode(
                "utf-8"
            ),
            usedforsecurity=False,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, signature.lower()):
            raise OfferwallMeCallbackError("Invalid callback signature.")

        try:
            reward = abs(Decimal(reward_text))
            rate = Decimal(rate_text)
            payout_usd = abs(Decimal(payout_text))
            configured_rate = settings.offerwall_me_exchange_rate
            amount_usd = (reward / configured_rate).quantize(Decimal("0.00000001"))
            raw_reward = Decimal(reward_text)
        except (InvalidOperation, ZeroDivisionError) as error:
            raise OfferwallMeCallbackError("Invalid callback amount.") from error
        if (
            not reward.is_finite()
            or reward == 0
            or (status == "1" and raw_reward <= 0)
            or not rate.is_finite()
            or rate != configured_rate
            or not payout_usd.is_finite()
            or payout_usd <= 0
            or payout_usd.quantize(Decimal("0.00000001")) != amount_usd
            or amount_usd > Decimal("9999999999.99999999")
        ):
            raise OfferwallMeCallbackError(
                "Callback reward, payout, or exchange rate does not match configuration."
            )

        return OfferwallMeCallback(
            user_id=user_id,
            transaction_id=transaction_id,
            status=status,
            amount_usd=amount_usd,
            reward=reward_text,
            reward_value=rate_text,
            payout_usd=payout_usd,
            offer_name=values.get("offer_name", "")[:255],
            offer_type=values.get("offer_type", "")[:32],
            reward_name=values.get("reward_name", "")[:64],
            country=values.get("country", "").upper()[:2],
        )


offerwall_me_adapter = OfferwallMeAdapter()
