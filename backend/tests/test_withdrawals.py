import base64
from decimal import Decimal

from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.rate_limit import _hits
from conftest import activate_package, configure_payout_rate, security_codes


def login(client, email="workbit-user@example.com"):
    route = "/api/v1/auth/admin/login" if email == "workbit-admin@example.com" else "/api/v1/auth/login"
    return client.post(
        route,
        json={"email": email, "password": "WorkBitDev123!"},
    )


def fund_wallet(client, transaction_id="withdrawal-test"):
    _hits.clear()
    activate_package(client, f"TESTWITHDRAWAL{transaction_id}"[:120])
    configure_payout_rate(client)
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


def add_payout_account(client, method, destination, account_id=None):
    _hits.clear()
    payload = {"method": method, "destination": destination}
    if account_id:
        payload["account_id"] = account_id
    code_response = client.post("/api/v1/wallet/payout-accounts/otp", json=payload)
    if code_response.status_code != 202:
        return code_response
    code = security_codes[-1][1]
    return client.post(
        "/api/v1/wallet/payout-accounts",
        json={**payload, "code": code},
    )


def remove_payout_account(client, account_id):
    _hits.clear()
    sent = client.post(f"/api/v1/wallet/payout-accounts/{account_id}/otp")
    if sent.status_code != 202:
        return sent
    return client.request(
        "DELETE",
        f"/api/v1/wallet/payout-accounts/{account_id}",
        json={"code": security_codes[-1][1]},
    )


def request_withdrawal(client, amount, method="BKASH", destination="01712345678"):
    accounts = client.get("/api/v1/wallet/payout-accounts").json()
    existing = next((account for account in accounts if account["method"] == method), None)
    saved = add_payout_account(
        client,
        method,
        destination,
        existing["id"] if existing else None,
    )
    if saved.status_code != 200:
        return saved
    _hits.clear()
    code_request = client.post(
        "/api/v1/withdrawals/otp",
        json={"amount": amount, "account_id": saved.json()["id"]},
    )
    if code_request.status_code != 202:
        return code_request
    code = security_codes[-1][1]
    return client.post(
        "/api/v1/withdrawals",
        json={
            "amount": amount,
            "account_id": saved.json()["id"],
            "payment_method": method,
            "code": code,
        },
    )


def test_withdrawals_require_configuration_and_are_private(client, monkeypatch):
    login(client)
    assert client.get("/api/v1/withdrawals").status_code == 200
    response = request_withdrawal(client, "5.00")
    assert response.status_code == 503
    monkeypatch.setattr(settings, "withdrawal_encryption_key", "not-valid-base64")
    invalid_key = request_withdrawal(client, "5.00")
    assert invalid_key.status_code == 503
    assert client.get("/api/v1/dashboard").json()["withdrawal_summary"]["enabled"] is False
    assert client.get("/api/v1/admin/withdrawals").status_code == 401


def test_users_can_save_update_and_remove_encrypted_payout_accounts(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"a" * 32).decode("ascii"),
    )
    assert login(client).status_code == 200

    saved = add_payout_account(client, "BKASH", "+880 1712-345678")
    assert saved.status_code == 200
    assert saved.json()["method"] == "BKASH"
    assert saved.json()["destination_hint"].endswith("5678")

    updated = add_payout_account(client, "NAGAD", "01812345678")
    assert updated.status_code == 200
    accounts = client.get("/api/v1/wallet/payout-accounts")
    assert accounts.status_code == 200
    assert {account["method"] for account in accounts.json()} == {"BKASH", "NAGAD"}
    assert "destination_ciphertext" not in str(accounts.json())
    assert "01712345678" not in str(accounts.json())

    from app.database.session import SessionLocal
    from app.models import UserPayoutAccount

    db = SessionLocal()
    try:
        account = db.query(UserPayoutAccount).filter_by(method="BKASH").one()
        assert account.destination_ciphertext != "01712345678"
        assert account.destination_hint.endswith("5678")
    finally:
        db.close()

    removed = remove_payout_account(client, saved.json()["id"])
    assert removed.status_code == 204
    assert [account["method"] for account in client.get("/api/v1/wallet/payout-accounts").json()] == ["NAGAD"]


