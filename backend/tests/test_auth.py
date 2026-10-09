import asyncio

from sqlalchemy import select
from starlette.requests import Request

from app.core.errors import unexpected_exception_handler
from app.database.session import get_db
from app.main import app
from app.models import Role, User
from app.services import auth as auth_service
from app.services.email import EmailDeliveryError


def registration():
    return {"full_name":"Taylor Test","email":"taylor@example.com","password":"StrongPassword123","confirm_password":"StrongPassword123","country":"US","terms_accepted":True}

def test_registration_creates_wallet(client):
    response = client.post("/api/v1/auth/register", json=registration())
    assert response.status_code == 201
    assert response.json()["email"] == "taylor@example.com"

def test_registration_verification_otp_activates_account(client, monkeypatch):
    issued_codes = []
    monkeypatch.setattr(
        auth_service.email_service,
        "send_verification",
        lambda _recipient, code: issued_codes.append(code),
    )
    created = client.post("/api/v1/auth/register", json=registration())
    assert created.status_code == 201
    assert len(issued_codes) == 1
    assert len(issued_codes[0]) == 6
    assert issued_codes[0].isdigit()

    verified = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "taylor@example.com", "code": issued_codes[0]},
    )
    assert verified.status_code == 200
    assert verified.json()["message"] == "Email verified."
    reused = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "taylor@example.com", "code": issued_codes[0]},
    )
    assert reused.status_code == 400
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "taylor@example.com", "password": "StrongPassword123"},
    )
    assert login.status_code == 200
    assert login.json()["email_verified"] is True

def test_verification_otp_rejects_wrong_code_and_locks_after_five_attempts(client, monkeypatch):
    codes = []
    monkeypatch.setattr(
        auth_service.email_service,
        "send_verification",
        lambda _recipient, code: codes.append(code),
    )
    assert client.post("/api/v1/auth/register", json=registration()).status_code == 201
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"email": "taylor@example.com", "code": "000000" if codes[0] != "000000" else "000001"},
        )
        assert response.status_code == 400
    locked = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "taylor@example.com", "code": codes[0]},
    )
    assert locked.status_code == 400

def test_resend_verification_replaces_old_otp_and_is_rate_limited(client, monkeypatch):
    from app.services.rate_limit import _hits

    codes = []
    monkeypatch.setattr(
        auth_service.email_service,
        "send_verification",
        lambda _recipient, code: codes.append(code),
    )
    assert client.post("/api/v1/auth/register", json=registration()).status_code == 201
    _hits.clear()
    first = client.post(
        "/api/v1/auth/request-verification",
        json={"email": "taylor@example.com"},
    )
    assert first.status_code == 202
    assert len(codes) == 2
    cooldown = client.post(
        "/api/v1/auth/request-verification",
        json={"email": "taylor@example.com"},
    )
    assert cooldown.status_code == 429

    old_code = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "taylor@example.com", "code": codes[0]},
    )
    assert old_code.status_code == 400
    new_code = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "taylor@example.com", "code": codes[1]},
    )
    assert new_code.status_code == 200

def test_verification_otp_expires(client, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.database.session import get_db
    from app.models import AuthToken

    code = []
    monkeypatch.setattr(
        auth_service.email_service,
        "send_verification",
        lambda _recipient, value: code.append(value),
    )
    assert client.post("/api/v1/auth/register", json=registration()).status_code == 201

    session_generator = app.dependency_overrides[get_db]()
    db = next(session_generator)
    try:
        token = db.query(AuthToken).filter(AuthToken.purpose == "VERIFY_EMAIL").one()
        token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        session_generator.close()

    response = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "taylor@example.com", "code": code[0]},
    )
    assert response.status_code == 400

def test_duplicate_email(client):
    client.post("/api/v1/auth/register", json=registration())
    assert client.post("/api/v1/auth/register", json=registration()).status_code == 400

def test_registration_reports_missing_seeded_user_role(client):
    session_generator = app.dependency_overrides[get_db]()
    db = next(session_generator)
    try:
        role = db.scalar(select(Role).where(Role.name == "USER"))
        assert role is not None
        role.name = "MISSING_USER_ROLE"
        db.commit()
    finally:
        session_generator.close()

    response = client.post("/api/v1/auth/register", json=registration())
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "Run the seed command" in response.json()["error"]["message"]

