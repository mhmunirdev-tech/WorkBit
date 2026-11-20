from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.core.config import settings

OFFERWALL_AD_SLUG = "offerwall-ad"
AMOUNT_PATTERN = re.compile(r"^\d{1,10}(?:\.\d{1,8})?$")
SIGNATURE_PATTERN = re.compile(r"^sha256=([0-9a-fA-F]{64})$")
EVENTS = frozenset(
    {
        "conversion.approved",
        "conversion.held",
        "conversion.released",
        "conversion.reversed",
        "conversion.rejected",
    }
)


class OfferwallAdConfigurationError(RuntimeError):
    pass


class OfferwallAdCallbackError(ValueError):
    pass


@dataclass(frozen=True)
class OfferwallAdCallback:
    user_id: str
    transaction_id: str
    conversion_id: str
    offer_id: str
    offer_name: str
    payout: Decimal
    currency: str
    status: str
    event: str
    event_id: str
    network: str
    campaign_id: str
    click_id: str
    unix_timestamp: str
    is_test: bool


class OfferwallAdAdapter:
    def verify_callback(
        self,
        payload: dict[str, object],
        raw_body: bytes,
        signature: str,
        signature_source: str,
        event_header: str,
        event_id: str,
    ) -> OfferwallAdCallback:
        secret = settings.offerwall_ad_signing_secret or ""
        if not secret.strip():
            raise OfferwallAdConfigurationError(
                "Offerwall Ad signing secret is not configured."
            )
        if signature_source.strip().casefold() != "body":
            raise OfferwallAdCallbackError(
                "Offerwall Ad callback must use signed JSON body delivery."
            )

        match = SIGNATURE_PATTERN.fullmatch(signature.strip())
        if match is None:
            raise OfferwallAdCallbackError("Malformed Offerwall Ad signature.")
        expected = hmac.new(
            secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, match.group(1).lower()):
            raise OfferwallAdCallbackError("Invalid Offerwall Ad signature.")

        event = self._text(payload, "event", required=True)
        event_header = event_header.strip()
        event_id = event_id.strip()
        if event not in EVENTS or event_header != event:
            raise OfferwallAdCallbackError("Unsupported or mismatched callback event.")
        if not event_id or len(event_id) > 128:
            raise OfferwallAdCallbackError("Invalid Offerwall Ad event ID.")

        user_id = self._text(payload, "subid", required=True)
        try:
            user_id = str(UUID(user_id))
        except ValueError as error:
            raise OfferwallAdCallbackError("Invalid callback visitor ID.") from error

        transaction_id = self._text(payload, "transaction_id", required=True)
        if not transaction_id or len(transaction_id) > 128:
            raise OfferwallAdCallbackError("Invalid callback transaction ID.")

        payout_text = self._text(payload, "payout", required=True)
        if not AMOUNT_PATTERN.fullmatch(payout_text):
            raise OfferwallAdCallbackError("Invalid callback payout.")
        try:
            payout = Decimal(payout_text)
        except InvalidOperation as error:
            raise OfferwallAdCallbackError("Invalid callback payout.") from error
        if not payout.is_finite() or payout <= 0:
            raise OfferwallAdCallbackError("Callback payout must be positive.")

        currency = self._text(payload, "currency", required=True).upper()
        if currency != "USD":
            raise OfferwallAdCallbackError(
                "Offerwall Ad payout currency must match WorkBit's USD wallet."
            )

        status = self._text(payload, "status", required=True).casefold()
        if status not in {"approved", "held", "reversed", "rejected"}:
            raise OfferwallAdCallbackError("Invalid Offerwall Ad conversion status.")
        is_test = payload.get("test", False)
        if not isinstance(is_test, bool):
            raise OfferwallAdCallbackError("Invalid Offerwall Ad test flag.")

        return OfferwallAdCallback(
            user_id=user_id,
            transaction_id=transaction_id,
            conversion_id=self._text(payload, "conversion_id")[:128],
            offer_id=self._text(payload, "offer_id")[:128],
            offer_name=self._text(payload, "offer_name")[:255],
            payout=payout,
            currency=currency,
            status=status,
            event=event,
            event_id=event_id,
            network=self._text(payload, "network")[:128],
            campaign_id=self._text(payload, "campaign_id")[:128],
            click_id=self._text(payload, "click_id")[:128],
            unix_timestamp=self._text(payload, "unix_timestamp")[:32],
            is_test=is_test,
        )

    @staticmethod
    def _text(
        payload: dict[str, object], key: str, required: bool = False
    ) -> str:
        value = payload.get(key)
        if value is None:
            if required:
                raise OfferwallAdCallbackError(
                    f"Missing Offerwall Ad callback field: {key}."
                )
            return ""
        if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
            raise OfferwallAdCallbackError(
                f"Invalid Offerwall Ad callback field: {key}."
            )
        text = str(value).strip()
        if required and not text:
            raise OfferwallAdCallbackError(
                f"Missing Offerwall Ad callback field: {key}."
            )
        return text


offerwall_ad_adapter = OfferwallAdAdapter()
