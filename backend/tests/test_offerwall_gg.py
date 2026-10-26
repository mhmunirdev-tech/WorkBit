import hashlib
import hmac
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.database.session import SessionLocal
from app.models import OfferConversion, User, Wallet
from conftest import activate_package

PUBLIC_KEY = "p" * 32
SECRET_KEY = "test-offerwall-secret"


def configure_offerwall(monkeypatch):
    monkeypatch.setattr(settings, "offerwall_gg_enabled", True)
    monkeypatch.setattr(settings, "offerwall_gg_public_key", PUBLIC_KEY)
    monkeypatch.setattr(settings, "offerwall_gg_secret_key", SECRET_KEY)
    monkeypatch.setattr(settings, "offerwall_gg_currency_name", "USD")


def get_user_id():
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "workbit-user@example.com"))
        assert user is not None
        return user.id
    finally:
        db.close()


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"},
    )
    assert response.status_code == 200


def callback_values(user_id, transaction_id="og-tx-1", amount="1.0000", **overrides):
    values = {
        "userId": user_id,
        "transactionId": transaction_id,
        "offerId": "offer-42",
        "offerName": "Test offer",
        "goalId": "",
        "currencyAmount": amount,
        "currencyName": "USD",
        "status": "reversed" if amount.startswith("-") else "credited",
        "test": "0",
        "timestamp": "1793030000",
    }
    values.update(overrides)
    values["signature"] = hmac.new(
        SECRET_KEY.encode(),
        f"{values['userId']}:{values['transactionId']}:{values['currencyAmount']}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return values


def get_wallet():
    db = SessionLocal()
    try:
        wallet = db.scalar(
            select(Wallet).where(
                Wallet.user_id
                == db.scalar(select(User.id).where(User.email == "workbit-user@example.com"))
            )
        )
        assert wallet is not None
        return Decimal(wallet.available_balance), Decimal(wallet.pending_balance)
    finally:
        db.close()


def test_offerwall_wall_url_requires_authentication_and_active_package(client, monkeypatch):
    configure_offerwall(monkeypatch)

    assert client.get("/api/v1/offers/providers/offerwall-gg/wall-url").status_code == 401
    login(client)
    assert client.get("/api/v1/offers/providers/offerwall-gg/wall-url").status_code == 402

    activate_package(client, "TEST-OFFERWALL-WALL-URL")
    response = client.get("/api/v1/offers/providers/offerwall-gg/wall-url")

    assert response.status_code == 200
    parsed = urlparse(response.json()["wall_url"])
    query = parse_qs(parsed.query)
    assert parsed.netloc == "offerwall.gg"
    assert parsed.path == f"/wall/{PUBLIC_KEY}"
    assert query["userId"] == [get_user_id()]
    canonical = f"appId={PUBLIC_KEY}&userId={get_user_id()}"
    expected = hmac.new(SECRET_KEY.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    assert query["signature"] == [expected]
    assert response.headers["cache-control"] == "no-store"


def test_offerwall_callback_verifies_signature_and_never_credits_test_events(client, monkeypatch):
    configure_offerwall(monkeypatch)
    user_id = get_user_id()
    invalid = callback_values(user_id)
    invalid["currencyAmount"] = "9.0000"
    assert client.get("/api/v1/postbacks/offerwall-gg", params=invalid).status_code == 403

    invalid_user = callback_values("not-a-uuid")
    assert client.get("/api/v1/postbacks/offerwall-gg", params=invalid_user).status_code == 403

    test_event = callback_values("offerwall-test-user", test="1")
    before = get_wallet()
    response = client.post("/api/v1/postbacks/offerwall-gg", data=test_event)

    assert response.status_code == 200
    assert response.text == "OK"
    assert get_wallet() == before


def test_offerwall_callback_is_idempotent_and_reverses_the_same_conversion(client, monkeypatch):
    configure_offerwall(monkeypatch)
    activate_package(client, "TEST-OFFERWALL-CALLBACK")
    user_id = get_user_id()
    values = callback_values(user_id)

    credited = client.get("/api/v1/postbacks/offerwall-gg", params=values)
    repeated_credit = client.get("/api/v1/postbacks/offerwall-gg", params=values)
    assert credited.status_code == repeated_credit.status_code == 200
    assert get_wallet()[0] == Decimal("0.80000000")

    reversal = callback_values(
        user_id,
        amount="-1.0000",
        status="reversed",
    )
    reversed_response = client.get("/api/v1/postbacks/offerwall-gg", params=reversal)
    repeated_reversal = client.get("/api/v1/postbacks/offerwall-gg", params=reversal)

    assert reversed_response.status_code == repeated_reversal.status_code == 200
    assert get_wallet()[0] == Decimal("0E-8")
    db = SessionLocal()
    try:
        conversion = db.scalar(
            select(OfferConversion).where(
                OfferConversion.network_id == "offerwall-gg",
                OfferConversion.external_transaction_id == "og-tx-1",
            )
        )
        assert conversion is not None and conversion.status == "REVERSED"
    finally:
        db.close()


def test_offerwall_reversal_creates_debt_when_the_reward_was_already_withdrawn(client, monkeypatch):
    configure_offerwall(monkeypatch)
    activate_package(client, "TEST-OFFERWALL-DEBT")
    user_id = get_user_id()
    assert client.get(
        "/api/v1/postbacks/offerwall-gg",
        params=callback_values(user_id),
    ).status_code == 200

    db = SessionLocal()
    try:
        wallet = db.scalar(select(Wallet).where(Wallet.user_id == user_id))
        assert wallet is not None
        wallet.available_balance = Decimal("0")
        db.commit()
    finally:
        db.close()

    reversal = client.get(
        "/api/v1/postbacks/offerwall-gg",
        params=callback_values(user_id, amount="-1.0000", status="reversed"),
    )

    assert reversal.status_code == 200
    dashboard = client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    assert Decimal(dashboard.json()["available_balance"]) == Decimal("-0.80000000")
    assert Decimal(dashboard.json()["reversal_debt"]) == Decimal("0.80000000")
    assert dashboard.json()["withdrawal_summary"]["enabled"] is False


def test_offerwall_callback_rejects_unknown_reversal_and_currency_override(client, monkeypatch):
    configure_offerwall(monkeypatch)
    user_id = get_user_id()
    unknown_reversal = callback_values(
        user_id,
        transaction_id="unknown-tx",
        amount="-1.0000",
        status="reversed",
    )
    assert client.get("/api/v1/postbacks/offerwall-gg", params=unknown_reversal).status_code == 409

    wrong_currency = callback_values(
        user_id,
        transaction_id="wrong-currency",
        currencyName="BDT",
    )
    assert client.get("/api/v1/postbacks/offerwall-gg", params=wrong_currency).status_code == 403


def offerwall_catalog_payload(user_id, click_url=None, offers=None, pages=1):
    return {
        "success": True,
        "data": {
            "offers": offers
            if offers is not None
            else [
                {
                    "id": 4021,
                    "externalId": "network-offer-4021",
                    "provider": "lootably",
                    "name": "World of Sea Battle",
                    "description": "Build a ship and win your first sea battle.",
                    "requirements": "Reach level 10 within 7 days.",
                    "image": "https://cdn.example/offers/4021.png",
                    "categories": ["games"],
                    "devices": ["desktop"],
                    "reward": "1.25",
                    "rewardIsVariable": False,
                    "rewardUpTo": False,
                    "paymentModel": "cpa",
                    "featured": True,
                    "clickUrl": click_url
                    or f"https://offerwall.gg/wall/{PUBLIC_KEY}/click/4021?userId={user_id}",
                }
            ],
            "pagination": {"page": 1, "pages": pages, "total": 1, "perPage": 50},
            "currency": {"name": "USD", "perUsd": 1},
            "targeting": {"country": "US", "device": "desktop"},
        },
    }


class MockOfferwallResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class MockOfferwallClient:
    def __init__(self, payload, request_error=None):
        self.payload = payload
        self.request_error = request_error
        self.request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, url, params, headers):
        self.request = {"url": url, "params": params, "headers": headers}
        if self.request_error:
            raise self.request_error
        return MockOfferwallResponse(self.payload)


def mock_offerwall_catalog(monkeypatch, mock_client):
    monkeypatch.setattr(
        "app.services.offerwall_gg_catalog.httpx.AsyncClient",
        lambda **_kwargs: mock_client,
    )


def test_offerwall_catalog_requires_authentication_and_active_package(client, monkeypatch):
    configure_offerwall(monkeypatch)

    assert client.get("/api/v1/offers/providers/offerwall-gg/catalog").status_code == 401
    login(client)
    assert client.get("/api/v1/offers/providers/offerwall-gg/catalog").status_code == 402


def test_offerwall_catalog_returns_safe_tracked_offers_and_uses_server_credentials(
    client, monkeypatch
):
    configure_offerwall(monkeypatch)
    login(client)
    activate_package(client, "TEST-OFFERWALL-CATALOG")
    user_id = get_user_id()
    mock_client = MockOfferwallClient(offerwall_catalog_payload(user_id))
    mock_offerwall_catalog(monkeypatch, mock_client)

    response = client.get("/api/v1/offers/providers/offerwall-gg/catalog?page=1&limit=50")

    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 1
    assert result["offers"][0]["title"] == "World of Sea Battle"
    assert Decimal(result["offers"][0]["user_reward_usd"]) == Decimal("1.00")
    assert result["offers"][0]["click_url"].endswith(f"?userId={user_id}")
    assert SECRET_KEY not in response.text
    assert mock_client.request["url"] == "https://offerwall.gg/api/v1/offers"
    assert mock_client.request["headers"] == {"X-Api-Key": SECRET_KEY}
    assert mock_client.request["params"]["userId"] == user_id
    assert mock_client.request["params"]["country"]
    assert response.headers["cache-control"] == "no-store"


def test_offerwall_catalog_accepts_empty_inventory(client, monkeypatch):
    configure_offerwall(monkeypatch)
    login(client)
    activate_package(client, "TEST-OFFERWALL-CATALOG-EMPTY")
    mock_offerwall_catalog(
        monkeypatch,
        MockOfferwallClient(offerwall_catalog_payload(get_user_id(), offers=[], pages=0)),
    )

    response = client.get("/api/v1/offers/providers/offerwall-gg/catalog")

    assert response.status_code == 200
    assert response.json()["offers"] == []
    assert response.json()["pages"] == 0


def test_offerwall_catalog_rejects_untrusted_click_url_and_surfaces_upstream_failure(
    client, monkeypatch
):
    configure_offerwall(monkeypatch)
    login(client)
    activate_package(client, "TEST-OFFERWALL-CATALOG-INVALID")
    user_id = get_user_id()
    mock_offerwall_catalog(
        monkeypatch,
        MockOfferwallClient(
            offerwall_catalog_payload(
                user_id,
                click_url=f"https://advertiser.example/click?userId={user_id}",
            )
        ),
    )
    invalid_link = client.get("/api/v1/offers/providers/offerwall-gg/catalog")
    assert invalid_link.status_code == 502

    mock_offerwall_catalog(
        monkeypatch,
        MockOfferwallClient(
            payload=None,
            request_error=httpx.ConnectError("provider unavailable"),
        ),
    )
    unavailable = client.get("/api/v1/offers/providers/offerwall-gg/catalog")
    assert unavailable.status_code == 503
    assert SECRET_KEY not in unavailable.text