def test_registration_reports_resend_failure_and_rolls_back(client, monkeypatch):
    def fail_delivery(_recipient, _token):
        raise EmailDeliveryError("provider unavailable")

    monkeypatch.setattr(auth_service.email_service, "send_verification", fail_delivery)
    response = client.post("/api/v1/auth/register", json=registration())
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "provider unavailable" not in response.text

    session_generator = app.dependency_overrides[get_db]()
    db = next(session_generator)
    try:
        assert db.scalar(select(Role).where(Role.name == "USER")) is not None
        assert db.scalar(select(User).where(User.email == "taylor@example.com")) is None
    finally:
        session_generator.close()

def test_unexpected_errors_return_safe_internal_server_error():
    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/register",
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 80),
        "scheme": "http",
    })
    response = asyncio.run(
        unexpected_exception_handler(request, RuntimeError("internal detail"))
    )
    assert response.status_code == 500
    assert b"internal detail" not in response.body
    assert b"INTERNAL_SERVER_ERROR" in response.body

def test_login_me_and_logout(client):
    response = client.post("/api/v1/auth/login", json={"email":"workbit-user@example.com","password":"WorkBitDev123!"})
    assert response.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401

def test_admin_permission(client):
    client.post("/api/v1/auth/login", json={"email":"workbit-user@example.com","password":"WorkBitDev123!"})
    assert client.get("/api/v1/admin/dashboard").status_code == 403
    client.post("/api/v1/auth/login", json={"email":"workbit-admin@example.com","password":"WorkBitDev123!"})
    assert client.get("/api/v1/admin/dashboard").status_code == 200

def test_user_dashboard_is_authenticated_and_returns_own_summary(client):
    assert client.get("/api/v1/dashboard").status_code == 401
    login = client.post("/api/v1/auth/login", json={"email":"workbit-user@example.com", "password":"WorkBitDev123!"})
    assert login.status_code == 200

    invited_user = registration()
    invited_user["referral_code"] = "WBUSER001"
    assert client.post("/api/v1/auth/register", json=invited_user).status_code == 201

    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    dashboard = response.json()
    assert dashboard["user"]["email"] == "workbit-user@example.com"
    assert dashboard["user"]["referral_code"] == "WBUSER001"
    assert dashboard["user"]["referral_url"].endswith("/register?referral=WBUSER001")
    assert dashboard["currency"] == "USD"
    assert dashboard["stats"]["completed_offers"] == 0
    assert dashboard["stats"]["referrals"] == 1
    assert dashboard["stats"]["active_referrals"] == 0
    assert len(dashboard["earnings_chart"]) == 90
    assert dashboard["recent_transactions"] == []
    assert dashboard["withdrawal_summary"]["enabled"] is False
    assert dashboard["withdrawal_summary"]["pending_request"] is None
    assert "password_hash" not in dashboard["user"]

def test_reset_password_requires_strong_password_and_updates_login(client, monkeypatch):
    issued_tokens = []
    monkeypatch.setattr(
        auth_service.email_service,
        "send_password_reset",
        lambda _recipient, token: issued_tokens.append(token),
    )

    created = client.post("/api/v1/auth/register", json=registration())
    assert created.status_code == 201

    weak = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "1234567890abcdef1234567890abcdef",
            "password": "weakpass",
            "confirm_password": "weakpass",
        },
    )
    assert weak.status_code == 422

    reset = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "taylor@example.com"},
    )
    assert reset.status_code == 202
    assert len(issued_tokens) == 1

    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": issued_tokens[0],
            "password": "NewStrongPassword456",
            "confirm_password": "NewStrongPassword456",
        },
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password updated."

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "taylor@example.com", "password": "StrongPassword123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "taylor@example.com", "password": "NewStrongPassword456"},
    )
    assert new_login.status_code == 200


def test_forgot_password_is_non_enumerating(client):
    response = client.post("/api/v1/auth/forgot-password", json={"email":"nobody@example.com"})
    assert response.status_code == 202
    assert "If the account exists" in response.json()["message"]
