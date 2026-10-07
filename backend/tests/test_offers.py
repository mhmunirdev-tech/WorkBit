from sqlalchemy import select
from app.models import AdNetwork, OfferNetwork
from app.services.rate_limit import _hits

def login(client):
    response = client.post("/api/v1/auth/login", json={"email":"workbit-user@example.com", "password":"WorkBitDev123!"})
    assert response.status_code == 200

def test_offer_listing_and_filters(client):
    offers = client.get("/api/v1/offers?country=US").json()
    assert len(offers) == 3 and all(item["is_demo"] for item in offers)
    surveys = client.get("/api/v1/offers?country=US&category=SURVEY").json()
    assert len(surveys) == 1 and surveys[0]["category"] == "SURVEY"
    mobile = client.get("/api/v1/offers?country=US&device=MOBILE").json()
    assert len(mobile) == 1 and mobile[0]["device_type"] == "MOBILE"

def test_offer_detail_and_invalid_offer(client):
    assert client.get("/api/v1/offers/mock-game?country=US").status_code == 200
    assert client.get("/api/v1/offers/not-real?country=US").status_code == 404

def test_click_requires_authentication(client):
    assert client.post("/api/v1/offers/mock-game/click").status_code == 401
    assert client.post("/api/v1/offers/mock-game/redirect").status_code == 401

def test_unconfigured_provider_never_redirects(client):
    login(client)
    assert client.post("/api/v1/offers/mock-game/redirect").status_code == 503

def test_mock_click_is_recorded_without_reward(client):
    login(client); _hits.clear()
    response = client.post("/api/v1/offers/mock-game/click", headers={"user-agent":"pytest"})
    assert response.status_code == 202
    assert response.json()["status"] == "recorded"
    assert "No reward" in response.json()["message"]

def test_duplicate_click_is_rate_limited(client):
    login(client); _hits.clear()
    assert client.post("/api/v1/offers/mock-game/click").status_code == 202
    assert client.post("/api/v1/offers/mock-game/click").status_code == 429


def test_seeded_offer_networks_are_disabled_and_secrets_are_env_references(database):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        networks = db.scalars(select(OfferNetwork)).all()
        assert len(networks) == 10
        assert {network.slug for network in networks} == {
            "lootably", "adgem", "cpalead", "offerwall-gg", "monlix",
            "bitlabs", "adgate", "torox", "adswedmedia", "revu",
        }
        assert all(not network.enabled and network.status == "NOT_CONFIGURED" for network in networks)
        assert all(network.api_key_env and network.secret_key_env for network in networks)
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
