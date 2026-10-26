from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from uuid import UUID

from app.core.config import settings

OFFERWALL_GG_SLUG = "offerwall-gg"
WALL_ORIGIN = "https://offerwall.gg"
AMOUNT_PATTERN = re.compile(r"^-?\d{1,10}(?:\.\d{1,4})?$")


class OfferwallGGConfigurationError(RuntimeError):
    pass


class OfferwallGGCallbackError(ValueError):
    pass


@dataclass(frozen=True)
class OfferwallGGCallback:
    user_id: str
    transaction_id: str
    offer_id: str
    amount: Decimal
    currency: str
    status: str
    test: bool
    offer_name: str
    goal_id: str
    timestamp: str


class OfferwallGGAdapter:
    def _credentials(self) -> tuple[str, str]:
        if not settings.offerwall_gg_enabled:
            raise OfferwallGGConfigurationError("Offerwall.GG integration is disabled.")
        public_key = (settings.offerwall_gg_public_key or "").strip()
        secret_key = settings.offerwall_gg_secret_key or ""
        if not public_key or not secret_key:
            raise OfferwallGGConfigurationError("Offerwall.GG credentials are not configured.")
        if len(public_key) != 32:
            raise OfferwallGGConfigurationError("Offerwall.GG public key must be 32 characters.")
        return public_key, secret_key

    def build_wall_url(self, user_id: str) -> str:
        public_key, secret_key = self._credentials()
        signed_parameters = {"appId": public_key, "userId": user_id}
        canonical_query = urlencode(sorted(signed_parameters.items()))
        signature = hmac.new(
            secret_key.encode("utf-8"),
            canonical_query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return (
            f"{WALL_ORIGIN}/wall/{public_key}?"
            + urlencode({"userId": user_id, "signature": signature})
        )

    def verify_callback(self, values: dict[str, str]) -> OfferwallGGCallback:
        _, secret_key = self._credentials()
        user_id = values.get("userId", "")
        transaction_id = values.get("transactionId", "")
        amount_text = values.get("currencyAmount", "")
        signature = values.get("signature", "")

        if not user_id or len(user_id) > 36:
            raise OfferwallGGCallbackError("Invalid callback user id.")
        if not transaction_id or len(transaction_id) > 128:
            raise OfferwallGGCallbackError("Invalid callback transaction id.")
        if not AMOUNT_PATTERN.fullmatch(amount_text):
            raise OfferwallGGCallbackError("Invalid callback amount.")

        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            f"{user_id}:{transaction_id}:{amount_text}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, signature):
            raise OfferwallGGCallbackError("Invalid callback signature.")

        try:
            amount = Decimal(amount_text)
        except InvalidOperation as error:
            raise OfferwallGGCallbackError("Invalid callback amount.") from error
        if not amount.is_finite() or amount == 0:
            raise OfferwallGGCallbackError("Callback amount must be non-zero.")

        status = values.get("status", "")
        if (status == "credited" and amount < 0) or (status == "reversed" and amount > 0):
            raise OfferwallGGCallbackError("Callback status does not match the signed amount.")
        if status not in {"credited", "reversed"}:
            raise OfferwallGGCallbackError("Unsupported callback status.")

        currency = values.get("currencyName", "").strip().upper()
        configured_currency = settings.offerwall_gg_currency_name.strip().upper()
        if not currency or currency != configured_currency or len(currency) != 3:
            raise OfferwallGGCallbackError("Callback currency does not match the configured currency.")

        test_value = values.get("test", "0")
        if test_value not in {"0", "1"}:
            raise OfferwallGGCallbackError("Invalid callback test flag.")
        is_test = test_value == "1"

        if not is_test:
            try:
                user_id = str(UUID(user_id))
            except ValueError as error:
                raise OfferwallGGCallbackError("Invalid callback user id.") from error

        return OfferwallGGCallback(
            user_id=user_id,
            transaction_id=transaction_id,
            offer_id=values.get("offerId", "")[:128],
            amount=amount,
            currency=currency,
            status=status,
            test=is_test,
            offer_name=values.get("offerName", "")[:255],
            goal_id=values.get("goalId", "")[:128],
            timestamp=values.get("timestamp", "")[:32],
        )


offerwall_gg_adapter = OfferwallGGAdapter()
