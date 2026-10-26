from __future__ import annotations

from app.integrations.ad_providers.base import AdNetworkAdapter, UnconfiguredAdAdapter


AD_NETWORK_SLUGS = ("workbit-ad-manager", "other-ads")


class AdAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, AdNetworkAdapter] = {
            slug: UnconfiguredAdAdapter(slug) for slug in AD_NETWORK_SLUGS
        }

    def register(self, adapter: AdNetworkAdapter) -> None:
        self._adapters[adapter.slug.lower()] = adapter

    def get(self, slug: str) -> AdNetworkAdapter | None:
        return self._adapters.get(slug.lower())


ad_adapter_registry = AdAdapterRegistry()
