from decimal import Decimal

from sqlalchemy import select

from app.models import RewardDecision, RewardPolicy, WalletTransaction


def create_click(client):
    response = client.post("/api/v1/auth/login", json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"})
    assert response.status_code == 200
    click = client.post("/api/v1/offers/mock-game/click")
    assert click.status_code == 202
    return click.json()["click_id"]


def payload(click_id, transaction="mock-tx-reward-1", payout="1.00", status="PENDING"):
    return {"transaction_id": transaction, "click_id": click_id, "offer_id": "mock-game", "payout": payout, "currency": "USD", "status": status}


def test_reward_policy_seed_exists(client):
    response = client.post("/api/v1/auth/login", json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"})
    assert response.status_code == 200
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        policy = db.scalar(select(RewardPolicy).where(RewardPolicy.name == "default_offer_reward"))
        assert policy is not None
        assert policy.user_reward_percentage == Decimal("70.00")
        assert policy.platform_share_percentage == Decimal("30.00")
    finally:
        db.close()


def test_reward_decision_is_idempotent_and_wallet_projects(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    click_id = create_click(client)
    first = client.post("/api/v1/postbacks/mock", json=payload(click_id, transaction="mock-tx-reward-2", payout="2.00"))
    assert first.status_code == 202
    second = client.post("/api/v1/postbacks/mock", json=payload(click_id, transaction="mock-tx-reward-2", payout="2.00"))
    assert second.status_code == 409

    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        decisions = db.scalars(select(RewardDecision).where(RewardDecision.conversion_id == first.json()["id"])).all()
        assert len(decisions) == 1
        txs = db.scalars(select(WalletTransaction).where(WalletTransaction.reference_type == "reward_decision")).all()
        assert len(txs) >= 1
    finally:
        db.close()

    dashboard = client.get("/api/v1/dashboard").json()
    assert Decimal(dashboard["available_balance"]) >= Decimal("0")
    assert Decimal(dashboard["pending_balance"]) == Decimal("1.40")
    assert Decimal(dashboard["stats"]["today_earnings"]) == Decimal("0")
    assert len(dashboard["earnings_chart"]) == 90


def test_mock_conversion_does_not_reward_without_explicit_opt_in(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "enable_mock_rewards", False)
    click_id = create_click(client)
    response = client.post("/api/v1/postbacks/mock", json=payload(click_id, transaction="mock-tx-reward-disabled", payout="2.00"))
    assert response.status_code == 202
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["available_balance"] == "0E-8"
    assert dashboard["pending_balance"] == "0E-8"


def test_wallet_and_reward_endpoints_require_auth(client):
    assert client.get("/api/v1/wallet").status_code == 401
    assert client.get("/api/v1/wallet/transactions").status_code == 401
    assert client.get("/api/v1/rewards").status_code == 401

    login = client.post("/api/v1/auth/login", json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"})
    assert login.status_code == 200
    assert client.get("/api/v1/wallet").status_code == 200
    assert client.get("/api/v1/wallet/transactions").status_code == 200
    assert client.get("/api/v1/rewards").status_code == 200


def test_admin_approval_releases_pending_reward_to_available_balance(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    click_id = create_click(client)
    conversion = client.post("/api/v1/postbacks/mock", json=payload(click_id, transaction="mock-tx-approval", payout="2.00"))
    assert conversion.status_code == 202
    reward = client.get("/api/v1/rewards").json()[0]
    assert client.post("/api/v1/auth/login", json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"}).status_code == 200
    assert client.post(f"/api/v1/admin/rewards/{reward['id']}/approve").status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"}).status_code == 200
    wallet = client.get("/api/v1/wallet").json()
    assert Decimal(wallet["pending_balance"]) == Decimal("0")
    assert Decimal(wallet["available_balance"]) == Decimal("1.40")


def test_provider_reversal_cancels_pending_reward(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    click_id = create_click(client)
    assert client.post("/api/v1/postbacks/mock", json=payload(click_id, transaction="mock-tx-reversal-reward", payout="2.00")).status_code == 202
    assert client.post("/api/v1/postbacks/mock", json=payload(click_id, transaction="mock-tx-reversal-reward", payout="2.00", status="REVERSED")).status_code == 202
    wallet = client.get("/api/v1/wallet").json()
    assert Decimal(wallet["pending_balance"]) == Decimal("0")
    assert Decimal(wallet["lifetime_earned"]) == Decimal("0")
