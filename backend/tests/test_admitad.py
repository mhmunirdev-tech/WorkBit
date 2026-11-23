import httpx

from app.core.config import settings

CLIENT_ID = "test-admitad-client"
CLIENT_SECRET = "test-admitad-secret"
WEBSITE_ID = "12345"


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"},
    )
    assert response.status_code == 200


def configure_admitad(monkeypatch):
    monkeypatch.setattr(settings, "admitad_enabled", True)
    monkeypatch.setattr(settings, "admitad_client_id", CLIENT_ID)
    monkeypatch.setattr(settings, "admitad_client_secret", CLIENT_SECRET)
    monkeypatch.setattr(settings, "admitad_website_id", WEBSITE_ID)


def campaign(
    campaign_id=42,
    *,
    name="Partner store",
    status="active",
    connected=True,
    allow_deeplink=True,
    action_countries=None,
):
    return {
        "id": campaign_id,
        "name": name,
        "status": status,
        "connection_status": "active" if connected else "pending",
        "allow_deeplink": allow_deeplink,
        "site_url": "https://store.example/",
        "description": "Offers from this store.",
        "image": "//cdn.admitad.com/store.png",
        "currency": "USD",
        "actions": [{"name": "Sale", "type": "sale", "payment_size": "5.00%"}],
        "action_countries": action_countries or ["BD"],
    }


class MockAdmitadClient:
    campaign_payload = None
    deeplink_payload = None
    requests = []

    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        type(self).requests = []
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, data, auth, headers):
        self.requests.append(
            {"method": "POST", "url": url, "data": data, "auth": auth, "headers": headers}
        )
        return httpx.Response(
            200,
            json={"access_token": "temporary-token", "token_type": "bearer", "expires_in": 3600},
            request=httpx.Request("POST", url),
        )

    async def get(self, url, params, headers):
        self.requests.append(
            {"method": "GET", "url": url, "params": params, "headers": headers}
        )
        if "/advcampaigns/website/" in url:
            payload = self.campaign_payload
        else:
            payload = self.deeplink_payload
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))


def mock_admitad(monkeypatch, campaigns, links=None):
    MockAdmitadClient.campaign_payload = {
        "results": campaigns,
        "_meta": {"count": len(campaigns), "limit": 100, "offset": 0},
    }
    MockAdmitadClient.deeplink_payload = links or [
        {"link": "https://ad.admitad.com/goto/abc123/", "is_affiliate_product": True}
    ]
    monkeypatch.setattr(httpx, "AsyncClient", MockAdmitadClient)


def test_admitad_catalog_returns_only_approved_country_eligible_programs(
    client, monkeypatch
):
    configure_admitad(monkeypatch)
    login(client)
    mock_admitad(
        monkeypatch,
        [
            campaign(),
            campaign(43, name="US store", action_countries=["US"]),
            campaign(44, name="Unjoined store", connected=False),
            campaign(45, name="Inactive store", status="pending"),
            campaign(46, name="No deeplink", allow_deeplink=False),
        ],
    )

    response = client.get(
        "/api/v1/offers/providers/admitad/catalog",
        headers={"x-vercel-ip-country": "BD"},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert [item["id"] for item in response.json()["campaigns"]] == [42]
    assert response.json()["campaigns"][0]["image_url"] == "https://cdn.admitad.com/store.png"
    assert CLIENT_SECRET not in response.text

    token_request, catalog_request = MockAdmitadClient.requests
    assert token_request["url"] == "https://api.admitad.com/token/"
    assert token_request["data"]["scope"] == (
        "advcampaigns_for_website deeplink_generator"
    )
    assert token_request["auth"] == (CLIENT_ID, CLIENT_SECRET)
    assert catalog_request["url"] == (
        "https://api.admitad.com/advcampaigns/website/12345/"
    )
    assert catalog_request["params"]["connection_status"] == "active"
    assert catalog_request["params"]["has_tool"] == "deeplink"
    assert catalog_request["headers"]["Authorization"] == "Bearer temporary-token"


def test_admitad_link_is_generated_only_for_eligible_campaign(client, monkeypatch):
    configure_admitad(monkeypatch)
    login(client)
    mock_admitad(monkeypatch, [campaign()])

    response = client.get(
        "/api/v1/offers/providers/admitad/campaigns/42/link",
        headers={"x-vercel-ip-country": "BD"},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["link_url"] == "https://ad.admitad.com/goto/abc123/"
    link_request = MockAdmitadClient.requests[-1]
    assert link_request["url"] == (
        "https://api.admitad.com/deeplink/12345/advcampaign/42/"
    )
    assert link_request["params"] == {
        "subid": "workbit-offers",
        "ulp": "https://store.example/",
    }


def test_admitad_link_rejects_unapproved_country_and_untrusted_url(client, monkeypatch):
    configure_admitad(monkeypatch)
    login(client)
    mock_admitad(monkeypatch, [campaign(action_countries=["US"])])

    unavailable = client.get(
        "/api/v1/offers/providers/admitad/campaigns/42/link",
        headers={"x-vercel-ip-country": "BD"},
    )
    assert unavailable.status_code == 404

    mock_admitad(
        monkeypatch,
        [campaign()],
        links=[{"link": "https://evil.example/goto/abc123/", "is_affiliate_product": True}],
    )
    unsafe_link = client.get(
        "/api/v1/offers/providers/admitad/campaigns/42/link",
        headers={"x-vercel-ip-country": "BD"},
    )
    assert unsafe_link.status_code == 502


def test_admitad_requires_server_credentials(client, monkeypatch):
    monkeypatch.setattr(settings, "admitad_enabled", True)
    monkeypatch.setattr(settings, "admitad_client_id", CLIENT_ID)
    monkeypatch.setattr(settings, "admitad_client_secret", None)
    monkeypatch.setattr(settings, "admitad_website_id", WEBSITE_ID)
    login(client)

    response = client.get("/api/v1/offers/providers/admitad/catalog")

    assert response.status_code == 503
    assert CLIENT_SECRET not in response.text
