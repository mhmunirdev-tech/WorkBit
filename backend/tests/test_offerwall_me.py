import hashlib
import hmac
import time
from decimal import Decimal
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
from sqlalchemy import event, select

from app.core.config import settings
from app.database.session import SessionLocal
from app.models import OfferConversion, User, Wallet
from conftest import activate_package, engine

PUBLIC_API_KEY = "offerwall-me-public-key"
SECRET_KEY = "test-offerwall-me-secret"
API_TOKEN = "test-offerwall-me-api-token"
SOURCE_IP = "95.216.65.163"


def configure_offerwall_me(monkeypatch):
    monkeypatch.setattr(settings, "offerwall_me_enabled", True)
    monkeypatch.setattr(settings, "offerwall_me_postback_enabled", True)
    monkeypatch.setattr(settings, "offerwall_me_public_api_key", PUBLIC_API_KEY)
    monkeypatch.setattr(settings, "offerwall_me_api_token", API_TOKEN)
    monkeypatch.setattr(settings, "offerwall_me_secret_key", SECRET_KEY)
    monkeypatch.setattr(settings, "offerwall_me_currency_name", "Points")
    monkeypatch.setattr(settings, "offerwall_me_exchange_rate", Decimal("1000"))


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


def get_wallet_balance():
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "workbit-user@example.com"))
        assert user is not None
        wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id))
        assert wallet is not None
        return Decimal(wallet.available_balance), Decimal(wallet.pending_balance)
    finally:
        db.close()


def callback_values(user_id, transaction_id="owm-tx-1", **overrides):
    values = {
        "subId": user_id,
        "transId": transaction_id,
        "offer_name": "Test task",
        "offer_type": "task",
        "reward": "1000.00000000",
        "reward_name": "Points",
        "reward_value": "1000",
        "payout": "1.00000000",
        "userIp": "203.0.113.10",
        "country": "BD",
        "status": "1",
    }
    values.update(overrides)
    values["signature"] = hashlib.md5(
        f"{values['subId']}{values['transId']}{values['reward']}{SECRET_KEY}".encode(),
        usedforsecurity=False,
    ).hexdigest()
    return values


def postback(client, values, source_ip=SOURCE_IP):
    return client.post(
        "/api/v1/postbacks/offerwall-me",
        data=values,
        headers={"x-forwarded-for": source_ip},
    )


def test_offerwall_me_wall_url_uses_server_signed_user_identity(client, monkeypatch):
    configure_offerwall_me(monkeypatch)
    login(client)

    response = client.get("/api/v1/offers/providers/offerwall-me/wall-url")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    url = urlsplit(response.json()["wall_url"])
    query = parse_qs(url.query)
    assert url.netloc == "offerwall.me"
    assert url.path == f"/offerwall/{PUBLIC_API_KEY}/{get_user_id()}"
    expires = int(query["identityExpires"][0])
    assert int(time.time()) < expires <= int(time.time()) + 3600
    message = (
        f"offerwall-user-v1\n{PUBLIC_API_KEY}\n{get_user_id()}\n"
        f"{query['identityExpires'][0]}"
    )
    expected = hmac.new(
        SECRET_KEY.encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    assert query["identitySignature"] == [expected]
    assert SECRET_KEY not in response.json()["wall_url"]


def test_offerwall_me_callback_credits_once_and_reverses_idempotently(
    client, monkeypatch
):
    configure_offerwall_me(monkeypatch)
    activate_package(client, "OFFERWALL-ME-CALLBACK")
    user_id = get_user_id()
    before = get_wallet_balance()

    first = postback(client, callback_values(user_id))
    duplicate = postback(client, callback_values(user_id))
    assert first.status_code == duplicate.status_code == 200
    assert first.text == "ok"
    assert get_wallet_balance()[0] - before[0] == Decimal("0.70000000")

    reversal = postback(
        client,
        callback_values(
            user_id,
            status="2",
            reward="-1000.00000000",
            payout="-1.00000000",
        ),
    )
    duplicate_reversal = postback(
        client,
        callback_values(
            user_id,
            status="2",
            reward="-1000.00000000",
            payout="-1.00000000",
        ),
    )
    assert reversal.status_code == duplicate_reversal.status_code == 200
    assert get_wallet_balance() == before

    db = SessionLocal()
    try:
        conversion = db.scalar(
            select(OfferConversion).where(
                OfferConversion.network_id == "offerwall-me",
                OfferConversion.external_transaction_id == "owm-tx-1",
            )
        )
        assert conversion is not None and conversion.status == "REVERSED"
    finally:
        db.close()


def test_offerwall_me_callback_rejects_bad_signature_source_and_payout(
    client, monkeypatch
):
    configure_offerwall_me(monkeypatch)
    user_id = get_user_id()

    invalid_signature = callback_values(user_id)
    invalid_signature["signature"] = "0" * 32
    assert postback(client, invalid_signature).status_code == 403

    assert (
        postback(client, callback_values(user_id), source_ip="182.48.93.43").status_code
        == 403
    )

    mismatched_payout = callback_values(user_id, payout="2")
    assert postback(client, mismatched_payout).status_code == 403
    mismatched_currency = callback_values(user_id, reward_name="USD")
    assert postback(client, mismatched_currency).status_code == 403


def test_offerwall_me_callback_rejects_duplicate_fields_and_disabled_callback(
    client, monkeypatch
):
    configure_offerwall_me(monkeypatch)
    user_id = get_user_id()
    values = callback_values(user_id)
    response = client.post(
        "/api/v1/postbacks/offerwall-me",
        content=urlencode([*values.items(), ("status", "2")]),
        headers={
            "content-type": "application/x-www-form-urlencoded",
            "x-forwarded-for": SOURCE_IP,
        },
    )
    assert response.status_code == 400

    monkeypatch.setattr(settings, "offerwall_me_postback_enabled", False)
    assert postback(client, values).status_code == 503


def test_offerwall_me_wall_url_is_unavailable_when_disabled(client, monkeypatch):
    configure_offerwall_me(monkeypatch)
    monkeypatch.setattr(settings, "offerwall_me_enabled", False)
    login(client)

    response = client.get("/api/v1/offers/providers/offerwall-me/wall-url")

    assert response.status_code == 404


class MockOfferwallMeClient:
    payload = None
    status_code = 200
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
            self.status_code,
            json=self.payload,
            request=httpx.Request("GET", url),
        )


