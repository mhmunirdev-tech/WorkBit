from decimal import Decimal

import httpx

from app.core.config import settings
from app.database.session import SessionLocal
from app.models import User
from sqlalchemy import select
from conftest import configure_payout_rate

APP_ID = "test-moonetix-app"
API_KEY = "test-moonetix-api-key"


def configure_moonetix(monkeypatch):
    monkeypatch.setattr(settings, "moonetix_enabled", True)
    monkeypatch.setattr(settings, "moonetix_app_id", APP_ID)
    monkeypatch.setattr(settings, "moonetix_api_key", API_KEY)
    monkeypatch.setattr(settings, "moonetix_currency_name", "WBC")
    monkeypatch.setattr(settings, "moonetix_exchange_rate", Decimal("1000"))


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"},
    )
    assert response.status_code == 200


def get_user_id():
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "workbit-user@example.com"))
        assert user is not None
        return user.id
    finally:
        db.close()


def moonetix_payload(user_id):
    return {
        "ok": True,
        "currency": "WBC",
        "history_url": f"https://wall.moonetix.com/{APP_ID}?user_id={user_id}&hash=abc#status",
        "offers": [
            {
                "id": 58,
                "title": "Nova Quest: reach level 10",
                "category": "game",
                "description": "Install the app and reach level 10.",
                "goals": [
                    {"name": "Create an account", "reward": 325, "payout_usd": 0.5},
                    {"name": "Reach level 10", "reward": 650, "payout_usd": 1},
                ],
                "reward": 975,
                "reward_before_bonus": None,
                "payout_usd": 1.5,
                "payout_type": "fixed",
                "reward_max": None,
                "payout_max_usd": None,
                "thumbnail_url": "https://moonetix.com/uploads/campaigns/thumb.webp",
                "start_url": f"https://wall.moonetix.com/{APP_ID}/offer/58?user_id={user_id}&hash=abc",
            }
        ],
    }


class MockMoonetixClient:
    payload = None
    request_args = None

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, params, headers):
        type(self).request_args = (url, params, headers)
        return httpx.Response(
            200,
            json=self.payload,
            request=httpx.Request("GET", url),
        )


def test_moonetix_catalog_returns_workbit_reward_estimates_and_signed_start_urls(
    client, monkeypatch
):
    configure_moonetix(monkeypatch)
    configure_payout_rate(client)
    login(client)
    user_id = get_user_id()
    MockMoonetixClient.payload = moonetix_payload(user_id)
    monkeypatch.setattr(httpx, "AsyncClient", MockMoonetixClient)

    response = client.get(
        "/api/v1/offers/providers/moonetix/catalog",
        headers={
            "x-vercel-ip-country": "BD",
            "user-agent": "WorkBit test browser",
        },
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["total"] == 1
    assert payload["currency"] == "WBC"
    offer = payload["offers"][0]
    assert offer["title"] == "Nova Quest: reach level 10"
    assert offer["reward_name"] == "WBC"
    assert offer["goals"][1]["name"] == "Reach level 10"
    assert Decimal(offer["payout_usd"]) == Decimal("1.5")
    assert Decimal(offer["estimated_user_reward_usd"]) == Decimal("1.05000000")
    assert offer["start_url"].startswith(f"https://wall.moonetix.com/{APP_ID}/offer/58?")

    url, params, headers = MockMoonetixClient.request_args
    assert url == "https://api.moonetix.com/v1/offers"
    assert params == {
        "user_id": user_id,
        "country": "BD",
        "ua": "WorkBit test browser",
    }
    assert headers["Authorization"] == f"Bearer {API_KEY}"


def test_moonetix_catalog_rejects_foreign_or_untracked_start_urls(client, monkeypatch):
    configure_moonetix(monkeypatch)
    login(client)
    user_id = get_user_id()
    payload = moonetix_payload(user_id)
    payload["offers"][0]["start_url"] = "https://attacker.example/offer"
    MockMoonetixClient.payload = payload
    monkeypatch.setattr(httpx, "AsyncClient", MockMoonetixClient)

    response = client.get(
        "/api/v1/offers/providers/moonetix/catalog",
        headers={"x-vercel-ip-country": "BD"},
    )

    assert response.status_code == 502


def test_moonetix_catalog_requires_matching_currency(client, monkeypatch):
    configure_moonetix(monkeypatch)
    login(client)
    user_id = get_user_id()
    payload = moonetix_payload(user_id)
    payload["currency"] = "Coins"
    MockMoonetixClient.payload = payload
    monkeypatch.setattr(httpx, "AsyncClient", MockMoonetixClient)

    response = client.get(
        "/api/v1/offers/providers/moonetix/catalog",
        headers={"x-vercel-ip-country": "BD"},
    )

    assert response.status_code == 503
