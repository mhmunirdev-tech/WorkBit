from decimal import Decimal

import httpx

from app.core.config import settings

API_KEY = "test-timewall-api-key"


def configure_timewall(monkeypatch):
    monkeypatch.setattr(settings, "timewall_enabled", True)
    monkeypatch.setattr(settings, "timewall_api_key", API_KEY)


class MockTimeWallResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://api.timewall.io/get-surveys")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("upstream error", request=request, response=response)

    def json(self):
        return self.payload


class MockTimeWallClient:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.request_url = ""
        self.request_kwargs = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, **kwargs):
        self.request_url = url
        self.request_kwargs = kwargs
        return MockTimeWallResponse(self.payload, self.status_code)


def mock_timewall_surveys(monkeypatch, mock_client):
    monkeypatch.setattr(
        "app.services.timewall_surveys.httpx.AsyncClient",
        lambda **_kwargs: mock_client,
    )


def login_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_timewall_surveys_api_uses_server_key_and_verified_user_context(
    client, monkeypatch
):
    configure_timewall(monkeypatch)
    assert client.get("/api/v1/offers/providers/timewall/surveys").status_code == 401
    user_id = login_user(client)

    mock_client = MockTimeWallClient(
        {
            "success": True,
            "prescreener_required": False,
            "currency": "WBC",
            "surveys": [
                {
                    "id": "survey-123",
                    "loi": 12,
                    "usd_rate": "1.40",
                    "currency_amount": "235.20",
                    "link": "https://timesurveys.com/s/survey-123",
                }
            ],
        }
    )
    mock_timewall_surveys(monkeypatch, mock_client)

    response = client.get(
        "/api/v1/offers/providers/timewall/surveys",
        headers={
            "X-Forwarded-For": "8.8.8.8",
            "User-Agent": "WorkBit test browser",
        },
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["total"] == 1
    assert body["currency"] == "WBC"
    survey = body["surveys"][0]
    assert survey["id"] == "survey-123"
    assert survey["estimated_time_minutes"] == 12
    assert Decimal(survey["estimated_user_reward_usd"]) == Decimal("0.98000000")
    assert survey["entry_url"] == "https://timesurveys.com/s/survey-123"

    assert mock_client.request_url == "https://api.timewall.io/get-surveys"
    assert mock_client.request_kwargs["headers"] == {"Authorization": f"Bearer {API_KEY}"}
    assert mock_client.request_kwargs["json"] == {
        "uid": user_id,
        "ip": "8.8.8.8",
        "user_agent": "WorkBit test browser",
        "limit": 10,
        "provider": "all",
    }


def test_timewall_surveys_require_verified_client_ip(client, monkeypatch):
    configure_timewall(monkeypatch)
    login_user(client)
    mock_client = MockTimeWallClient({"success": True, "currency": "WBC", "surveys": []})
    mock_timewall_surveys(monkeypatch, mock_client)

    response = client.get(
        "/api/v1/offers/providers/timewall/surveys",
        headers={"User-Agent": "WorkBit test browser"},
    )

    assert response.status_code == 503
    assert "verified user IP" in response.json()["error"]["message"]
    assert mock_client.request_url == ""


def test_timewall_surveys_reject_unsafe_provider_links(client, monkeypatch):
    configure_timewall(monkeypatch)
    login_user(client)
    mock_timewall_surveys(
        monkeypatch,
        MockTimeWallClient(
            {
                "success": True,
                "currency": "WBC",
                "surveys": [
                    {
                        "id": "survey-123",
                        "loi": 12,
                        "usd_rate": "1.40",
                        "currency_amount": "235.20",
                        "link": "https://example.com/s/survey-123",
                    }
                ],
            }
        ),
    )

    response = client.get(
        "/api/v1/offers/providers/timewall/surveys",
        headers={
            "X-Forwarded-For": "8.8.8.8",
            "User-Agent": "WorkBit test browser",
        },
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "REQUEST_ERROR"


def test_timewall_surveys_are_hidden_until_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "timewall_enabled", False)
    login_user(client)

    response = client.get("/api/v1/offers/providers/timewall/surveys")

    assert response.status_code == 404
