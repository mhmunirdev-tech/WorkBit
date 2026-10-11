import base64
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.rate_limit import _hits
from conftest import activate_package, configure_payout_rate


def login(client, email="workbit-user@example.com"):
    route = "/api/v1/auth/admin/login" if email == "workbit-admin@example.com" else "/api/v1/auth/login"
    return client.post(
        route,
        json={"email": email, "password": "WorkBitDev123!"},
    )


def fund_wallet(client, transaction_id="withdrawal-test"):
    _hits.clear()
    activate_package(client, f"TESTWITHDRAWAL{transaction_id}"[:120])
    configure_payout_rate(client)
    click = client.post("/api/v1/offers/mock-game/click")
    assert click.status_code == 202
    response = client.post(
        "/api/v1/postbacks/mock",
        json={
            "transaction_id": transaction_id,
            "click_id": click.json()["click_id"],
            "offer_id": "mock-game",
            "payout": "10.00",
            "currency": "USD",
            "status": "APPROVED",
        },
    )
    assert response.status_code == 202


def test_withdrawals_require_configuration_and_are_private(client, monkeypatch):
    login(client)
    assert client.get("/api/v1/withdrawals").status_code == 200
    response = client.post(
        "/api/v1/withdrawals",
        json={"amount": "5.00", "destination": "01712345678", "payment_method": "BKASH"},
    )
    assert response.status_code == 503
    monkeypatch.setattr(settings, "withdrawal_encryption_key", "not-valid-base64")
    invalid_key = client.post(
        "/api/v1/withdrawals",
        json={"amount": "5.00", "destination": "user@example.com"},
    )
    assert invalid_key.status_code == 503
    assert client.get("/api/v1/dashboard").json()["withdrawal_summary"]["enabled"] is False
    assert client.get("/api/v1/admin/withdrawals").status_code == 403


def test_withdrawal_reserves_funds_and_admin_completes(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"w" * 32).decode("ascii"),
    )
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    fund_wallet(client, "withdrawal-complete-test")

    before = client.get("/api/v1/wallet").json()
    assert before["available_balance"] == "8.00000000"
    response = client.post(
        "/api/v1/withdrawals",
        json={"amount": "5.00", "destination": "01712345678", "payment_method": "BKASH"},
    )
    assert response.status_code == 201
    request_data = response.json()
    assert request_data["status"] == "PENDING"
    assert request_data["destination_hint"].endswith("5678")
    assert request_data["method"] == "BKASH"
    assert request_data["payout_currency"] == "BDT"
    assert request_data["payout_amount"] == "600.00000000"
    assert request_data["exchange_rate"] == "120.00000000"
    assert "destination" not in request_data
    assert "01712345678" not in str(request_data)

    wallet = client.get("/api/v1/wallet").json()
    assert wallet["available_balance"] == "3.00000000"
    duplicate = client.post(
        "/api/v1/withdrawals",
        json={"amount": "5.00", "destination": "01712345678", "payment_method": "BKASH"},
    )
    assert duplicate.status_code == 409
    history = client.get("/api/v1/withdrawals").json()
    assert len(history) == 1
    assert "destination" not in history[0]

    with TestClient(client.app) as admin:
        assert login(admin, "workbit-admin@example.com").status_code == 200
        detail = admin.get(f"/api/v1/admin/withdrawals/{request_data['id']}")
        assert detail.status_code == 200
        assert detail.json()["destination"] == "01712345678"
        assert admin.post(
            f"/api/v1/admin/withdrawals/{request_data['id']}/approve",
            json={"note": "Payout verified."},
        ).status_code == 200
        completed = admin.post(
            f"/api/v1/admin/withdrawals/{request_data['id']}/complete",
            json={"note": "Paid manually."},
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "COMPLETED"

    wallet = client.get("/api/v1/wallet").json()
    assert wallet["available_balance"] == "3.00000000"
    assert wallet["lifetime_withdrawn"] == "5.00000000"
    transactions = client.get("/api/v1/wallet/transactions").json()
    reserved = next(item for item in transactions if item["reference_id"] == request_data["id"])
    assert reserved["status"] == "APPROVED"


def test_rejected_withdrawal_releases_balance_and_enforces_minimum(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"r" * 32).decode("ascii"),
    )
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    fund_wallet(client, "withdrawal-reject-test")
    invalid = client.post(
        "/api/v1/withdrawals",
        json={"amount": "4.99", "destination": "01712345678", "payment_method": "BKASH"},
    )
    assert invalid.status_code == 400

    response = client.post(
        "/api/v1/withdrawals",
        json={"amount": "5.00", "destination": "01712345678", "payment_method": "BKASH"},
    )
    assert response.status_code == 201

    with TestClient(client.app) as admin:
        assert login(admin, "workbit-admin@example.com").status_code == 200
        rejected = admin.post(
            f"/api/v1/admin/withdrawals/{response.json()['id']}/reject",
            json={"note": "Destination needs correction."},
        )
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "REJECTED"

    wallet = client.get("/api/v1/wallet").json()
    assert wallet["available_balance"] == "8.00000000"
    assert wallet["lifetime_withdrawn"] == "0E-8"
    transactions = client.get("/api/v1/wallet/transactions").json()
    reserved = next(
        item for item in transactions
        if item["reference_id"] == response.json()["id"] and item["type"] == "WITHDRAWAL_REQUEST"
    )
    assert reserved["status"] == "APPROVED"
    released = next(item for item in transactions if item["type"] == "WITHDRAWAL_RELEASE")
    assert released["status"] == "APPROVED"


def test_payout_exchange_rate_is_admin_configurable_and_snapshotted(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"r" * 32).decode("ascii"),
    )
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    fund_wallet(client, "withdrawal-rate-snapshot")

    summary = client.get("/api/v1/dashboard").json()
    assert summary["withdrawal_summary"]["enabled"] is True
    assert summary["withdrawal_summary"]["usd_bdt_rate"] == "120.00000000"
    assert summary["withdrawal_summary"]["minimum_amount"] == "5.00"

    invalid_number = client.post(
        "/api/v1/withdrawals",
        json={"amount": "5.00", "destination": "01234567890", "payment_method": "NAGAD"},
    )
    assert invalid_number.status_code == 422

    created = client.post(
        "/api/v1/withdrawals",
        json={"amount": "5.00", "destination": "+8801712345678", "payment_method": "NAGAD"},
    )
    assert created.status_code == 201
    assert created.json()["destination_hint"].endswith("5678")
    assert created.json()["payout_amount"] == "600.00000000"

    from app.database.session import SessionLocal
    from app.models import PayoutSettings

    db = SessionLocal()
    try:
        rate = db.get(PayoutSettings, "default")
        assert rate is not None and rate.usd_bdt_rate == Decimal("120.00")
    finally:
        db.close()


def test_withdrawal_rate_must_be_configured_and_is_admin_only(client):
    assert login(client).status_code == 200
    assert client.get("/api/v1/admin/payout-settings").status_code == 403
    assert client.put(
        "/api/v1/admin/payout-settings",
        json={"usd_bdt_rate": "120.00"},
    ).status_code == 403
    assert client.get("/api/v1/dashboard").json()["withdrawal_summary"]["enabled"] is False


def test_withdrawal_minimum_is_enforced_by_backend(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"m" * 32).decode("ascii"),
    )
    fund_wallet(client, "withdrawal-minimum-check")
    response = client.post(
        "/api/v1/withdrawals",
        json={"amount": "4.99", "destination": "01712345678", "payment_method": "BKASH"},
    )
    assert response.status_code == 400
