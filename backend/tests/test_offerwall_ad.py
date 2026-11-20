import hashlib
import hmac
import json
from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.database.session import SessionLocal
from app.models import OfferConversion, User, Wallet
from conftest import activate_package

SIGNING_SECRET = "test-offerwall-ad-signing-secret"


def configure_offerwall_ad(monkeypatch):
    monkeypatch.setattr(settings, "offerwall_ad_postback_enabled", True)
    monkeypatch.setattr(settings, "offerwall_ad_signing_secret", SIGNING_SECRET)


def get_user_id():
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "workbit-user@example.com"))
        assert user is not None
        return user.id
    finally:
        db.close()


def get_balances():
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "workbit-user@example.com"))
        assert user is not None
        wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id))
        assert wallet is not None
        return Decimal(wallet.available_balance), Decimal(wallet.pending_balance)
    finally:
        db.close()


def callback_payload(user_id, event, status, transaction_id="owa-tx-1"):
    return {
        "subid": user_id,
        "transaction_id": transaction_id,
        "conversion_id": "owa-conversion-1",
        "offer_id": "offer-42",
        "offer_name": "Test offer",
        "payout": "1.25000000",
        "currency": "USD",
        "status": status,
        "event": event,
        "network": "test-network",
        "campaign_id": "campaign-3",
        "click_id": "provider-click-4",
        "unix_timestamp": "1793030000",
    }


def send_callback(client, payload, event_id="event-1", signature_source="body"):
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(
        SIGNING_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return client.post(
        "/api/v1/postbacks/offerwall-ad",
        content=raw_body,
        headers={
            "content-type": "application/json",
            "x-offerwall-ad-event": payload["event"],
            "x-offerwall-ad-event-id": event_id,
            "x-offerwall-ad-signature": f"sha256={signature}",
            "x-offerwall-ad-signature-source": signature_source,
        },
    )


def test_offerwall_ad_signed_approval_is_idempotent_and_reverses(
    client, monkeypatch
):
    configure_offerwall_ad(monkeypatch)
    activate_package(client, "OFFERWALL-AD-CALLBACK")
    user_id = get_user_id()
    before = get_balances()

    approved = callback_payload(
        user_id, "conversion.approved", "approved"
    )
    first = send_callback(client, approved)
    duplicate = send_callback(client, approved)
    assert first.status_code == duplicate.status_code == 200
    assert get_balances()[0] - before[0] == Decimal("0.87500000")

    reversed_payload = callback_payload(
        user_id,
        "conversion.reversed",
        "reversed",
    )
    reversed_response = send_callback(client, reversed_payload, event_id="event-2")
    duplicate_reversal = send_callback(
        client, reversed_payload, event_id="event-2"
    )
    assert reversed_response.status_code == duplicate_reversal.status_code == 200
    assert get_balances() == before

    db = SessionLocal()
    try:
        conversion = db.scalar(
            select(OfferConversion).where(
                OfferConversion.network_id == "offerwall-ad",
                OfferConversion.external_transaction_id == "owa-tx-1",
            )
        )
        assert conversion is not None
        assert conversion.status == "REVERSED"
    finally:
        db.close()


def test_offerwall_ad_held_reward_is_pending_until_release(client, monkeypatch):
    configure_offerwall_ad(monkeypatch)
    activate_package(client, "OFFERWALL-AD-HELD")
    user_id = get_user_id()
    before = get_balances()

    held = send_callback(
        client,
        callback_payload(user_id, "conversion.held", "held"),
    )
    assert held.status_code == 200
    pending = get_balances()
    assert pending[0] == before[0]
    assert pending[1] - before[1] == Decimal("0.87500000")

    released = send_callback(
        client,
        callback_payload(user_id, "conversion.released", "approved"),
        event_id="event-2",
    )
    assert released.status_code == 200
    after_release = get_balances()
    assert after_release[0] - before[0] == Decimal("0.87500000")
    assert after_release[1] == before[1]


def test_offerwall_ad_rejects_bad_signatures_and_non_body_signing(
    client, monkeypatch
):
    configure_offerwall_ad(monkeypatch)
    payload = callback_payload(
        get_user_id(), "conversion.approved", "approved"
    )
    response = send_callback(client, payload, signature_source="url")
    assert response.status_code == 403

    valid_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    invalid_signature = hmac.new(
        SIGNING_SECRET.encode("utf-8"), b"tampered", hashlib.sha256
    ).hexdigest()
    response = client.post(
        "/api/v1/postbacks/offerwall-ad",
        content=valid_body,
        headers={
            "content-type": "application/json",
            "x-offerwall-ad-event": payload["event"],
            "x-offerwall-ad-event-id": "event-1",
            "x-offerwall-ad-signature": f"sha256={invalid_signature}",
            "x-offerwall-ad-signature-source": "body",
        },
    )
    assert response.status_code == 403


def test_offerwall_ad_rejects_duplicate_json_fields(client, monkeypatch):
    configure_offerwall_ad(monkeypatch)
    user_id = get_user_id()
    payload = callback_payload(user_id, "conversion.approved", "approved")
    raw_body = json.dumps(payload, separators=(",", ":")).replace(
        '"event":"conversion.approved"',
        '"event":"conversion.approved","event":"conversion.reversed"',
    ).encode("utf-8")
    signature = hmac.new(
        SIGNING_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()

    response = client.post(
        "/api/v1/postbacks/offerwall-ad",
        content=raw_body,
        headers={
            "content-type": "application/json",
            "x-offerwall-ad-event": "conversion.approved",
            "x-offerwall-ad-event-id": "event-1",
            "x-offerwall-ad-signature": f"sha256={signature}",
            "x-offerwall-ad-signature-source": "body",
        },
    )

    assert response.status_code == 400


def test_offerwall_ad_postback_is_disabled_by_default(client):
    assert client.post("/api/v1/postbacks/offerwall-ad").status_code == 503
