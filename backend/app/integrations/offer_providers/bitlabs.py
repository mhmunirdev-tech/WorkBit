from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlsplit

from app.core.config import settings

BITLABS_SLUG = "bitlabs"
BITLABS_WALL_URL = "https://web.bitlabs.ai/"
AMOUNT_PATTERN = re.compile(r"^-?\d{1,10}(?:\.\d{1,8})?$")
HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


class BitLabsConfigurationError(RuntimeError):
    pass


class BitLabsCallbackError(ValueError):
    pass


@dataclass(frozen=True)
class BitLabsCallback:
    user_id: str
    transaction_id: str
    payout_usd: Decimal
    activity_type: str
    reference_id: str
    offer_id: str
    task_id: str
    offer_state: str
    debug: bool


class BitLabsAdapter:
    def build_wall_url(self, user_id: str) -> str:
        if not settings.bitlabs_enabled:
            raise BitLabsConfigurationError("BitLabs integration is disabled.")
        token = (settings.bitlabs_api_key or "").strip()
        if not token:
            raise BitLabsConfigurationError("BitLabs App/API Token is not configured.")
        return f"{BITLABS_WALL_URL}?{urlencode({'uid': user_id, 'token': token})}"

    def verify_callback(
        self,
        values: dict[str, str],
        raw_query: str,
    ) -> BitLabsCallback:
        if not settings.bitlabs_enabled:
            raise BitLabsConfigurationError("BitLabs integration is disabled.")

        secret = (settings.bitlabs_postback_secret or "").strip()
        callback_url = (settings.bitlabs_callback_url or "").strip()
        if not secret or not callback_url:
            raise BitLabsConfigurationError(
                "BitLabs callback secret and public callback URL must be configured."
            )
        try:
            parsed_url = urlsplit(callback_url)
        except ValueError as error:
            raise BitLabsConfigurationError("BitLabs callback URL is invalid.") from error
        if (
            parsed_url.scheme != "https"
            or not parsed_url.netloc
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.path != "/api/v1/postbacks/bitlabs"
            or parsed_url.query
            or parsed_url.fragment
            or callback_url.endswith("/")
        ):
            raise BitLabsConfigurationError(
                "BitLabs callback URL must be an HTTPS URL without query or fragment."
            )

        prefix, separator, supplied_hash = raw_query.rpartition("&hash=")
        if not separator or not HASH_PATTERN.fullmatch(supplied_hash):
            raise BitLabsCallbackError("Missing or malformed callback hash.")
        signed_url = f"{callback_url}?{prefix}"
        try:
            signed_message = signed_url.encode("ascii")
        except UnicodeEncodeError as error:
            raise BitLabsConfigurationError("BitLabs callback URL must be ASCII.") from error
        expected_hash = hmac.new(
            secret.encode("utf-8"),
            signed_message,
            hashlib.sha1,
        ).hexdigest()
        if not hmac.compare_digest(expected_hash, supplied_hash.lower()):
            raise BitLabsCallbackError("Invalid callback hash.")

        user_id = self._value(values, "uid", "user_id")
        transaction_id = self._value(values, "tx", "transaction_id")
        amount_text = self._value(values, "usd", "value_usd")
        activity_type = self._value(values, "activity_type", "activity", "type").upper()
        if not user_id or len(user_id) > 65:
            raise BitLabsCallbackError("Invalid callback user id.")
        if not transaction_id or len(transaction_id) > 128:
            raise BitLabsCallbackError("Invalid callback transaction id.")
        if not activity_type:
            raise BitLabsCallbackError("Missing callback activity type.")
        if not AMOUNT_PATTERN.fullmatch(amount_text):
            raise BitLabsCallbackError("Invalid callback USD amount.")
        try:
            payout_usd = Decimal(amount_text)
        except InvalidOperation as error:
            raise BitLabsCallbackError("Invalid callback USD amount.") from error
        if not payout_usd.is_finite():
            raise BitLabsCallbackError("Invalid callback USD amount.")

        return BitLabsCallback(
            user_id=user_id,
            transaction_id=transaction_id,
            payout_usd=payout_usd,
            activity_type=activity_type,
            reference_id=self._value(values, "ref", "reference_id"),
            offer_id=self._value(values, "offer_id")[:128],
            task_id=self._value(values, "task_id", "offer_task_id")[:128],
            offer_state=self._value(values, "offer_state", "offer_task_state", "state").upper(),
            debug=self._value(values, "debug").lower() in {"1", "true", "yes"},
        )

    @staticmethod
    def _value(values: dict[str, str], *names: str) -> str:
        for name in names:
            value = values.get(name)
            if value is not None:
                return value.strip()
        return ""


bitlabs_adapter = BitLabsAdapter()
