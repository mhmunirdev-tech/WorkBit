from sqlalchemy import select

from app.models import RewardNotification
from conftest import activate_package


def test_reward_notification_tracks_status_and_is_user_scoped(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    activate_package(client, "TESTNOTIF001")
    click = client.post("/api/v1/offers/mock-game/click")
    assert click.status_code == 202
    conversion_payload = {
        "transaction_id": "notification-reward-1",
        "click_id": click.json()["click_id"],
        "offer_id": "mock-game",
        "payout": "2.00",
        "currency": "USD",
        "status": "PENDING",
    }

    pending = client.post("/api/v1/postbacks/mock", json=conversion_payload)
    assert pending.status_code == 202
    assert client.get("/api/v1/notifications").status_code == 200
    assert client.get("/api/v1/notifications").json()["items"] == []

    approved = client.post(
        "/api/v1/postbacks/mock",
        json={**conversion_payload, "status": "APPROVED"},
    )
    assert approved.status_code == 202
    notifications = client.get("/api/v1/notifications").json()
    assert notifications["unread_count"] == 1
    assert notifications["items"][0]["status"] == "APPROVED"
    assert notifications["items"][0]["title"] == "Reward approved"

    notification_id = notifications["items"][0]["id"]
    read = client.post(f"/api/v1/notifications/{notification_id}/read")
    assert read.status_code == 200
    assert read.json()["read_at"] is not None
    assert client.get("/api/v1/notifications").json()["unread_count"] == 0

    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        rows = db.scalars(select(RewardNotification)).all()
        assert len(rows) == 1
        assert rows[0].reason is None
    finally:
        db.close()


def test_reversal_notification_contains_review_reason(client, monkeypatch):
    from app.core.config import settings
    from app.database.session import SessionLocal
    from app.models import RewardDecision
    from app.services.rewards import reward_decision_service

    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    activate_package(client, "TESTNOTIF002")
    click = client.post("/api/v1/offers/mock-game/click").json()
    response = client.post(
        "/api/v1/postbacks/mock",
        json={
            "transaction_id": "notification-reward-2",
            "click_id": click["click_id"],
            "offer_id": "mock-game",
            "payout": "2.00",
            "currency": "USD",
            "status": "APPROVED",
        },
    )
    assert response.status_code == 202

    db = SessionLocal()
    try:
        decision = db.scalar(select(RewardDecision))
        assert decision is not None
        reward_decision_service.transition_decision(
            db, decision, "REVERSED", "Provider reported a duplicate completion."
        )
    finally:
        db.close()

    notifications = client.get("/api/v1/notifications").json()
    assert notifications["unread_count"] == 2
    reversal = next(item for item in notifications["items"] if item["status"] == "REVERSED")
    assert reversal["reason"] == "Provider reported a duplicate completion."
