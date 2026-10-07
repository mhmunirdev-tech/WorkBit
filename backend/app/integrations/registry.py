from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.schemas.offers import OfferRead


OFFER_PROVIDER_SLUGS = (
    "lootably",
    "adgem",
    "cpalead",
    "offerwall-gg",
    "monlix",
    "bitlabs",
    "adgate",
    "torox",
    "adswedmedia",
    "revu",
)


class ProviderUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifiedConversion:
    external_transaction_id: str
    click_id: str
    external_offer_id: str
    provider_payout: Decimal
    currency: str
    status: str
    occurred_at: datetime | None = None


class OfferNetworkAdapter:
    """Provider contract; implementations must follow that provider's current docs."""

    slug: str

    async def sync_offers(self, country: str) -> list[OfferRead]:
        raise NotImplementedError

    async def build_tracking_url(
        self, external_offer_id: str, click_id: str, user_id: str, country: str, device: str
    ) -> str:
        raise NotImplementedError

    def verify_postback(
        self, query: dict[str, str], headers: dict[str, str], body: bytes
    ) -> VerifiedConversion:
        raise NotImplementedError


class UnconfiguredOfferAdapter(OfferNetworkAdapter):
    def __init__(self, slug: str) -> None:
        self.slug = slug

    def _unavailable(self) -> ProviderUnavailableError:
        return ProviderUnavailableError(f"Offer provider '{self.slug}' is not configured.")

    async def sync_offers(self, country: str) -> list[OfferRead]:
        raise self._unavailable()

    async def build_tracking_url(
        self, external_offer_id: str, click_id: str, user_id: str, country: str, device: str
    ) -> str:
        raise self._unavailable()

    def verify_postback(
        self, query: dict[str, str], headers: dict[str, str], body: bytes
    ) -> VerifiedConversion:
        raise self._unavailable()


class OfferAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, OfferNetworkAdapter] = {
            slug: UnconfiguredOfferAdapter(slug) for slug in OFFER_PROVIDER_SLUGS
        }

    def get(self, slug: str) -> OfferNetworkAdapter | None:
        return self._adapters.get(slug.lower())


offer_adapter_registry = OfferAdapterRegistry()
