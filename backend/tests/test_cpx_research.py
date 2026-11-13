import hashlib
from decimal import Decimal
from urllib.parse import parse_qs, urlencode, urlsplit

from sqlalchemy import select

from app.core.config import settings
from app.database.session import SessionLocal
from app.models import OfferConversion, User, Wallet
from conftest import activate_package

APP_ID = "37861"
APP_SECURE_HASH = "test-cpx-secure-hash"


def configure_cpx_research(monkeypatch):
    monkeypatch.setattr(settings, "cpx_research_enabled", True)
    monkeypatch.setattr(settings, "cpx_research_postback_enabled", True)
    monkeypatch.setattr(settings, "cpx_research_app_id", APP_ID)
    monkeypatch.setattr(settings, "cpx_research_secure_hash", APP_SECURE_HASH)


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


def callback_url(user_id, transaction_id="cpx-tx-1", **overrides):
    values = {
        "status": "1",
        "trans_id": transaction_id,
        "user_id": user_id,
        "sub_id": "workbit-sub-1",
        "sub_id_2": "",
        "amount_local": "1.25",
        "amount_usd": "1.25",
        "offer_id": "cpx-survey-1",
        "ip_click": "203.0.113.10",
        "type": "complete",
    }
    values.update(overrides)
    values["hash"] = hashlib.md5(
        f"{values['trans_id']}-{APP_SECURE_HASH}".encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()
    return f"/api/v1/postbacks/cpx-research?{urlencode(values)}"


def test_cpx_research_wall_url_is_available_without_package_and_uses_verified_user_id(
    client, monkeypatch
):
    configure_cpx_research(monkeypatch)
    login_user(client)

    response = client.get("/api/v1/offers/providers/cpx-research/wall-url")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert APP_SECURE_HASH not in response.json()["wall_url"]
    query = parse_qs(urlsplit(response.json()["wall_url"]).query)
    user_id = get_user_id()
    expected_hash = hashlib.md5(
        f"{user_id}-{APP_SECURE_HASH}".encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()

    assert urlsplit(response.json()["wall_url"]).scheme == "https"
    assert urlsplit(response.json()["wall_url"]).netloc == "offers.cpx-research.com"
    assert query == {
        "app_id": [APP_ID],
        "ext_user_id": [user_id],
        "secure_hash": [expected_hash],
    }


def test_cpx_research_wall_url_is_hidden_when_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "cpx_research_enabled", False)
    login_user(client)
    activate_package(client, "CPX-RESEARCH-DISABLED-001")

    response = client.get("/api/v1/offers/providers/cpx-research/wall-url")

    assert response.status_code == 404


def test_cpx_research_wall_url_reports_missing_secure_hash(client, monkeypatch):
    configure_cpx_research(monkeypatch)
    monkeypatch.setattr(settings, "cpx_research_secure_hash", None)
    login_user(client)
    activate_package(client, "CPX-RESEARCH-MISSING-HASH")

    response = client.get("/api/v1/offers/providers/cpx-research/wall-url")

    assert response.status_code == 503
    assert "secure hash" in response.json()["error"]["message"].lower()


def test_cpx_research_callback_credits_once_and_reverses_canceled_transaction(
    client, monkeypatch
):
    configure_cpx_research(monkeypatch)
    activate_package(client, "CPX-RESEARCH-CALLBACK")
    user_id = get_user_id()
    before = get_wallet_balance()

    first = client.get(callback_url(user_id))
    duplicate = client.get(callback_url(user_id))

    assert first.status_code == duplicate.status_code == 200
    credited = get_wallet_balance()
    assert credited[0] - before[0] == Decimal("0.87500000")

    reversal = client.get(
        callback_url(
            user_id,
            status="2",
        )
    )
    duplicate_reversal = client.get(
        callback_url(
            user_id,
            status="2",
        )
    )

    assert reversal.status_code == duplicate_reversal.status_code == 200
    assert get_wallet_balance() == before
    db = SessionLocal()
    try:
        conversion = db.scalar(
            select(OfferConversion).where(
                OfferConversion.network_id == "cpx-research",
                OfferConversion.external_transaction_id == "cpx-tx-1",
            )
        )
        assert conversion is not None and conversion.status == "REVERSED"
    finally:
        db.close()


def test_cpx_research_callback_rejects_bad_hash_duplicate_params_and_unknown_user(
    client, monkeypatch
):
    configure_cpx_research(monkeypatch)
    user_id = get_user_id()
    valid_url = callback_url(user_id)

    invalid_hash = client.get(valid_url.replace("trans_id=cpx-tx-1", "trans_id=cpx-tx-invalid"))
    assert invalid_hash.status_code == 403
    duplicate_parameter = client.get(f"{valid_url}&amount_usd=1.25")
    assert duplicate_parameter.status_code == 400
    unknown_user = client.get(callback_url("bd3dca27-26fe-4f66-9e3a-68c9343fbdbd"))
    assert unknown_user.status_code == 400


def test_cpx_research_callback_rejects_amount_change_for_existing_transaction(
    client, monkeypatch
):
    configure_cpx_research(monkeypatch)
    activate_package(client, "CPX-RESEARCH-AMOUNT-MISMATCH")
    user_id = get_user_id()
    before = get_wallet_balance()

    credited = client.get(callback_url(user_id))
    changed_amount = client.get(
        callback_url(
            user_id,
            amount_usd="8.25",
            amount_local="8.25",
        )
    )

    assert credited.status_code == 200
    assert changed_amount.status_code == 409
    assert get_wallet_balance()[0] - before[0] == Decimal("0.87500000")


def test_cpx_research_callback_is_disabled_separately_from_wall(client, monkeypatch):
    configure_cpx_research(monkeypatch)
    monkeypatch.setattr(settings, "cpx_research_postback_enabled", False)
    activate_package(client, "CPX-RESEARCH-POSTBACK-DISABLED")
    login_user(client)

    wall = client.get("/api/v1/offers/providers/cpx-research/wall-url")
    callback = client.get(callback_url(get_user_id()))

    assert wall.status_code == 200
    assert callback.status_code == 503
    assert get_wallet_balance() == (Decimal("0E-8"), Decimal("0E-8"))
