from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from uuid import UUID

from app.core.config import settings

CPX_RESEARCH_WALL_URL = "https://offers.cpx-research.com/index.php"
APP_ID_PATTERN = re.compile(r"^[0-9]{1,20}$")
AMOUNT_PATTERN = re.compile(r"^-?\d{1,10}(?:\.\d{1,8})?$")
HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")


class CPXResearchConfigurationError(RuntimeError):
    pass


class CPXResearchCallbackError(ValueError):
    pass


@dataclass(frozen=True)
class CPXResearchCallback:
    user_id: str
    transaction_id: str
    status: str
    amount_usd: Decimal
    amount_local: str
    offer_id: str
    event_type: str
    sub_id_1: str
    sub_id_2: str
    ip_click: str


class CPXResearchAdapter:
    def build_wall_url(self, user_id: str) -> str:
        if not settings.cpx_research_enabled:
            raise CPXResearchConfigurationError("CPX Research integration is disabled.")

        app_id = (settings.cpx_research_app_id or "").strip()
        app_secure_hash = (settings.cpx_research_secure_hash or "").strip()
        if not APP_ID_PATTERN.fullmatch(app_id) or not app_secure_hash.strip():
            raise CPXResearchConfigurationError(
                "CPX Research App ID and secure hash must be configured."
            )
        try:
            UUID(user_id)
        except ValueError as error:
            raise CPXResearchConfigurationError("WorkBit user ID must be a UUID.") from error

        secure_hash = hashlib.md5(
            f"{user_id}_{app_secure_hash}".encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()
        return f"{CPX_RESEARCH_WALL_URL}?{urlencode({
            'app_id': app_id,
            'ext_user_id': user_id,
            'secure_hash': secure_hash,
        })}"

    def verify_callback(self, values: dict[str, str]) -> CPXResearchCallback:
        app_secure_hash = (settings.cpx_research_secure_hash or "").strip()
        if not app_secure_hash:
            raise CPXResearchConfigurationError(
                "CPX Research Security Hash is not configured."
            )

        transaction_id = values.get("trans_id", "").strip()
        user_id = values.get("user_id", "").strip()
        status = values.get("status", "").strip()
        amount_text = values.get("amount_usd", "").strip()
        supplied_hash = values.get("hash", "").strip()

        if not transaction_id or len(transaction_id) > 128:
            raise CPXResearchCallbackError("Invalid CPX Research transaction ID.")
        if not user_id or len(user_id) > 36:
            raise CPXResearchCallbackError("Invalid CPX Research user ID.")
        try:
            user_id = str(UUID(user_id))
        except ValueError as error:
            raise CPXResearchCallbackError("Invalid CPX Research user ID.") from error
        if status not in {"1", "2"}:
            raise CPXResearchCallbackError("Invalid CPX Research callback status.")
        if not AMOUNT_PATTERN.fullmatch(amount_text):
            raise CPXResearchCallbackError("Invalid CPX Research USD amount.")
        if not HASH_PATTERN.fullmatch(supplied_hash):
            raise CPXResearchCallbackError("Missing or malformed CPX Research hash.")

        expected_hash = hashlib.md5(
            f"{transaction_id}-{app_secure_hash}".encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()
        if not hmac.compare_digest(expected_hash, supplied_hash.lower()):
            raise CPXResearchCallbackError("Invalid CPX Research callback hash.")

        try:
            amount_usd = Decimal(amount_text)
        except InvalidOperation as error:
            raise CPXResearchCallbackError("Invalid CPX Research USD amount.") from error
        if not amount_usd.is_finite() or amount_usd < 0:
            raise CPXResearchCallbackError("Invalid CPX Research USD amount.")

        return CPXResearchCallback(
            user_id=user_id,
            transaction_id=transaction_id,
            status=status,
            amount_usd=amount_usd,
            amount_local=values.get("amount_local", "").strip()[:64],
            offer_id=values.get("offer_id", "").strip()[:128],
            event_type=values.get("type", "").strip()[:32],
            sub_id_1=values.get("sub_id", "").strip()[:128],
            sub_id_2=values.get("sub_id_2", "").strip()[:128],
            ip_click=values.get("ip_click", "").strip()[:64],
        )


cpx_research_adapter = CPXResearchAdapter()
