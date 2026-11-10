from decimal import Decimal

from conftest import activate_package


def test_admin_provider_performance_aggregates_rewards_and_reversals(client, monkeypatch):
    from app.core.config import settings
    from app.database.session import SessionLocal
    from app.models import RewardDecision
    from app.services.rewards import reward_decision_service
    from sqlalchemy import select

    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    activate_package(client, "TESTPROVIDER001")
    click = client.post("/api/v1/offers/mock-game/click").json()
    conversion = client.post(
        "/api/v1/postbacks/mock",
        json={
            "transaction_id": "provider-performance-1",
            "click_id": click["click_id"],
            "offer_id": "mock-game",
            "payout": "2.00",
            "currency": "USD",
            "status": "APPROVED",
        },
    )
    assert conversion.status_code == 202

    admin = client.post(
        "/api/v1/auth/admin/login",
        json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"},
    )
    assert admin.status_code == 200

    response = client.get("/api/v1/analytics/admin/provider-performance")
    assert response.status_code == 200
    provider = next(row for row in response.json() if row["provider"] == "mock")
    assert provider["conversions"] == 1
    assert provider["approved"] == 1
    assert provider["approval_rate"] == 100
    assert Decimal(provider["approved_provider_payout_usd"]) == Decimal("2.00")
    assert Decimal(provider["approved_user_rewards_usd"]) == Decimal("1.40")

    db = SessionLocal()
    try:
        decision = db.scalar(select(RewardDecision))
        assert decision is not None
        reward_decision_service.transition_decision(
            db, decision, "REVERSED", "Provider reported a duplicate completion."
        )
    finally:
        db.close()

    after_reversal = client.get("/api/v1/analytics/admin/provider-performance")
    provider = next(row for row in after_reversal.json() if row["provider"] == "mock")
    assert provider["reversed"] == 1
    assert provider["approval_rate"] == 0
    assert Decimal(provider["reversed_user_rewards_usd"]) == Decimal("1.40")


def test_provider_performance_requires_admin_permission(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"},
    )
    assert login.status_code == 200
    assert client.get("/api/v1/analytics/admin/provider-performance").status_code == 401
