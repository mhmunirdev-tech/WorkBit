import asyncio

import pytest

from app.integrations.ad_providers import (
    AdAdapterRegistry,
    AdNetworkAdapter,
    AdProviderUnavailableError,
    UnconfiguredAdAdapter,
    ad_adapter_registry,
)


def test_ad_provider_registry_is_case_insensitive_and_keeps_unconfigured_defaults():
    assert isinstance(ad_adapter_registry.get("WORKBIT-AD-MANAGER"), UnconfiguredAdAdapter)
    assert ad_adapter_registry.get("unknown-provider") is None


def test_ad_provider_registry_accepts_provider_specific_adapters():
    class TestAdapter(AdNetworkAdapter):
        slug = "test-provider"

    registry = AdAdapterRegistry()
    adapter = TestAdapter()
    registry.register(adapter)

    assert registry.get("TEST-PROVIDER") is adapter


def test_unconfigured_provider_fails_closed():
    adapter = UnconfiguredAdAdapter("test-provider")

    with pytest.raises(AdProviderUnavailableError):
        asyncio.run(adapter.render_placement("placement", "user", "BD", "WEB"))
