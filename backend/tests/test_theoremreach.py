import base64
import hashlib
import hmac
from decimal import Decimal
from urllib.parse import parse_qs, urlencode, urlsplit

from sqlalchemy import select

from app.core.config import settings
from app.database.session import SessionLocal
from app.models import OfferConversion, User, Wallet
from conftest import activate_package

CALLBACK_URL = "https://api.workbitbd.com/api/v1/postbacks/theoremreach"
API_KEY = "test-theoremreach-api-key"
SECRET_KEY = "test-theoremreach-secret"
PARTNER_ID = "test-theoremreach-placement"


def configure_theoremreach(monkeypatch):
    monkeypatch.setattr(settings, "theoremreach_enabled", True)
    monkeypatch.setattr(settings, "theoremreach_api_key", API_KEY)
    monkeypatch.setattr(settings, "theoremreach_secret_key", SECRET_KEY)
    monkeypatch.setattr(settings, "theoremreach_partner_id", PARTNER_ID)
    monkeypatch.setattr(settings, "theoremreach_callback_url", CALLBACK_URL)
    monkeypatch.setattr(settings, "theoremreach_currency_name_singular", "Credit")
    monkeypatch.setattr(settings, "theoremreach_currency_name_plural", "Credits")
    monkeypatch.setattr(settings, "theoremreach_exchange_rate", Decimal("10"))
    monkeypatch.setattr(settings, "theoremreach_decimals_to_display", 2)


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
        user = db.scalar(select(User).where(User.email == "workbit-user@example.com"))
        assert user is not None
        wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id))
        assert wallet is not None
        return Decimal(wallet.available_balance), Decimal(wallet.pending_balance)
    finally:
        db.close()


def callback_url(**overrides):
    values = {
        "user_id": get_user_id(),
        "tx_id": "theoremreach-reward-1",
        "currency": "1.25",
        "reward": "12.5",
        "partner_id": PARTNER_ID,
        "external_transaction_id": "theoremreach-session-1",
    }
    values.update(overrides)
    query = urlencode(values)
    signing_url = f"{CALLBACK_URL}?{query}"
    digest = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_url.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    signature = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"/api/v1/postbacks/theoremreach?{query}&hash={signature}"


def test_theoremreach_wall_url_requires_auth_and_active_package(client, monkeypatch):
    configure_theoremreach(monkeypatch)
    assert client.get("/api/v1/offers/providers/theoremreach/wall-url").status_code == 401
    login_user(client)
    assert client.get("/api/v1/offers/providers/theoremreach/wall-url").status_code == 402

    activate_package(client, "THEOREMREACH-WALL-001")
    response = client.get("/api/v1/offers/providers/theoremreach/wall-url")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    wall_url = response.json()["wall_url"]
    query = parse_qs(urlsplit(wall_url).query)
    assert urlsplit(wall_url).path == "/respondent_entry/direct"
    assert query["api_key"] == [API_KEY]
    assert query["user_id"] == [get_user_id()]
    assert query["external_id"] == [get_user_id()]
    assert query["partner_id"] == [PARTNER_ID]
    assert query["exchange_rate"] == ["10"]
    assert query["currency_name_plural"] == ["Credits"]
    assert "hash" in query
    assert SECRET_KEY not in wall_url


def test_theoremreach_debug_callback_does_not_change_wallet(client, monkeypatch):
    configure_theoremreach(monkeypatch)
    monkeypatch.setattr(settings, "theoremreach_enabled", False)
    url = callback_url(
        debug="true",
        user_id="",
        tx_id="",
        currency="",
        partner_id="",
    )
    initial_balance = get_wallet_balance()

    response = client.get(url)

    assert response.status_code == 200
    assert get_wallet_balance() == initial_balance

    live_callback = client.get(callback_url())
    assert live_callback.status_code == 503
    assert get_wallet_balance() == initial_balance


def test_theoremreach_verified_callback_credits_once_and_reverses_once(client, monkeypatch):
    configure_theoremreach(monkeypatch)
    activate_package(client, "THEOREMREACH-CALLBACK-001")
    initial_balance = get_wallet_balance()

    first = client.get(callback_url())
    assert first.status_code == 200
    credited_balance = get_wallet_balance()
    assert credited_balance != initial_balance
    assert client.get(callback_url()).status_code == 200
    assert get_wallet_balance() == credited_balance

    reversal_url = callback_url(currency="-1.25", reversal="true")
    reversal = client.get(reversal_url)
    assert reversal.status_code == 200
    reversed_balance = get_wallet_balance()
    assert reversed_balance == initial_balance
    assert client.get(reversal_url).status_code == 200
    assert get_wallet_balance() == reversed_balance

    db = SessionLocal()
    try:
        conversion = db.scalar(
            select(OfferConversion).where(
                OfferConversion.network_id == "theoremreach",
                OfferConversion.external_transaction_id == "theoremreach-reward-1",
            )
        )
        assert conversion is not None
        assert conversion.status == "REVERSED"
    finally:
        db.close()


def test_theoremreach_rejects_bad_hash_duplicate_parameters_and_mismatched_reversal(
    client, monkeypatch
):
    configure_theoremreach(monkeypatch)
    valid_url = callback_url()
    invalid_hash = client.get(valid_url.replace("currency=1.25", "currency=1.26"))
    assert invalid_hash.status_code == 403

    duplicate_parameter = client.get(f"{valid_url}&currency=1.25")
    assert duplicate_parameter.status_code == 400

    mismatched_reversal = client.get(callback_url(reversal="true"))
    assert mismatched_reversal.status_code == 403
