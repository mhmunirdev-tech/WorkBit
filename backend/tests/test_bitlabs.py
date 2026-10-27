import hashlib
import hmac
from decimal import Decimal
from urllib.parse import parse_qs, urlencode, urlsplit

from sqlalchemy import select

from app.core.config import settings
from app.database.session import SessionLocal
from app.models import OfferConversion, User, Wallet
from conftest import activate_package

CALLBACK_URL = "https://api.workbitbd.com/api/v1/postbacks/bitlabs"
APP_TOKEN = "test-bitlabs-app-token"
APP_SECRET = "test-bitlabs-app-secret"


def configure_bitlabs(monkeypatch):
    monkeypatch.setattr(settings, "bitlabs_enabled", True)
    monkeypatch.setattr(settings, "bitlabs_api_key", APP_TOKEN)
    monkeypatch.setattr(settings, "bitlabs_postback_secret", APP_SECRET)
    monkeypatch.setattr(settings, "bitlabs_callback_url", CALLBACK_URL)


def login_user(client):
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


def bitlabs_callback_url(**overrides):
    values = {
        "uid": get_user_id(),
        "tx": "bitlabs-completion-1",
        "usd": "1.25",
        "ref": "",
        "activity_type": "COMPLETE",
        "offer_id": "offer-23",
        "task_id": "task-4",
        "offer_state": "COMPLETED",
    }
    values.update(overrides)
    raw_query = urlencode(values)
    signed_url = f"{CALLBACK_URL}?{raw_query}"
    signature = hmac.new(
        APP_SECRET.encode("utf-8"),
        signed_url.encode("ascii"),
        hashlib.sha1,
    ).hexdigest()
    return f"/api/v1/postbacks/bitlabs?{raw_query}&hash={signature}"


def test_bitlabs_wall_url_requires_active_package_and_uses_account_user_id(client, monkeypatch):
    configure_bitlabs(monkeypatch)
    login_user(client)

    assert client.get("/api/v1/offers/providers/bitlabs/wall-url").status_code == 402
    activate_package(client, "BITLABSWALL001")
    response = client.get("/api/v1/offers/providers/bitlabs/wall-url")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    query = parse_qs(urlsplit(response.json()["wall_url"]).query)
    assert query == {"uid": [get_user_id()], "token": [APP_TOKEN]}


def test_bitlabs_completed_callback_credits_once_and_reconciliation_reverses(client, monkeypatch):
    configure_bitlabs(monkeypatch)
    activate_package(client, "BITLABSCALLBACK001")
    initial_balance = get_wallet_balance()

    completion = bitlabs_callback_url()
    first_response = client.get(completion)
    assert first_response.status_code == 200
    credited_balance = get_wallet_balance()
    assert credited_balance[0] > initial_balance[0]

    assert client.get(completion).status_code == 200
    assert get_wallet_balance() == credited_balance

    partial_reconciliation = bitlabs_callback_url(
        tx="bitlabs-partial-reconciliation-1",
        usd="0.5",
        ref="bitlabs-completion-1",
        activity_type="RECONCILIATION",
        offer_state="RECONCILED",
    )
    assert client.get(partial_reconciliation).status_code == 503
    assert get_wallet_balance() == credited_balance

    reconciliation = bitlabs_callback_url(
        tx="bitlabs-reconciliation-1",
        usd="0",
        ref="bitlabs-completion-1",
        activity_type="RECONCILIATION",
        offer_state="RECONCILED",
    )
    assert client.get(reconciliation).status_code == 200
    assert get_wallet_balance() == initial_balance

    db = SessionLocal()
    try:
        conversion = db.scalar(
            select(OfferConversion).where(
                OfferConversion.network_id == "bitlabs",
                OfferConversion.external_transaction_id == "bitlabs-completion-1",
            )
        )
        assert conversion is not None
        assert conversion.status == "REVERSED"
    finally:
        db.close()


def test_bitlabs_callback_debug_mode_is_acknowledged_without_credit(client, monkeypatch):
    configure_bitlabs(monkeypatch)
    activate_package(client, "BITLABSDEBUG001")
    initial_balance = get_wallet_balance()

    debug_callback = bitlabs_callback_url(
        tx="bitlabs-debug-1",
        debug="true",
    )
    assert client.get(debug_callback).status_code == 200
    assert get_wallet_balance() == initial_balance

    db = SessionLocal()
    try:
        assert db.scalar(
            select(OfferConversion).where(
                OfferConversion.network_id == "bitlabs",
                OfferConversion.external_transaction_id == "bitlabs-debug-1",
            )
        ) is None
    finally:
        db.close()


def test_bitlabs_callback_rejects_bad_hash(client, monkeypatch):
    configure_bitlabs(monkeypatch)
    callback = bitlabs_callback_url().rsplit("=", 1)[0] + "=" + "0" * 40

    response = client.get(callback)

    assert response.status_code == 403
