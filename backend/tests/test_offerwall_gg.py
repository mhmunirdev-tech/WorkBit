import hashlib
import hmac
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

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