def test_removing_payout_account_requires_matching_one_time_email_code(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"e" * 32).decode("ascii"),
    )
    assert login(client).status_code == 200
    saved = add_payout_account(client, "BKASH", "01712345678")
    assert saved.status_code == 200
    other = add_payout_account(client, "NAGAD", "01812345678")
    assert other.status_code == 200
    account_id = saved.json()["id"]

    direct_delete = client.request(
        "DELETE",
        f"/api/v1/wallet/payout-accounts/{account_id}",
        json={"code": "123456"},
    )
    assert direct_delete.status_code == 400
    assert len(client.get("/api/v1/wallet/payout-accounts").json()) == 2

    _hits.clear()
    issued = client.post(f"/api/v1/wallet/payout-accounts/{account_id}/otp")
    assert issued.status_code == 202
    recipient, code, action = security_codes[-1]
    assert recipient == "workbit-user@example.com"
    assert action == "payout account removal"

    mismatched_account = client.request(
        "DELETE",
        f"/api/v1/wallet/payout-accounts/{other.json()['id']}",
        json={"code": code},
    )
    assert mismatched_account.status_code == 400
    assert len(client.get("/api/v1/wallet/payout-accounts").json()) == 2

    wrong = client.request(
        "DELETE",
        f"/api/v1/wallet/payout-accounts/{account_id}",
        json={"code": "000000" if code != "000000" else "000001"},
    )
    assert wrong.status_code == 400
    assert len(client.get("/api/v1/wallet/payout-accounts").json()) == 2

    removed = client.request(
        "DELETE",
        f"/api/v1/wallet/payout-accounts/{account_id}",
        json={"code": code},
    )
    assert removed.status_code == 204
    assert [item["id"] for item in client.get("/api/v1/wallet/payout-accounts").json()] == [other.json()["id"]]
    reused = client.request(
        "DELETE",
        f"/api/v1/wallet/payout-accounts/{account_id}",
        json={"code": code},
    )
    assert reused.status_code == 404


def test_users_can_save_two_accounts_per_method_but_not_a_third(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"c" * 32).decode("ascii"),
    )
    assert login(client).status_code == 200
    assert add_payout_account(client, "BKASH", "01712345678").status_code == 200
    assert add_payout_account(client, "BKASH", "01812345678").status_code == 200
    assert add_payout_account(client, "BKASH", "01912345678").status_code == 409
    assert add_payout_account(client, "NAGAD", "01612345678").status_code == 200
    assert add_payout_account(client, "NAGAD", "01512345678").status_code == 200
    accounts = client.get("/api/v1/wallet/payout-accounts").json()
    assert len(accounts) == 4
    assert sum(item["method"] == "BKASH" for item in accounts) == 2
    assert sum(item["method"] == "NAGAD" for item in accounts) == 2


def test_payout_account_requires_matching_one_time_email_code(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"d" * 32).decode("ascii"),
    )
    assert login(client).status_code == 200
    _hits.clear()
    payload = {"method": "BKASH", "destination": "01712345678"}
    issued = client.post("/api/v1/wallet/payout-accounts/otp", json=payload)
    assert issued.status_code == 202
    recipient, code, action = security_codes[-1]
    assert recipient == "workbit-user@example.com"
    assert action == "payout account change"

    wrong = client.post(
        "/api/v1/wallet/payout-accounts",
        json={**payload, "code": "000000" if code != "000000" else "000001"},
    )
    assert wrong.status_code == 400
    assert client.get("/api/v1/wallet/payout-accounts").json() == []

    mismatch = client.post(
        "/api/v1/wallet/payout-accounts",
        json={"method": "BKASH", "destination": "01812345678", "code": code},
    )
    assert mismatch.status_code == 400
    saved = client.post(
        "/api/v1/wallet/payout-accounts",
        json={**payload, "code": code},
    )
    assert saved.status_code == 200
    reused = client.post(
        "/api/v1/wallet/payout-accounts",
        json={**payload, "code": code},
    )
    assert reused.status_code == 400


def test_withdrawal_uses_saved_number_and_admin_can_review_it(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"s" * 32).decode("ascii"),
    )
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    fund_wallet(client, "withdrawal-saved-payout-account")
    saved = add_payout_account(client, "NAGAD", "01812345678")
    assert saved.status_code == 200

    created = request_withdrawal(client, "5.00", "NAGAD", "01812345678")
    assert created.status_code == 201
    assert created.json()["method"] == "NAGAD"
    assert created.json()["destination_hint"].endswith("5678")
    assert "01812345678" not in str(created.json())

    with TestClient(client.app) as admin:
        assert login(admin, "workbit-admin@example.com").status_code == 200
        detail = admin.get(f"/api/v1/admin/withdrawals/{created.json()['id']}")
        assert detail.status_code == 200
        assert detail.json()["destination"] == "01812345678"


