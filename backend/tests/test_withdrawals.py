import base64

from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.rate_limit import _hits


def login(client, email="workbit-user@example.com"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WorkBitDev123!"},
    )


def fund_wallet(client, transaction_id="withdrawal-test"):
    _hits.clear()
    assert login(client).status_code == 200
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
        json={"amount": "5.00", "destination": "user@example.com"},
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
    assert before["available_balance"] == "7.00000000"
    response = client.post(
        "/api/v1/withdrawals",
        json={"amount": "5.00", "destination": "user@example.com"},
    )
    assert response.status_code == 201
    request_data = response.json()
    assert request_data["status"] == "PENDING"
    assert request_data["destination_hint"].endswith("com")
    assert "destination" not in request_data
    assert "user@example.com" not in str(request_data)

    wallet = client.get("/api/v1/wallet").json()
    assert wallet["available_balance"] == "2.00000000"
    duplicate = client.post(
        "/api/v1/withdrawals",
        json={"amount": "5.00", "destination": "user@example.com"},
    )
    assert duplicate.status_code == 409
    history = client.get("/api/v1/withdrawals").json()
    assert len(history) == 1
    assert "destination" not in history[0]

    with TestClient(client.app) as admin:
        assert login(admin, "workbit-admin@example.com").status_code == 200
        detail = admin.get(f"/api/v1/admin/withdrawals/{request_data['id']}")
        assert detail.status_code == 200
        assert detail.json()["destination"] == "user@example.com"
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
    assert wallet["available_balance"] == "2.00000000"
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
        json={"amount": "4.99", "destination": "user@example.com"},
    )
    assert invalid.status_code == 400

    response = client.post(
        "/api/v1/withdrawals",
        json={"amount": "5.00", "destination": "user@example.com"},
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
    assert wallet["available_balance"] == "7.00000000"
    assert wallet["lifetime_withdrawn"] == "0E-8"
    transactions = client.get("/api/v1/wallet/transactions").json()
    reserved = next(
        item for item in transactions
        if item["reference_id"] == response.json()["id"] and item["type"] == "WITHDRAWAL_REQUEST"
    )
    assert reserved["status"] == "APPROVED"
    released = next(item for item in transactions if item["type"] == "WITHDRAWAL_RELEASE")
    assert released["status"] == "APPROVED"