def offer_payload(user_id):
    return {
        "status": 200,
        "data": [
            {
                "id": "offer-1",
                "provider": "Partner",
                "name": "Install and register",
                "description": "Complete the advertiser requirements.",
                "image": "https://cdn.example.com/offer.png",
                "reward": 1000,
                "payout": "1.000000",
                "devices": ["Android", "Mobile"],
                "countries": ["BD"],
                "is_multi_step": True,
                "url": f"https://offerwall.me/offerstart.php?id={user_id}&offer=offer-1",
            },
            {
                "id": "offer-us",
                "provider": "Partner",
                "name": "US only",
                "reward": 1000,
                "payout": "1",
                "countries": ["US"],
                "url": f"https://offerwall.me/offerstart.php?id={user_id}&offer=offer-us",
            },
            {
                "id": "offer-all",
                "provider": "Offerwall",
                "name": "Available everywhere",
                "reward": 500,
                "payout": "0.5",
                "countries": ["ALL"],
                "url": f"https://offerwall.me/offerstart.php?id={user_id}&offer=offer-all",
            },
        ],
    }


def test_offerwall_me_catalog_returns_filtered_offers_and_server_signed_api_request(
    client, monkeypatch
):
    configure_offerwall_me(monkeypatch)
    login(client)
    user_id = get_user_id()
    MockOfferwallMeClient.payload = offer_payload(user_id)
    MockOfferwallMeClient.status_code = 200
    monkeypatch.setattr(httpx, "AsyncClient", MockOfferwallMeClient)
    policy_query_count = 0

    def count_policy_queries(conn, cursor, statement, parameters, context, executemany):
        nonlocal policy_query_count
        if "reward_policies" in statement.lower():
            policy_query_count += 1

    event.listen(engine, "before_cursor_execute", count_policy_queries)
    try:
        response = client.get(
            "/api/v1/offers/providers/offerwall-me/catalog",
            headers={
                "x-forwarded-for": "8.8.8.8",
                "x-vercel-ip-country": "BD",
                "user-agent": "WorkBit test browser",
            },
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_policy_queries)

    assert response.status_code == 200
    assert policy_query_count == 1
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["total"] == 2
    assert {offer["id"] for offer in payload["offers"]} == {"offer-1", "offer-all"}
    offer = next(offer for offer in payload["offers"] if offer["id"] == "offer-1")
    assert offer["title"] == "Install and register"
    assert offer["provider_reward"] == "1000"
    assert offer["reward_name"] == "Points"
    assert Decimal(offer["provider_payout_usd"]) == Decimal("1")
    assert offer["estimated_user_reward_usd"] == "0.70000000"
    assert offer["countries"] == ["BD"]
    assert offer["click_url"].startswith("https://offerwall.me/offerstart.php?")

    url, params, headers = MockOfferwallMeClient.request_args
    assert url == "https://offerwall.me/offerapi.php"
    assert params["id"] == user_id
    assert params["ip"] == "8.8.8.8"
    assert params["country"] == "BD"
    assert params["api"] == PUBLIC_API_KEY
    assert params["token"] == API_TOKEN
    assert headers["User-Agent"] == "WorkBit test browser"
    message = (
        f"offerwall-user-v1\n{PUBLIC_API_KEY}\n{user_id}\n"
        f"{params['identityExpires']}"
    )
    expected_signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    assert params["identitySignature"] == expected_signature


