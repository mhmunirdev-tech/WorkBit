from __future__ import annotations


AD_NETWORK_SLUGS = ("workbit-ad-manager", "other-ads")


class AdProviderUnavailableError(RuntimeError):
    pass


class AdNetworkAdapter:
    """Ad monetization contract kept separate from offer and reward processing."""

    slug: str

    async def render_placement(self, placement_id: str, user_id: str, country: str, device: str) -> object:
        raise NotImplementedError


class UnconfiguredAdAdapter(AdNetworkAdapter):
    def __init__(self, slug: str) -> None:
        self.slug = slug

    async def render_placement(self, placement_id: str, user_id: str, country: str, device: str) -> object:
        raise AdProviderUnavailableError(f"Ad provider '{self.slug}' is not configured.")


class AdAdapterRegistry:
    def __init__(self) -> None:
        self._adapters = {slug: UnconfiguredAdAdapter(slug) for slug in AD_NETWORK_SLUGS}

    def get(self, slug: str) -> AdNetworkAdapter | None:
        return self._adapters.get(slug.lower())


ad_adapter_registry = AdAdapterRegistry()
