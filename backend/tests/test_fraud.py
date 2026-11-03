from sqlalchemy import select

from app.core.config import settings
from app.models import AdminLog, FraudEvent, User
from app.security.tokens import create_session
from conftest import TestingSession, security_codes


def _register(client, email):
    return client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Fraud Test",
            "email": email,
            "password": "FraudTest123!",
            "confirm_password": "FraudTest123!",
            "country": "BD",
            "terms_accepted": True,
        },
    )


def _admin(client):
    response = client.post(
        "/api/v1/auth/admin/login",
        json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"},
    )
    assert response.status_code == 200


def test_shared_ip_is_recorded_as_signal_without_restricting_accounts(client):
    for suffix in range(3):
        response = _register(client, f"fraud-shared-{suffix}@example.com")
        assert response.status_code == 201

    db = TestingSession()
    try:
        events = db.scalars(
            select(FraudEvent)
            .where(FraudEvent.event_type == "REGISTRATION")
            .order_by(FraudEvent.created_at)
        ).all()
        assert [event.risk_level for event in events] == ["LOW", "LOW", "MEDIUM"]
        assert all(event.status == "OPEN" for event in events)
        assert all(
            db.get(User, event.user_id).status == "PENDING_VERIFICATION"
            for event in events
        )
        assert events[-1].ip_hash
        assert "testclient" not in events[-1].evidence_json
    finally:
        db.close()


def test_repeated_login_failures_are_recorded_and_do_not_suspend_account(client):
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "workbit-user@example.com", "password": "WrongPassword123!"},
        )
        assert response.status_code == 401

    db = TestingSession()
    try:
        events = db.scalars(
            select(FraudEvent)
            .where(FraudEvent.event_type == "LOGIN_FAILURE")
            .order_by(FraudEvent.created_at)
        ).all()
        assert len(events) == 5
        assert events[-1].risk_level == "MEDIUM"
        assert events[-1].user_id is None
        assert db.scalar(
            select(User.status).where(User.email == "workbit-user@example.com")
        ) == "ACTIVE"
    finally:
        db.close()


def test_fraud_review_and_account_restore_are_authorized_and_audited(client):
    assert client.get("/api/v1/admin/fraud/events").status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"},
    ).status_code == 200
    db = TestingSession()
    try:
        user_id = db.scalar(
            select(User.id).where(User.email == "workbit-user@example.com")
        )
    finally:
        db.close()
    client.cookies.set(
        settings.admin_session_cookie_name,
        create_session(user_id),
    )
    assert client.get("/api/v1/admin/fraud/events").status_code == 403
    client.cookies.delete(settings.admin_session_cookie_name)

    _admin(client)
    response = _register(client, "fraud-review@example.com")
    assert response.status_code == 201
    event_id = client.get(
        "/api/v1/admin/fraud/events?risk_level=LOW"
    ).json()[0]["id"]

    review = client.patch(
        f"/api/v1/admin/fraud/events/{event_id}",
        json={"status": "UNDER_REVIEW", "note": "Review registration evidence."},
    )
    assert review.status_code == 200
    assert review.json()["status"] == "UNDER_REVIEW"

    user_id = response.json()["id"]
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "fraud-review@example.com", "password": "FraudTest123!"},
    ).status_code == 200
    suspended = client.post(
        f"/api/v1/admin/fraud/users/{user_id}/status",
        json={"status": "SUSPENDED", "reason": "Manual review requires a temporary hold."},
    )
    assert suspended.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 403

    restored = client.post(
        f"/api/v1/admin/fraud/users/{user_id}/status",
        json={"status": "ACTIVE", "reason": "Review completed; account restored."},
    )
    assert restored.status_code == 409

    db = TestingSession()
    try:
        user = db.get(User, user_id)
        user.email_verified = True
        db.commit()
    finally:
        db.close()

    requested = client.post(
        "/api/v1/fraud/appeals/request-code",
        json={"email": "fraud-review@example.com"},
    )
    assert requested.status_code == 202
    appeal_code = security_codes[-1][1]
    appeal = client.post(
        "/api/v1/fraud/appeals",
        json={
            "email": "fraud-review@example.com",
            "code": appeal_code,
            "statement": "I believe this restriction was applied in error.",
        },
    )
    assert appeal.status_code == 202
    assert client.get("/api/v1/admin/fraud/overview").json()["under_review"] == 2

    restored = client.post(
        f"/api/v1/admin/fraud/users/{user_id}/status",
        json={"status": "ACTIVE", "reason": "Review completed; account restored."},
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "ACTIVE"
    assert client.get("/api/v1/admin/fraud/events").status_code == 200
    db = TestingSession()
    try:
        audit_count = db.scalar(
            select(AdminLog.id).where(
                AdminLog.target_type == "user",
                AdminLog.target_id == user_id,
                AdminLog.action == "FRAUD_ACCOUNT_STATUS_CHANGED",
            )
        )
        assert audit_count
    finally:
        db.close()
