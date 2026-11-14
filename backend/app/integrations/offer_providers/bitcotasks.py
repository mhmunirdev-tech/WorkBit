from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.core.config import settings

BITCOTASKS_SLUG = "bitcotasks"
AMOUNT_PATTERN = re.compile(r"^\d{1,10}(?:\.\d{1,8})?$")
SIGNATURE_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")
MAX_USD_AMOUNT = Decimal("9999999999.99999999")


class BitcoTasksConfigurationError(RuntimeError):
    pass


class BitcoTasksCallbackError(ValueError):
    pass


@dataclass(frozen=True)
class BitcoTasksCallback:
    user_id: str
    transaction_id: str
    offer_name: str
    offer_type: str
    amount_usd: Decimal
    reported_payout_usd: Decimal
    reward: str
    reward_name: str
    reward_value: Decimal
    user_ip: str
    country: str
    status: str
    debug: bool


class BitcoTasksAdapter:
    @staticmethod
    def public_api_key() -> str:
        api_key = (settings.bitcotasks_api_key or "").strip()
        if not api_key or len(api_key) > 256:
            raise BitcoTasksConfigurationError(
                "BitcoTasks API key is not configured."
            )
        return api_key

    def build_sdk_config(self, user_id: str) -> dict[str, str]:
        if not settings.bitcotasks_enabled:
            raise BitcoTasksConfigurationError("BitcoTasks integration is disabled.")
        try:
            sub_id = UUID(user_id).hex
        except ValueError as error:
            raise BitcoTasksConfigurationError(
                "WorkBit user ID must be a UUID."
            ) from error
        sdk_config = {"api_key": self.public_api_key(), "sub_id": sub_id}
        secret = (settings.bitcotasks_secret_key or "").strip()
        if secret:
            sdk_config["sig"] = hmac.new(
                secret.encode("utf-8"),
                sub_id.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
        return sdk_config

    def verify_callback(
        self, values: dict[str, str], secret_key: str | None = None
    ) -> BitcoTasksCallback:
        secret = secret_key if secret_key is not None else settings.bitcotasks_secret_key
        secret = (secret or "").strip()
        exchange_rate = settings.bitcotasks_exchange_rate
        currency_name = settings.bitcotasks_currency_name.strip()
        if (
            not secret
            or exchange_rate is None
            or not exchange_rate.is_finite()
            or exchange_rate <= 0
            or not currency_name
            or len(currency_name) > 64
        ):
            raise BitcoTasksConfigurationError(
                "BitcoTasks secret key, currency name, and exchange rate must be configured."
            )

        sub_id = values.get("subid", "")
        transaction_id = values.get("transid", "")
        reward_text = values.get("reward", "")
        signature = values.get("signature", "").strip()
        if not sub_id or not transaction_id or not reward_text:
            raise BitcoTasksCallbackError("Missing signed callback fields.")
        if (
            sub_id != sub_id.strip()
            or transaction_id != transaction_id.strip()
            or reward_text != reward_text.strip()
            or len(transaction_id) > 128
            or not AMOUNT_PATTERN.fullmatch(reward_text)
            or not SIGNATURE_PATTERN.fullmatch(signature)
        ):
            raise BitcoTasksCallbackError("Malformed signed callback fields.")

        expected_signature = hashlib.md5(
            f"{sub_id}{transaction_id}{reward_text}{secret}".encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, signature.lower()):
            raise BitcoTasksCallbackError("Invalid callback signature.")

        debug_value = values.get("debug", "").strip().lower()
        if debug_value not in {"", "0", "1", "false", "true"}:
            raise BitcoTasksCallbackError("Invalid callback debug flag.")
        debug = debug_value in {"1", "true"}
        if debug:
            return BitcoTasksCallback(
                user_id="",
                transaction_id="",
                offer_name="",
                offer_type="",
                amount_usd=Decimal("0"),
                reported_payout_usd=Decimal("0"),
                reward=reward_text,
                reward_name="",
                reward_value=Decimal("0"),
                user_ip="",
                country="",
                status="",
                debug=True,
            )

        if len(sub_id) != 32:
            raise BitcoTasksCallbackError("Invalid callback user ID.")
        try:
            user_id = str(UUID(hex=sub_id))
            reward = Decimal(reward_text)
            payout_usd = Decimal(values.get("payout", ""))
            reward_value = Decimal(values.get("reward_value", ""))
        except (ValueError, InvalidOperation) as error:
            raise BitcoTasksCallbackError("Invalid callback amount or user ID.") from error

        status = values.get("status", "").strip()
        reward_name = values.get("reward_name", "").strip()
        if status not in {"1", "2"}:
            raise BitcoTasksCallbackError("Invalid callback status.")
        if reward_name.casefold() != currency_name.casefold():
            raise BitcoTasksCallbackError("Callback reward currency does not match configuration.")
        if (
            not reward.is_finite()
            or reward <= 0
            or not reward_value.is_finite()
            or reward_value != exchange_rate
            or not payout_usd.is_finite()
            or payout_usd <= 0
        ):
            raise BitcoTasksCallbackError(
                "Callback reward, payout, or exchange rate is invalid."
            )

        amount_usd_unrounded = reward / exchange_rate
        if amount_usd_unrounded > MAX_USD_AMOUNT:
            raise BitcoTasksCallbackError("Callback USD amount is invalid.")
        try:
            amount_usd = amount_usd_unrounded.quantize(Decimal("0.00000001"))
        except InvalidOperation as error:
            raise BitcoTasksCallbackError("Callback USD amount is invalid.") from error
        if not amount_usd.is_finite() or amount_usd <= 0:
            raise BitcoTasksCallbackError("Callback USD amount is invalid.")

        return BitcoTasksCallback(
            user_id=user_id,
            transaction_id=transaction_id,
            offer_name=values.get("offer_name", "")[:200],
            offer_type=values.get("offer_type", "")[:80],
            amount_usd=amount_usd,
            reported_payout_usd=payout_usd,
            reward=reward_text,
            reward_name=reward_name,
            reward_value=reward_value,
            user_ip=values.get("userip", "")[:64],
            country=values.get("country", "")[:2].upper(),
            status=status,
            debug=False,
        )


bitcotasks_adapter = BitcoTasksAdapter()
