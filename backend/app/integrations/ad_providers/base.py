from __future__ import annotations


class AdProviderUnavailableError(RuntimeError):
    pass


class AdNetworkAdapter:
    """Contract for server-managed ad providers; display-only embeds stay in the frontend."""

    slug: str

    async def render_placement(self, placement_id: str, user_id: str, country: str, device: str) -> object:
        raise NotImplementedError


class UnconfiguredAdAdapter(AdNetworkAdapter):
    def __init__(self, slug: str) -> None:
        self.slug = slug

    async def render_placement(self, placement_id: str, user_id: str, country: str, device: str) -> object:
        raise AdProviderUnavailableError(f"Ad provider '{self.slug}' is not configured.")
