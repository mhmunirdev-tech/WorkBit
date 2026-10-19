from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models import OfferConversion, RewardDecision, RewardPolicy, User, WalletTransaction
from app.services.rewards import reward_decision_service
from conftest import activate_package


def create_click(client):
    activate_package(client, "TESTREWARDPAY01")
    click = client.post("/api/v1/offers/mock-game/click")
    assert click.status_code == 202
    return click.json()["click_id"]


def payload(click_id, transaction="mock-tx-reward-1", payout="1.00", status="PENDING"):
    return {"transaction_id": transaction, "click_id": click_id, "offer_id": "mock-game", "payout": payout, "currency": "USD", "status": status}


def test_reward_policy_seed_exists(client):
    response = client.post("/api/v1/auth/admin/login", json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"})
    assert response.status_code == 200
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        policy = db.scalar(select(RewardPolicy).where(RewardPolicy.name == "default_offer_reward"))
        assert policy is not None
        assert policy.user_reward_percentage == Decimal("80.00")
        assert policy.platform_share_percentage == Decimal("20.00")
        assert policy.minimum_reward == Decimal("0.00")
        assert policy.maximum_reward == Decimal("0.00")
    finally:
        db.close()


def test_approved_conversion_credits_available_balance_and_is_idempotent(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    click_id = create_click(client)
    first = client.post("/api/v1/postbacks/mock", json=payload(click_id, transaction="mock-tx-reward-2", payout="2.00", status="APPROVED"))
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
    assert Decimal(dashboard["available_balance"]) == Decimal("1.60")
    assert Decimal(dashboard["pending_balance"]) == Decimal("0")
    assert Decimal(dashboard["stats"]["today_earnings"]) == Decimal("1.60")
    assert len(dashboard["earnings_chart"]) == 90
    assert client.post(
        "/api/v1/auth/admin/login",
        json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"},
    ).status_code == 200
    admin_dashboard = client.get("/api/v1/admin/dashboard")
    assert admin_dashboard.status_code == 200
    assert Decimal(admin_dashboard.json()["approved_ad_payout"]) == Decimal("2.00")
    assert Decimal(admin_dashboard.json()["platform_ad_revenue"]) == Decimal("0.40")
    assert Decimal(admin_dashboard.json()["registered_user_amount"]) == Decimal("10")


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


def test_provider_approved_reward_is_available_without_admin_approval(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    click_id = create_click(client)
    conversion = client.post("/api/v1/postbacks/mock", json=payload(click_id, transaction="mock-tx-approval", payout="2.00", status="APPROVED"))
    assert conversion.status_code == 202
    reward = client.get("/api/v1/rewards").json()[0]
    assert reward["status"] == "APPROVED"
    wallet = client.get("/api/v1/wallet").json()
    assert Decimal(wallet["pending_balance"]) == Decimal("0")
    assert Decimal(wallet["available_balance"]) == Decimal("1.60")
    assert client.post(
        "/api/v1/auth/admin/login",
        json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"},
    ).status_code == 200
    dashboard = client.get("/api/v1/admin/dashboard")
    assert dashboard.status_code == 200
    assert Decimal(dashboard.json()["approved_ad_payout"]) == Decimal("2.00")
    assert Decimal(dashboard.json()["platform_ad_revenue"]) == Decimal("0.40")
    assert Decimal(dashboard.json()["registered_user_amount"]) == Decimal("10")


def test_provider_pending_conversion_credits_available_balance_when_approved(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    click_id = create_click(client)
    pending_payload = payload(
        click_id,
        transaction="mock-tx-provider-approval",
        payout="2.00",
        status="PENDING",
    )
    created = client.post("/api/v1/postbacks/mock", json=pending_payload)
    assert created.status_code == 202
    assert client.get("/api/v1/rewards").json() == []
    wallet = client.get("/api/v1/wallet").json()
    assert Decimal(wallet["pending_balance"]) == Decimal("0")
    assert Decimal(wallet["available_balance"]) == Decimal("0")

    provider_approval = client.post(
        "/api/v1/postbacks/mock",
        json={**pending_payload, "status": "APPROVED"},
    )
    assert provider_approval.status_code == 202
    assert provider_approval.json()["status"] == "APPROVED"

    wallet = client.get("/api/v1/wallet").json()
    assert Decimal(wallet["pending_balance"]) == Decimal("0")
    assert Decimal(wallet["available_balance"]) == Decimal("1.60")

    decision = client.get("/api/v1/rewards").json()[0]
    assert decision["status"] == "APPROVED"


def test_provider_approved_reward_is_available_without_reward_holding_period(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    click_id = create_click(client)
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        policy = db.scalar(
            select(RewardPolicy).where(RewardPolicy.name == "default_offer_reward")
        )
        assert policy is not None
        policy.pending_period_days = 1
        db.commit()
    finally:
        db.close()

    conversion = client.post(
        "/api/v1/postbacks/mock",
        json=payload(click_id, transaction="mock-tx-reward-withholding", status="APPROVED"),
    )
    assert conversion.status_code == 202
    decision = client.get("/api/v1/rewards").json()[0]
    assert decision["status"] == "APPROVED"
    wallet = client.get("/api/v1/wallet").json()
    assert Decimal(wallet["available_balance"]) == Decimal("0.80")
    assert Decimal(wallet["pending_balance"]) == Decimal("0")


def test_provider_reversal_cancels_pending_reward(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    click_id = create_click(client)
    assert client.post("/api/v1/postbacks/mock", json=payload(click_id, transaction="mock-tx-reversal-reward", payout="2.00")).status_code == 202
    assert client.post("/api/v1/postbacks/mock", json=payload(click_id, transaction="mock-tx-reversal-reward", payout="2.00", status="REVERSED")).status_code == 202
    wallet = client.get("/api/v1/wallet").json()
    assert Decimal(wallet["pending_balance"]) == Decimal("0")
    assert Decimal(wallet["lifetime_earned"]) == Decimal("0")


def test_manual_review_approval_credits_wallet_and_rejecting_approved_reward_conflicts(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    click_id = create_click(client)
    payload_data = payload(click_id, transaction="mock-tx-review-approval", payout="2.00")
    response = client.post("/api/v1/postbacks/mock", json=payload_data)
    assert response.status_code == 202
    review = client.post(
        "/api/v1/postbacks/mock",
        json={**payload_data, "status": "MANUAL_REVIEW"},
    )
    assert review.status_code == 202
    assert review.json()["status"] == "MANUAL_REVIEW"

    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        decision = db.scalar(select(RewardDecision).where(RewardDecision.conversion_id == response.json()["id"]))
        assert decision is not None and decision.status == "MANUAL_REVIEW"
        reward_id = decision.id
    finally:
        db.close()

    assert client.post(
        "/api/v1/auth/admin/login",
        json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"},
    ).status_code == 200
    approved = client.post(f"/api/v1/admin/rewards/{reward_id}/approve")
    assert approved.status_code == 200
    rejected = client.post(f"/api/v1/admin/rewards/{reward_id}/reject")
    assert rejected.status_code == 409

    assert client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"},
    ).status_code == 200
    wallet = client.get("/api/v1/wallet").json()
    assert Decimal(wallet["available_balance"]) == Decimal("1.60")
    assert Decimal(wallet["pending_balance"]) == Decimal("0")


def test_policy_selection_excludes_scope_mismatches_and_breaks_ties_deterministically(client):
    from datetime import datetime, timedelta, timezone

    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "workbit-user@example.com"))
        default_policy = db.scalar(select(RewardPolicy).where(RewardPolicy.name == "default_offer_reward"))
        assert user is not None and default_policy is not None
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add_all(
            [
                RewardPolicy(
                    name="z_country_mismatch",
                    enabled=True,
                    user_reward_percentage=Decimal("90"),
                    platform_share_percentage=Decimal("10"),
                    minimum_reward=Decimal("0"),
                    maximum_reward=Decimal("0"),
                    pending_period_days=0,
                    rounding_precision=2,
                    country_code="CA",
                ),
                RewardPolicy(
                    name="a_global",
                    enabled=True,
                    user_reward_percentage=Decimal("60"),
                    platform_share_percentage=Decimal("40"),
                    minimum_reward=Decimal("0"),
                    maximum_reward=Decimal("0"),
                    pending_period_days=0,
                    rounding_precision=2,
                    effective_from=now_utc - timedelta(minutes=1),
                    effective_to=now_utc + timedelta(minutes=1),
                ),
            ]
        )
        conversion = OfferConversion(
            network_id="mock",
            external_transaction_id="policy-test",
            click_id="a" * 32,
            offer_id="mock-game",
            external_offer_id="mock-game",
            user_id=user.id,
            provider_payout=Decimal("1"),
            currency="USD",
            status="PENDING",
        )
        db.flush()
        policy = reward_decision_service._select_policy(db, user, conversion)
        assert policy is not None
        assert policy.name == "a_global"
    finally:
        db.rollback()
        db.close()


def test_conversion_currency_must_match_wallet_before_persistence(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    click_id = create_click(client)
    response = client.post(
        "/api/v1/postbacks/mock",
        json={**payload(click_id, transaction="mock-tx-currency-mismatch"), "currency": "EUR"},
    )
    assert response.status_code == 422

    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        conversion = db.scalar(
            select(OfferConversion).where(
                OfferConversion.network_id == "mock",
                OfferConversion.external_transaction_id == "mock-tx-currency-mismatch",
            )
        )
        assert conversion is None
    finally:
        db.close()


def test_missing_reward_policy_is_not_created_as_a_fallback(client, monkeypatch):
    from app.core.config import settings
    from app.database.session import SessionLocal

    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    db = SessionLocal()
    try:
        db.query(RewardPolicy).delete()
        db.commit()
    finally:
        db.close()

    click_id = create_click(client)
    response = client.post(
        "/api/v1/postbacks/mock",
        json=payload(click_id, transaction="mock-tx-no-policy", status="APPROVED"),
    )
    assert response.status_code == 503

    db = SessionLocal()
    try:
        assert db.scalar(select(RewardPolicy.id)) is None
    finally:
        db.close()
