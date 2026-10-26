from decimal import Decimal


def admin_login(client):
    response = client.post(
        "/api/v1/auth/admin/login",
        json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"},
    )
    assert response.status_code == 200


def test_admin_user_registry_excludes_admin_and_returns_wallet_package_fields(client):
    admin_login(client)

    response = client.get("/api/v1/admin/users")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["registered_count"] == 1
    assert payload["active_count"] == 1
    assert payload["pending_verification_count"] == 0
    assert payload["active_package_count"] == 0
    assert payload["items"][0]["email"] == "workbit-user@example.com"
    assert Decimal(payload["items"][0]["available_balance"]) == Decimal("0")
    assert payload["items"][0]["active_package"] is False


def test_admin_dashboard_metrics_are_scoped_to_registered_users(client):
    admin_login(client)

    response = client.get("/api/v1/admin/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_users"] == 1
    assert Decimal(payload["total_wallet_balance"]) == Decimal("0")


def test_admin_user_registry_supports_search_and_status_filters(client):
    admin_login(client)

    assert client.get("/api/v1/admin/users?search=workbit-user").json()["total"] == 1
    assert client.get("/api/v1/admin/users?search=workbit-admin").json()["total"] == 0
    assert client.get("/api/v1/admin/users?status=PENDING_VERIFICATION").json()["total"] == 0
    assert client.get("/api/v1/admin/users?page=0").status_code == 422
