import hashlib
import hmac
from decimal import Decimal
from urllib.parse import urlencode
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.database.session import SessionLocal
from app.models import OfferConversion, User, Wallet
from conftest import activate_package

API_KEY = "bitcotasks-public-api-key"
SECRET_KEY = "test-bitcotasks-secret"
SOURCE_IP = "45.14.135.48"


def configure_bitcotasks(monkeypatch):
    monkeypatch.setattr(settings, "bitcotasks_enabled", True)
    monkeypatch.setattr(settings, "bitcotasks_postback_enabled", True)
    monkeypatch.setattr(settings, "bitcotasks_api_key", API_KEY)
    monkeypatch.setattr(settings, "bitcotasks_secret_key", SECRET_KEY)
    monkeypatch.setattr(settings, "bitcotasks_currency_name", "Points")
    monkeypatch.setattr(settings, "bitcotasks_exchange_rate", Decimal("1000"))


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


def callback_values(user_id, transaction_id="bt-tx-1", **overrides):
    values = {
        "subId": UUID(user_id).hex,
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
        "debug": "0",
    }
    values.update(overrides)
    values["signature"] = hashlib.md5(
        f"{values['subId']}{values['transId']}{values['reward']}{SECRET_KEY}".encode(),
        usedforsecurity=False,
    ).hexdigest()
    return values


def postback(client, values, source_ip=SOURCE_IP):
    return client.post(
        "/api/v1/postbacks/bitcotasks",
        data=values,
        headers={"x-forwarded-for": source_ip},
    )


def test_bitcotasks_sdk_config_is_authenticated_and_uses_32_char_sub_id(
    client, monkeypatch
):
    configure_bitcotasks(monkeypatch)
    assert client.get("/api/v1/offers/providers/bitcotasks/sdk-config").status_code == 401
    login(client)

    response = client.get("/api/v1/offers/providers/bitcotasks/sdk-config")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    sub_id = UUID(get_user_id()).hex
    assert response.json() == {
        "api_key": API_KEY,
        "sub_id": sub_id,
        "sig": hmac.new(
            SECRET_KEY.encode(),
            sub_id.encode(),
            hashlib.sha256,
        ).hexdigest(),
    }
    assert SECRET_KEY not in response.text


def test_bitcotasks_callback_credits_once_and_reverses_idempotently(
    client, monkeypatch
):
    configure_bitcotasks(monkeypatch)
    activate_package(client, "BITCOTASKS-CALLBACK")
    user_id = get_user_id()
    before = get_wallet_balance()

    first = postback(client, callback_values(user_id))
    duplicate = postback(client, callback_values(user_id))
    assert first.status_code == duplicate.status_code == 200
    assert first.text == "ok"
    assert get_wallet_balance()[0] - before[0] == Decimal("0.70000000")

    reversal = postback(
        client,
        callback_values(user_id, status="2"),
    )
    duplicate_reversal = postback(
        client,
        callback_values(user_id, status="2"),
    )
    assert reversal.status_code == duplicate_reversal.status_code == 200
    assert get_wallet_balance() == before

    db = SessionLocal()
    try:
        conversion = db.scalar(
            select(OfferConversion).where(
                OfferConversion.network_id == "bitcotasks",
                OfferConversion.external_transaction_id == "bt-tx-1",
            )
        )
        assert conversion is not None
        assert conversion.status == "REVERSED"
    finally:
        db.close()


def test_bitcotasks_rejects_bad_signature_source_and_currency(client, monkeypatch):
    configure_bitcotasks(monkeypatch)
    user_id = get_user_id()

    invalid_signature = callback_values(user_id)
    invalid_signature["signature"] = "0" * 32
    assert postback(client, invalid_signature).status_code == 403
    assert postback(
        client, callback_values(user_id), source_ip="203.0.113.10"
    ).status_code == 403
    assert postback(
        client, callback_values(user_id, reward_name="USD")
    ).status_code == 403
    assert postback(
        client, callback_values(user_id, reward_value="10")
    ).status_code == 403


def test_bitcotasks_debug_callback_is_not_credited(client, monkeypatch):
    configure_bitcotasks(monkeypatch)
    before = get_wallet_balance()
    values = callback_values(
        get_user_id(),
        debug="1",
    )
    values["subId"] = "debug-user"
    values["transId"] = "debug-tx"
    values["signature"] = hashlib.md5(
        f"debug-userdebug-tx{values['reward']}{SECRET_KEY}".encode(),
        usedforsecurity=False,
    ).hexdigest()

    response = postback(client, values)

    assert response.status_code == 200
    assert response.text == "ok"
    assert get_wallet_balance() == before


def test_bitcotasks_rejects_duplicate_form_fields(client, monkeypatch):
    configure_bitcotasks(monkeypatch)
    user_id = get_user_id()
    values = callback_values(user_id)
    response = client.post(
        "/api/v1/postbacks/bitcotasks",
        content=urlencode([*values.items(), ("status", "2")]),
        headers={
            "content-type": "application/x-www-form-urlencoded",
            "x-forwarded-for": SOURCE_IP,
        },
    )

    assert response.status_code == 400


def test_bitcotasks_sdk_config_is_unavailable_when_disabled(client, monkeypatch):
    configure_bitcotasks(monkeypatch)
    monkeypatch.setattr(settings, "bitcotasks_enabled", False)
    login(client)

    response = client.get("/api/v1/offers/providers/bitcotasks/sdk-config")

    assert response.status_code == 404
