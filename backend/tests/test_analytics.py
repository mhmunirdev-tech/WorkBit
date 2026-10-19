from uuid import uuid4

from app.services.rate_limit import _hits


def test_page_views_are_anonymous_deduplicated_and_visible_to_admin(client):
    visitor_id = str(uuid4())
    first = client.post(
        "/api/v1/analytics/page-view",
        json={"visitor_id": visitor_id, "path": "/packages"},
    )
    duplicate = client.post(
        "/api/v1/analytics/page-view",
        json={"visitor_id": visitor_id, "path": "/packages"},
    )
    another_page = client.post(
        "/api/v1/analytics/page-view",
        json={"visitor_id": visitor_id, "path": "/"},
    )
    heartbeat = client.post(
        "/api/v1/analytics/page-view",
        json={"visitor_id": visitor_id, "path": "/", "event_type": "VISITOR_PING"},
    )

    assert first.status_code == 202
    assert duplicate.status_code == 202
    assert another_page.status_code == 202
    assert heartbeat.status_code == 202
    assert client.get("/api/v1/analytics/admin").status_code == 401

    admin_login = client.post(
        "/api/v1/auth/admin/login",
        json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"},
    )
    assert admin_login.status_code == 200
    analytics = client.get("/api/v1/analytics/admin")

    assert analytics.status_code == 200
    assert analytics.json()["active_visitors"] == 1
    assert analytics.json()["unique_visitors_today"] == 1
    assert analytics.json()["page_views_today"] == 2
    assert len(analytics.json()["daily"]) == 90

    from app.database.session import SessionLocal
    from app.models import AnalyticsEvent

    db = SessionLocal()
    try:
        events = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type.in_(("PAGE_VIEW", "VISITOR_PING"))
        ).all()
        assert len(events) == 3
        assert all(event.visitor_hash != visitor_id for event in events)
        assert all(event.ip_hash and len(event.ip_hash) == 64 for event in events)
    finally:
        db.close()


def test_failed_logins_are_logged_with_masked_email_and_hashed_ip(client):
    failed = client.post(
        "/api/v1/auth/login",
        json={"email": "private.person@example.com", "password": "wrong-password"},
    )
    assert failed.status_code == 401

    admin_login = client.post(
        "/api/v1/auth/admin/login",
        json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"},
    )
    assert admin_login.status_code == 200
    analytics = client.get("/api/v1/analytics/admin")

    assert analytics.status_code == 200
    assert analytics.json()["failed_logins_24h"] == 1
    assert analytics.json()["daily"][-1]["failed_logins"] == 1
    recent = analytics.json()["recent_failed_logins"]
    assert len(recent) == 1
    assert recent[0]["login_type"] == "user"
    assert recent[0]["email_masked"] == "p***@example.com"
    assert len(recent[0]["ip_fingerprint"]) == 12
    assert "private.person@example.com" not in str(analytics.json())

    from app.database.session import SessionLocal
    from app.models import AnalyticsEvent

    db = SessionLocal()
    try:
        event = db.query(AnalyticsEvent).filter_by(event_type="LOGIN_FAILURE").one()
        assert event.email_masked == "p***@example.com"
        assert event.ip_hash and len(event.ip_hash) == 64
        assert event.ip_hash != "testclient"
    finally:
        db.close()


def test_non_admin_cannot_read_security_analytics(client):
    _hits.clear()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"},
    )
    assert login.status_code == 200

    response = client.get("/api/v1/analytics/admin")

    assert response.status_code == 401


def test_page_view_rejects_invalid_paths_and_event_types(client):
    visitor_id = str(uuid4())
    for path in ("https://example.com", "//example.com", "/packages?email=person@example.com"):
        response = client.post(
            "/api/v1/analytics/page-view",
            json={"visitor_id": visitor_id, "path": path},
        )
        assert response.status_code == 422
    invalid_type = client.post(
        "/api/v1/analytics/page-view",
        json={"visitor_id": visitor_id, "path": "/", "event_type": "LOGIN_SUCCESS"},
    )
    assert invalid_type.status_code == 422


def test_analytics_events_older_than_ninety_days_are_purged(client):
    from datetime import datetime, timedelta, timezone

    from app.database.session import SessionLocal
    from app.models import AnalyticsEvent

    db = SessionLocal()
    try:
        db.add(
            AnalyticsEvent(
                event_type="LOGIN_FAILURE",
                login_type="user",
                email_masked="o***@example.com",
                created_at=datetime.now(timezone.utc) - timedelta(days=91),
            )
        )
        db.commit()
    finally:
        db.close()

    assert client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-admin@example.com", "password": "wrong-password"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/admin/login",
        json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"},
    ).status_code == 200
    assert client.get("/api/v1/analytics/admin").status_code == 200

    db = SessionLocal()
    try:
        assert db.query(AnalyticsEvent).filter_by(email_masked="o***@example.com").count() == 0
    finally:
        db.close()