def test_withdrawal_otp_is_bound_to_amount_and_does_not_reserve_balance_early(client, monkeypatch):
        monkeypatch.setattr(
            settings,
            "withdrawal_encryption_key",
            base64.urlsafe_b64encode(b"e" * 32).decode("ascii"),
        )
        monkeypatch.setattr(settings, "enable_mock_rewards", True)
        fund_wallet(client, "withdrawal-otp-binding")
        saved = add_payout_account(client, "BKASH", "01712345678")
        assert saved.status_code == 200

        _hits.clear()
        issued = client.post(
            "/api/v1/withdrawals/otp",
            json={"amount": "5.00", "account_id": saved.json()["id"]},
        )
        assert issued.status_code == 202
        code = security_codes[-1][1]
        before = client.get("/api/v1/wallet").json()["available_balance"]
        wrong = client.post(
            "/api/v1/withdrawals",
            json={
                "amount": "5.00",
                "account_id": saved.json()["id"],
                "payment_method": "BKASH",
                "code": "000000" if code != "000000" else "000001",
            },
        )
        assert wrong.status_code == 400
        mismatch = client.post(
            "/api/v1/withdrawals",
            json={
                "amount": "6.00",
                "account_id": saved.json()["id"],
                "payment_method": "BKASH",
                "code": code,
            },
        )
        assert mismatch.status_code == 400
        assert client.get("/api/v1/wallet").json()["available_balance"] == before

        _hits.clear()
        issued = client.post(
            "/api/v1/withdrawals/otp",
            json={"amount": "5.00", "account_id": saved.json()["id"]},
        )
        assert issued.status_code == 202
        code = security_codes[-1][1]
        created = client.post(
            "/api/v1/withdrawals",
            json={
                "amount": "5.00",
                "account_id": saved.json()["id"],
                "payment_method": "BKASH",
                "code": code,
            },
        )
        assert created.status_code == 201
        assert client.get("/api/v1/wallet").json()["available_balance"] == "3.00000000"


def test_withdrawal_reserves_funds_and_admin_approval_marks_paid(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"w" * 32).decode("ascii"),
    )
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    fund_wallet(client, "withdrawal-complete-test")

    before = client.get("/api/v1/wallet").json()
    assert before["available_balance"] == "8.00000000"
    response = request_withdrawal(client, "5.00")
    assert response.status_code == 201
    request_data = response.json()
    assert request_data["status"] == "PENDING"
    assert request_data["destination_hint"].endswith("5678")
    assert request_data["method"] == "BKASH"
    assert request_data["payout_currency"] == "BDT"
    assert request_data["payout_amount"] == "600.00000000"
    assert request_data["exchange_rate"] == "120.00000000"
    assert "destination" not in request_data
    assert "01712345678" not in str(request_data)

    wallet = client.get("/api/v1/wallet").json()
    assert wallet["available_balance"] == "3.00000000"
    duplicate = request_withdrawal(client, "5.00")
    assert duplicate.status_code == 409
    history = client.get("/api/v1/withdrawals").json()
    assert len(history) == 1
    assert "destination" not in history[0]

    with TestClient(client.app) as admin:
        assert login(admin, "workbit-admin@example.com").status_code == 200
        detail = admin.get(f"/api/v1/admin/withdrawals/{request_data['id']}")
        assert detail.status_code == 200
        assert detail.json()["destination"] == "01712345678"
        paid = admin.post(
            f"/api/v1/admin/withdrawals/{request_data['id']}/approve",
            json={"note": "Payout verified."},
        )
        assert paid.status_code == 200
        assert paid.json()["status"] == "PAID"
        assert paid.json()["payment_transaction_id"] is None
        assert paid.json()["paid_at"] is not None

    wallet = client.get("/api/v1/wallet").json()
    assert wallet["available_balance"] == "3.00000000"
    assert wallet["lifetime_withdrawn"] == "5.00000000"
    user_history = client.get("/api/v1/withdrawals").json()
    assert user_history[0]["status"] == "PAID"
    transactions = client.get("/api/v1/wallet/transactions").json()
    reserved = next(item for item in transactions if item["reference_id"] == request_data["id"])
    assert reserved["status"] == "APPROVED"


def test_admin_approval_marks_withdrawal_paid_without_separate_completion_step(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"p" * 32).decode("ascii"),
    )
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    fund_wallet(client, "withdrawal-missing-payment-reference")
    created = request_withdrawal(client, "5.00")
    assert created.status_code == 201

    with TestClient(client.app) as admin:
        assert login(admin, "workbit-admin@example.com").status_code == 200
        withdrawal_id = created.json()["id"]
        paid = admin.post(
            f"/api/v1/admin/withdrawals/{withdrawal_id}/approve",
            json={"note": "Payout sent."},
        )
        assert paid.status_code == 200
        assert paid.json()["status"] == "PAID"
        assert paid.json()["paid_at"] is not None


