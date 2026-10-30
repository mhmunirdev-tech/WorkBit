from __future__ import annotations

import base64
import hashlib
import hmac
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlsplit
from uuid import UUID, uuid4

from app.core.config import settings

THEOREMREACH_SLUG = "theoremreach"
THEOREMREACH_ENTRY_URL = "https://theoremreach.com/respondent_entry/direct"
AMOUNT_PATTERN = re.compile(r"^-?\d{1,10}(?:\.\d{1,8})?$")
HASH_PATTERN = re.compile(r"^[A-Za-z0-9_-]{27}$")


class TheoremReachConfigurationError(RuntimeError):
    pass


class TheoremReachCallbackError(ValueError):
    pass


@dataclass(frozen=True)
class TheoremReachCallback:
    user_id: str
    transaction_id: str
    payout_usd: Decimal
    reversal: bool
    debug: bool
    external_transaction_id: str
    reward: str


class TheoremReachAdapter:
    def _configuration(
        self,
        require_enabled: bool = True,
    ) -> tuple[str, str, str, str]:
        if require_enabled and not settings.theoremreach_enabled:
            raise TheoremReachConfigurationError("TheoremReach integration is disabled.")

        api_key = (settings.theoremreach_api_key or "").strip()
        secret_key = settings.theoremreach_secret_key or ""
        partner_id = (settings.theoremreach_partner_id or "").strip()
        callback_url = (settings.theoremreach_callback_url or "").strip()
        if not api_key or not secret_key or not partner_id or not callback_url:
            raise TheoremReachConfigurationError(
                "TheoremReach API key, secret key, partner ID, and callback URL must be configured."
            )

        try:
            parsed_url = urlsplit(callback_url)
        except ValueError as error:
            raise TheoremReachConfigurationError("TheoremReach callback URL is invalid.") from error
        if (
            parsed_url.scheme != "https"
            or not parsed_url.netloc
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.path != "/api/v1/postbacks/theoremreach"
            or parsed_url.query
            or parsed_url.fragment
            or callback_url.endswith("/")
        ):
            raise TheoremReachConfigurationError(
                "TheoremReach callback URL must be the HTTPS callback endpoint without a query or trailing slash."
            )

        if settings.theoremreach_exchange_rate < 10:
            raise TheoremReachConfigurationError(
                "TheoremReach exchange rate must be at least 10."
            )
        if (
            not settings.theoremreach_currency_name_singular.strip()
            or not settings.theoremreach_currency_name_plural.strip()
        ):
            raise TheoremReachConfigurationError(
                "TheoremReach singular and plural currency names must be configured."
            )
        return api_key, secret_key, partner_id, callback_url

    def build_wall_url(self, user_id: str) -> str:
        api_key, secret_key, partner_id, _ = self._configuration()
        try:
            UUID(user_id)
        except ValueError as error:
            raise TheoremReachConfigurationError("WorkBit user ID must be a UUID.") from error

        transaction_id = uuid4().hex
        query = urlencode(
            [
                ("api_key", api_key),
                ("user_id", user_id),
                ("transaction_id", transaction_id),
                ("currency_name_plural", settings.theoremreach_currency_name_plural.strip()),
                ("currency_name_singular", settings.theoremreach_currency_name_singular.strip()),
                ("exchange_rate", format(settings.theoremreach_exchange_rate, "f")),
                ("external_id", user_id),
                ("partner_id", partner_id),
                ("decimals_to_display", str(settings.theoremreach_decimals_to_display)),
            ]
        )
        unsigned_url = f"{THEOREMREACH_ENTRY_URL}?{query}"
        signature = self._signature(secret_key, unsigned_url)
        return f"{unsigned_url}&hash={signature}"

    def verify_callback(
        self,
        values: dict[str, str],
        raw_query: str,
    ) -> TheoremReachCallback:
        _, secret_key, partner_id, callback_url = self._configuration(
            require_enabled=False
        )
        prefix, separator, supplied_hash = raw_query.rpartition("&hash=")
        if not separator:
            raise TheoremReachCallbackError("Missing callback hash.")
        if not HASH_PATTERN.fullmatch(supplied_hash):
            raise TheoremReachCallbackError("Malformed callback hash.")

        signed_url = f"{callback_url}?{prefix}"
        expected_hash = self._signature(secret_key, signed_url)
        if not hmac.compare_digest(expected_hash, supplied_hash):
            raise TheoremReachCallbackError("Invalid callback hash.")

        debug_value = self._value(values, "debug").lower()
        if debug_value not in {"", "0", "1", "false", "true"}:
            raise TheoremReachCallbackError("Invalid callback debug flag.")
        debug = debug_value in {"1", "true"}

        supplied_partner_id = self._value(values, "partner_id")
        if supplied_partner_id and supplied_partner_id != partner_id:
            raise TheoremReachCallbackError("Callback partner ID does not match.")

        if debug:
            return TheoremReachCallback(
                user_id="",
                transaction_id="",
                payout_usd=Decimal("0"),
                reversal=False,
                debug=True,
                external_transaction_id="",
                reward=self._value(values, "reward"),
            )
        if not settings.theoremreach_enabled:
            raise TheoremReachConfigurationError("TheoremReach integration is disabled.")

        user_id = self._value(values, "user_id") or self._value(values, "external_id")
        transaction_id = self._value(values, "tx_id") or self._value(
            values, "transaction_id"
        )
        amount_text = self._value(values, "reward_amount_in_dollars") or self._value(
            values, "currency"
        )
        reversal_value = self._value(values, "reversal").lower()
        if reversal_value not in {"", "0", "1", "false", "true"}:
            raise TheoremReachCallbackError("Invalid callback reversal flag.")
        reversal = reversal_value in {"1", "true"}

        if not user_id or len(user_id) > 36:
            raise TheoremReachCallbackError("Invalid callback user ID.")
        try:
            user_id = str(UUID(user_id))
        except ValueError as error:
            raise TheoremReachCallbackError("Invalid callback user ID.") from error
        if not transaction_id or len(transaction_id) > 128:
            raise TheoremReachCallbackError("Invalid callback transaction ID.")
        if not AMOUNT_PATTERN.fullmatch(amount_text):
            raise TheoremReachCallbackError("Invalid callback USD amount.")
        try:
            amount = Decimal(amount_text)
        except InvalidOperation as error:
            raise TheoremReachCallbackError("Invalid callback USD amount.") from error
        if not amount.is_finite() or amount == 0:
            raise TheoremReachCallbackError("Callback USD amount must be non-zero.")
        if reversal != (amount < 0):
            raise TheoremReachCallbackError(
                "Callback reversal flag does not match the signed amount."
            )

        return TheoremReachCallback(
            user_id=user_id,
            transaction_id=transaction_id,
            payout_usd=abs(amount),
            reversal=reversal,
            debug=False,
            external_transaction_id=self._value(values, "external_transaction_id")[:128],
            reward=self._value(values, "reward")[:64],
        )

    @staticmethod
    def _signature(secret_key: str, url: str) -> str:
        digest = hmac.new(
            secret_key.encode("utf-8"),
            url.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    @staticmethod
    def _value(values: dict[str, str], *names: str) -> str:
        for name in names:
            value = values.get(name)
            if value is not None:
                return value.strip()
        return ""


theoremreach_adapter = TheoremReachAdapter()
