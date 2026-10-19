from decimal import Decimal

from sqlalchemy import select

from app.models import AdNetwork, Offer, OfferNetwork
from app.services.rate_limit import _hits
from conftest import activate_package

def login(client):
    response = client.post("/api/v1/auth/login", json={"email":"workbit-user@example.com", "password":"WorkBitDev123!"})
    assert response.status_code == 200

def test_offer_listing_and_filters(client):
    offers = client.get("/api/v1/offers?country=US").json()
    assert len(offers) == 6 and all(item["is_demo"] for item in offers)
    assert {item["source_name"] for item in offers} == {
        "Demo Games API",
        "Demo Surveys API",
        "Demo Apps API",
    }
    surveys = client.get("/api/v1/offers?country=US&category=SURVEY").json()
    assert len(surveys) == 2 and all(item["category"] == "SURVEY" for item in surveys)
    mobile = client.get("/api/v1/offers?country=US&device=MOBILE").json()
    assert len(mobile) == 2 and all(item["device_type"] == "MOBILE" for item in mobile)

def test_offer_detail_and_invalid_offer(client):
    assert client.get("/api/v1/offers/mock-game?country=US").status_code == 200
    assert client.get("/api/v1/offers/not-real?country=US").status_code == 404


def test_development_offer_content_is_loaded_from_database(client):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        offer = db.get(Offer, "mock-game")
        assert offer is not None
        offer.title = "Database-managed offer"
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/offers/mock-game?country=US")
    assert response.status_code == 200
    assert response.json()["title"] == "Database-managed offer"


def test_demo_offers_are_available_for_the_account_country(client):
    offers = client.get("/api/v1/offers?country=BD").json()

    assert len(offers) == 6
    assert all(item["country"] == "BD" for item in offers)
    detail = client.get("/api/v1/offers/mock-game?country=BD")
    assert detail.status_code == 200
    assert detail.json()["country"] == "BD"


def test_click_requires_authentication(client):
    assert client.post("/api/v1/offers/mock-game/click").status_code == 401
    assert client.post("/api/v1/offers/mock-game/redirect").status_code == 401

def test_unconfigured_provider_never_redirects(client):
    login(client)
    activate_package(client, "TESTOFFERPAY01")
    assert client.post("/api/v1/offers/mock-game/redirect").status_code == 503

def test_mock_click_is_recorded_without_reward(client):
    activate_package(client, "TESTOFFERPAY02"); _hits.clear()
    response = client.post("/api/v1/offers/mock-game/click", headers={"user-agent":"pytest"})
    assert response.status_code == 202
    assert response.json()["status"] == "recorded"
    assert "No reward" in response.json()["message"]