def test_rejected_withdrawal_releases_balance_and_enforces_minimum(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"r" * 32).decode("ascii"),
    )
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    fund_wallet(client, "withdrawal-reject-test")
    invalid = request_withdrawal(client, "4.99")
    assert invalid.status_code == 400

    response = request_withdrawal(client, "5.00")
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
    assert wallet["available_balance"] == "8.00000000"
    assert wallet["lifetime_withdrawn"] == "0E-8"
    transactions = client.get("/api/v1/wallet/transactions").json()
    reserved = next(
        item for item in transactions
        if item["reference_id"] == response.json()["id"] and item["type"] == "WITHDRAWAL_REQUEST"
    )
    assert reserved["status"] == "APPROVED"
    released = next(item for item in transactions if item["type"] == "WITHDRAWAL_RELEASE")
    assert released["status"] == "APPROVED"


def test_payout_exchange_rate_is_admin_configurable_and_snapshotted(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"r" * 32).decode("ascii"),
    )
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    fund_wallet(client, "withdrawal-rate-snapshot")

    summary = client.get("/api/v1/dashboard").json()
    assert summary["withdrawal_summary"]["enabled"] is True
    assert summary["withdrawal_summary"]["usd_bdt_rate"] == "120.00000000"
    assert summary["withdrawal_summary"]["minimum_amount"] == "5.00000000"

    invalid_number = client.post(
        "/api/v1/wallet/payout-accounts/otp",
        json={"method": "NAGAD", "destination": "01234567890"},
    )
    assert invalid_number.status_code == 422

    created = request_withdrawal(client, "5.00", "NAGAD", "+8801712345678")
    assert created.status_code == 201
    assert created.json()["destination_hint"].endswith("5678")
    assert created.json()["payout_amount"] == "600.00000000"

    from app.database.session import SessionLocal
    from app.models import PayoutSettings

    db = SessionLocal()
    try:
        rate = db.get(PayoutSettings, "default")
        assert rate is not None and rate.usd_bdt_rate == Decimal("120.00")
    finally:
        db.close()


def test_withdrawal_rate_must_be_configured_and_is_admin_only(client):
    assert login(client).status_code == 200
    assert client.get("/api/v1/admin/payout-settings").status_code == 401
    assert client.put(
        "/api/v1/admin/payout-settings",
        json={"usd_bdt_rate": "120.00"},
    ).status_code == 401
    assert client.get("/api/v1/dashboard").json()["withdrawal_summary"]["enabled"] is False


def test_withdrawal_minimum_is_enforced_by_backend(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"m" * 32).decode("ascii"),
    )
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    fund_wallet(client, "withdrawal-minimum-check")
    response = request_withdrawal(client, "4.99")
    assert response.status_code == 400


def test_admin_manages_withdrawal_minimum_in_database(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "withdrawal_encryption_key",
        base64.urlsafe_b64encode(b"n" * 32).decode("ascii"),
    )
    monkeypatch.setattr(settings, "enable_mock_rewards", True)
    assert login(client, "workbit-admin@example.com").status_code == 200

    updated = client.put(
        "/api/v1/admin/payout-settings",
        json={"usd_bdt_rate": "120.00", "minimum_withdrawal_usd": "7.50"},
    )
    assert updated.status_code == 200
    assert updated.json()["minimum_withdrawal_usd"] == "7.50000000"
    retrieved = client.get("/api/v1/admin/payout-settings")
    assert retrieved.status_code == 200
    assert retrieved.json()["minimum_withdrawal_usd"] == "7.50000000"

    legacy_update = client.put(
        "/api/v1/admin/payout-settings",
        json={"usd_bdt_rate": "121.00"},
    )
    assert legacy_update.status_code == 200
    assert legacy_update.json()["minimum_withdrawal_usd"] == "7.50000000"

    assert login(client).status_code == 200
    fund_wallet(client, "db-withdrawal-minimum")
    summary = client.get("/api/v1/dashboard")
    assert summary.status_code == 200
    assert summary.json()["withdrawal_summary"]["minimum_amount"] == "7.50000000"

    too_small = request_withdrawal(client, "5.00")
    assert too_small.status_code == 400
    assert too_small.json()["error"]["message"] == "The minimum request is 7.50000000 USD."

    from app.database.session import SessionLocal
    from app.models import PayoutSettings

    db = SessionLocal()
    try:
        settings_row = db.get(PayoutSettings, "default")
        assert settings_row is not None
        assert settings_row.minimum_withdrawal_usd == Decimal("7.50000000")
    finally:
        db.close()