def test_offerwall_me_catalog_accepts_rewards_rounded_to_configured_currency_precision(
    client, monkeypatch
):
    configure_offerwall_me(monkeypatch)
    login(client)
    user_id = get_user_id()
    payload = offer_payload(user_id)
    payload["data"][0]["reward"] = "123.46"
    payload["data"][0]["payout"] = "0.123456"
    MockOfferwallMeClient.payload = payload
    monkeypatch.setattr(httpx, "AsyncClient", MockOfferwallMeClient)

    response = client.get(
        "/api/v1/offers/providers/offerwall-me/catalog",
        headers={"x-forwarded-for": "8.8.8.8", "x-vercel-ip-country": "BD"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    offer = next(item for item in response.json()["offers"] if item["id"] == "offer-1")
    assert offer["provider_reward"] == "123.46"
    assert Decimal(offer["provider_payout_usd"]) == Decimal("0.12346")


def test_offerwall_me_catalog_estimates_from_signed_reward_not_gross_api_payout(
    client, monkeypatch
):
    configure_offerwall_me(monkeypatch)
    login(client)
    user_id = get_user_id()
    payload = offer_payload(user_id)
    payload["data"][0]["reward"] = "14843.81"
    payload["data"][0]["payout"] = "19.791740"
    MockOfferwallMeClient.payload = payload
    monkeypatch.setattr(httpx, "AsyncClient", MockOfferwallMeClient)

    response = client.get(
        "/api/v1/offers/providers/offerwall-me/catalog",
        headers={"x-forwarded-for": "8.8.8.8", "x-vercel-ip-country": "BD"},
    )

    assert response.status_code == 200
    offer = next(item for item in response.json()["offers"] if item["id"] == "offer-1")
    assert Decimal(offer["provider_payout_usd"]) == Decimal("14.84381")
    assert offer["estimated_user_reward_usd"] == "10.39066700"


def test_offerwall_me_catalog_handles_empty_data_and_rejects_unsafe_urls(
    client, monkeypatch
):
    configure_offerwall_me(monkeypatch)
    login(client)
    user_id = get_user_id()
    monkeypatch.setattr(httpx, "AsyncClient", MockOfferwallMeClient)

    MockOfferwallMeClient.payload = {"status": 404, "message": "No data found"}
    empty = client.get(
        "/api/v1/offers/providers/offerwall-me/catalog",
        headers={"x-forwarded-for": "8.8.8.8", "x-vercel-ip-country": "BD"},
    )
    assert empty.status_code == 200
    assert empty.json() == {"offers": [], "total": 0}

    unsafe_payload = offer_payload(user_id)
    unsafe_payload["data"][0]["url"] = "https://evil.example/offer?id=" + user_id
    MockOfferwallMeClient.payload = unsafe_payload
    unsafe = client.get(
        "/api/v1/offers/providers/offerwall-me/catalog",
        headers={"x-forwarded-for": "8.8.8.8", "x-vercel-ip-country": "BD"},
    )
    assert unsafe.status_code == 502
    assert unsafe.json()["error"] == {
        "code": "UPSTREAM_ERROR",
        "message": "Offerwall.me returned an unsafe offer link.",
    }


def test_offerwall_me_catalog_requires_user_ip_and_api_token(client, monkeypatch):
    configure_offerwall_me(monkeypatch)
    login(client)

    no_ip = client.get(
        "/api/v1/offers/providers/offerwall-me/catalog",
        headers={"x-vercel-ip-country": "BD"},
    )
    assert no_ip.status_code == 503

    monkeypatch.setattr(settings, "offerwall_me_api_token", None)
    missing_token = client.get(
        "/api/v1/offers/providers/offerwall-me/catalog",
        headers={"x-forwarded-for": "8.8.8.8", "x-vercel-ip-country": "BD"},
    )
    assert missing_token.status_code == 503
