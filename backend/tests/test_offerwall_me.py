import hashlib
import hmac
import time
from decimal import Decimal
from urllib.parse import parse_qs, urlencode, urlsplit

from sqlalchemy import select

from app.core.config import settings
from app.database.session import SessionLocal
from app.models import OfferConversion, User, Wallet
from conftest import activate_package

PUBLIC_API_KEY = "offerwall-me-public-key"
SECRET_KEY = "test-offerwall-me-secret"
SOURCE_IP = "95.216.65.163"


def configure_offerwall_me(monkeypatch):
    monkeypatch.setattr(settings, "offerwall_me_enabled", True)
    monkeypatch.setattr(settings, "offerwall_me_postback_enabled", True)
    monkeypatch.setattr(settings, "offerwall_me_public_api_key", PUBLIC_API_KEY)
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