def test_simulated_ad_completion_credits_available_balance_immediately(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    activate_package(client, "TESTOFFER-SIMULATED-AD")
    _hits.clear()

    click = client.post("/api/v1/offers/mock-game/click")
    assert click.status_code == 202

    response = client.post("/api/v1/offers/mock-game/simulate-completion")

    assert response.status_code == 200
    assert response.json()["reward_status"] == "APPROVED"
    gross_ad_reward = Decimal(client.get("/api/v1/offers/mock-game?country=US").json()["user_reward"])
    expected_user_reward = gross_ad_reward * Decimal("0.80")
    expected_platform_share = gross_ad_reward * Decimal("0.20")
    assert Decimal(response.json()["reward_amount"]) == expected_user_reward
    assert Decimal(response.json()["platform_share_amount"]) == expected_platform_share
    assert Decimal(response.json()["available_balance"]) == expected_user_reward
    assert "was retained as the platform share" in response.json()["message"]
    assert Decimal(response.json()["pending_balance"]) == Decimal("0")
    assert "available balance" in response.json()["message"]
    wallet = client.get("/api/v1/wallet").json()
    assert Decimal(wallet["available_balance"]) == expected_user_reward
    assert Decimal(wallet["pending_balance"]) == Decimal("0")

    repeated = client.post("/api/v1/offers/mock-game/simulate-completion")
    assert repeated.status_code == 429
    assert repeated.json()["error"]["message"] == "Please wait before starting this offer again."


def test_simulated_ad_completion_splits_gross_rewards_and_reports_platform_share(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    activate_package(client, "TESTOFFER-SIMULATED-AMOUNTS")
    _hits.clear()

    offers = client.get("/api/v1/offers?country=US").json()
    expected_user_total = Decimal("0")
    expected_platform_total = Decimal("0")
    for offer in offers:
        response = client.post(f"/api/v1/offers/{offer['id']}/simulate-completion")
        gross_ad_reward = Decimal(offer["user_reward"])

        assert response.status_code == 200
        assert Decimal(response.json()["reward_amount"]) == gross_ad_reward * Decimal("0.80")
        assert Decimal(response.json()["platform_share_amount"]) == gross_ad_reward * Decimal("0.20")
        expected_user_total += gross_ad_reward * Decimal("0.80")
        expected_platform_total += gross_ad_reward * Decimal("0.20")

    wallet = client.get("/api/v1/wallet").json()
    assert Decimal(wallet["available_balance"]) == expected_user_total
    assert Decimal(wallet["pending_balance"]) == Decimal("0")

    assert client.post(
        "/api/v1/auth/admin/login",
        json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"},
    ).status_code == 200
    admin_dashboard = client.get("/api/v1/admin/dashboard")
    assert admin_dashboard.status_code == 200
    assert Decimal(admin_dashboard.json()["approved_ad_payout"]) == sum(
        (Decimal(offer["user_reward"]) for offer in offers),
        Decimal("0"),
    )
    assert Decimal(admin_dashboard.json()["platform_ad_revenue"]) == expected_platform_total


def test_simulated_ad_completion_requires_development_mock_rewards(client, monkeypatch):
    from app.core.config import settings

    login(client)
    _hits.clear()
    disabled = client.post("/api/v1/offers/mock-game/simulate-completion")
    assert disabled.status_code == 503

    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    monkeypatch.setattr(settings, "environment", "production")
    production = client.post("/api/v1/offers/mock-game/simulate-completion")
    assert production.status_code == 503


def test_duplicate_click_is_rate_limited(client):
    activate_package(client, "TESTOFFERPAY03"); _hits.clear()
    assert client.post("/api/v1/offers/mock-game/click").status_code == 202
    limited = client.post("/api/v1/offers/mock-game/click")
    assert limited.status_code == 429
    assert limited.json()["error"]["message"] == "Please wait before starting this offer again."


def test_click_requires_an_approved_package(client):
    login(client)
    response = client.post("/api/v1/offers/mock-game/click")
    assert response.status_code == 402
    assert response.json()["error"]["code"] == "PAYMENT_REQUIRED"


def test_seeded_offer_networks_are_disabled_and_secrets_are_env_references(database):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        networks = db.scalars(select(OfferNetwork)).all()
        provider_networks = [network for network in networks if network.provider != "MOCK"]
        assert len(provider_networks) == 10
        assert {network.slug for network in provider_networks} == {
            "lootably", "adgem", "cpalead", "offerwall-gg", "monlix",
            "bitlabs", "adgate", "torox", "adswedmedia", "revu",
        }
        assert all(not network.enabled and network.status == "NOT_CONFIGURED" for network in provider_networks)
        assert all(network.api_key_env and network.secret_key_env for network in provider_networks)
        mock_networks = [network for network in networks if network.provider == "MOCK"]
        assert {network.name for network in mock_networks} == {
            "Demo Games API",
            "Demo Surveys API",
            "Demo Apps API",
        }
        assert all(not network.enabled and network.status == "DEVELOPMENT_ONLY" for network in mock_networks)
        assert not hasattr(OfferNetwork, "api_key")
        assert not hasattr(OfferNetwork, "secret_key")
    finally:
        db.close()


def test_ad_network_registry_is_separate(database):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        ad_networks = db.scalars(select(AdNetwork)).all()
        assert {network.slug for network in ad_networks} == {"workbit-ad-manager", "other-ads"}
        assert all(not network.enabled and network.status == "NOT_CONFIGURED" for network in ad_networks)
    finally:
        db.close()


def test_non_mock_offer_postbacks_are_unavailable_without_assuming_a_payload(client):
    response = client.post("/api/v1/postbacks/adgem", json={"some": "unverified fields"})
    assert response.status_code == 503
    assert "not configured" in response.json()["error"]["message"].lower()


def test_mock_offer_catalog_is_unavailable_outside_development(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "environment", "production")
    assert client.get("/api/v1/offers?country=US").status_code == 503
