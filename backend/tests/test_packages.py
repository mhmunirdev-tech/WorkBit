from decimal import Decimal

from conftest import activate_package, configure_payout_rate


def login(client, email="workbit-user@example.com"):
    route = "/api/v1/auth/admin/login" if email == "workbit-admin@example.com" else "/api/v1/auth/login"
    return client.post(route, json={"email": email, "password": "WorkBitDev123!"})


def test_package_catalog_shows_prices_and_configured_mobile_payment_numbers(client):
    assert login(client).status_code == 200
    response = client.get("/api/v1/packages")

    assert response.status_code == 200
    catalog = response.json()
    assert [(item["code"], item["amount"]) for item in catalog["packages"]] == [
        ("BASIC", "10.00"),
        ("STANDARD", "50.00"),
        ("PREMIUM", "100.00"),
        ("VIP", "550.00"),
        ("VIP_PRO", "1000.00"),
        ("FOUNDER", "500.00"),
    ]
    assert catalog["payment_instructions"] == {
        "BKASH": "01839299096",
        "NAGAD": "01811914794",
    }
    assert catalog["package_active"] is False
    assert catalog["packages"][0]["payment_amount_bdt"] is None
    assert [(item["code"], item["duration_days"]) for item in catalog["packages"]] == [
        ("BASIC", 365),
        ("STANDARD", 730),
        ("PREMIUM", 1095),
        ("VIP", 1095),
        ("VIP_PRO", 1825),
        ("FOUNDER", 3650),
    ]


def test_public_package_catalog_shows_current_plans_without_login(client):
    response = client.get("/api/v1/public/packages")

    assert response.status_code == 200
    assert [
        (item["code"], item["name"], item["amount"], item["currency"], item["duration_days"])
        for item in response.json()
    ] == [
        ("BASIC", "Basic", "10.00", "USD", 365),
        ("STANDARD", "Standard", "50.00", "USD", 730),
        ("PREMIUM", "Premium", "100.00", "USD", 1095),
        ("VIP", "VIP", "550.00", "USD", 1095),
        ("VIP_PRO", "VIP Pro", "1000.00", "USD", 1825),
        ("FOUNDER", "Founder", "500.00", "USD", 3650),
    ]


def test_admin_can_edit_catalog_and_purchase_keeps_original_terms(client):
    assert client.get("/api/v1/admin/packages").status_code == 401
    assert login(client).status_code == 200
    assert client.get("/api/v1/admin/packages").status_code == 401
    configure_payout_rate(client)

    purchase = client.post(
        "/api/v1/package-purchases",
        json={
            "package_code": "BASIC",
            "payment_method": "BKASH",
            "payment_reference": "BASIC-SNAPSHOT-001",
        },
    )
    assert purchase.status_code == 201
    assert Decimal(purchase.json()["amount"]) == Decimal("10.00")
    assert Decimal(purchase.json()["payment_amount_bdt"]) == Decimal("1200.00")
    assert Decimal(purchase.json()["usd_bdt_rate"]) == Decimal("120.00")
    assert purchase.json()["duration_days"] == 365

    assert login(client, "workbit-admin@example.com").status_code == 200
    catalog = client.get("/api/v1/admin/packages")
    assert catalog.status_code == 200
    assert len(catalog.json()) == 6
    updated = client.put(
        "/api/v1/admin/packages/BASIC",
        json={
            "name": "Basic Plus",
            "description": "Updated plan details",
            "amount": "99.00",
            "duration_days": 30,
            "is_active": False,
            "sort_order": 5,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Basic Plus"
    assert updated.json()["amount"] == "99.00"
    assert updated.json()["duration_days"] == 30
    assert "BASIC" not in {
        item["code"] for item in client.get("/api/v1/public/packages").json()
    }
    assert client.put("/api/v1/admin/packages/UNKNOWN", json=updated.json()).status_code == 404

    approved = client.post(
        f"/api/v1/admin/package-purchases/{purchase.json()['id']}/approve",
        json={"note": "Original payment verified."},
    )
    assert approved.status_code == 200
    assert approved.json()["package_name"] == "Basic"
    assert Decimal(approved.json()["amount"]) == Decimal("10.00")
    assert approved.json()["duration_days"] == 365
    assert approved.json()["expires_at"] is not None

    expiry = approved.json()["expires_at"]
    assert login(client, "workbit-admin@example.com").status_code == 200
    later_update = client.put(
        "/api/v1/admin/packages/BASIC",
        json={
            "name": "Basic Renewed",
            "description": "New catalog terms",
            "amount": "120.00",
            "duration_days": 60,
            "is_active": False,
            "sort_order": 5,
        },
    )
    assert later_update.status_code == 200
    assert login(client).status_code == 200
    assert client.get("/api/v1/packages").json()["latest_purchase"]["expires_at"] == expiry
    hidden_purchase = client.post(
        "/api/v1/package-purchases",
        json={
            "package_code": "BASIC",
            "payment_method": "NAGAD",
            "payment_reference": "HIDDEN-PACKAGE-001",
        },
    )
    assert hidden_purchase.status_code == 404


def test_pending_package_does_not_unlock_ads_until_admin_approval(client):
    assert login(client).status_code == 200
    configure_payout_rate(client)
    dashboard = client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["package_active"] is False
    assert dashboard.json()["package_purchase_status"] is None

    purchase = client.post(
        "/api/v1/package-purchases",
        json={
            "package_code": "STANDARD",
            "payment_method": "NAGAD",
            "payment_reference": "NAGAD-TRANSACTION-001",
        },
    )
    assert purchase.status_code == 201
    assert Decimal(purchase.json()["amount"]) == Decimal("50.00")
    assert purchase.json()["duration_days"] == 730
    assert purchase.json()["status"] == "PENDING"
    assert client.post("/api/v1/offers/mock-game/click").status_code == 402
    pending_dashboard = client.get("/api/v1/dashboard")
    assert pending_dashboard.json()["package_active"] is False
    assert pending_dashboard.json()["package_purchase_status"] == "PENDING"

    admin = client
    assert login(admin, "workbit-admin@example.com").status_code == 200
    purchases = admin.get("/api/v1/admin/package-purchases")
    assert purchases.status_code == 200
    assert purchases.json()[0]["user_email"] == "workbit-user@example.com"
    approved = admin.post(
        f"/api/v1/admin/package-purchases/{purchase.json()['id']}/approve",
        json={"note": "Payment reference verified."},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["starts_at"] is not None
    assert approved.json()["expires_at"] is not None
    assert admin.get("/api/v1/admin/dashboard").json()["registered_user_amount"] == "50.00000000"

    assert login(admin).status_code == 200
    assert admin.get("/api/v1/packages").json()["package_active"] is True
    assert admin.get("/api/v1/dashboard").json()["package_active"] is True
    assert admin.post("/api/v1/offers/mock-game/click").status_code == 202


def test_package_purchase_rejects_duplicate_reference_and_pending_request(client):
    assert login(client).status_code == 200
    configure_payout_rate(client)
    purchase = client.post(
        "/api/v1/package-purchases",
        json={
            "package_code": "BASIC",
            "payment_method": "BKASH",
            "payment_reference": "DUPLICATE-PAY-001",
        },
    )
    assert purchase.status_code == 201
    pending = client.post(
        "/api/v1/package-purchases",
        json={
            "package_code": "STANDARD",
            "payment_method": "NAGAD",
            "payment_reference": "SECOND-PENDING-001",
        },
    )
    assert pending.status_code == 409
    duplicate_reference = client.post(
        "/api/v1/package-purchases",
        json={
            "package_code": "STANDARD",
            "payment_method": "BKASH",
            "payment_reference": "DUPLICATE-PAY-001",
        },
    )
    assert duplicate_reference.status_code == 409


def test_rejected_package_does_not_count_as_admin_revenue_or_unlock_ads(client):
    assert login(client).status_code == 200
    configure_payout_rate(client)
    purchase = client.post(
        "/api/v1/package-purchases",
        json={
            "package_code": "BASIC",
            "payment_method": "BKASH",
            "payment_reference": "REJECTED-PAY-001",
        },
    )
    assert purchase.status_code == 201
    assert login(client, "workbit-admin@example.com").status_code == 200
    rejected = client.post(
        f"/api/v1/admin/package-purchases/{purchase.json()['id']}/reject",
        json={"note": "Payment not received."},
    )
    assert rejected.status_code == 200
    dashboard = client.get("/api/v1/admin/dashboard")
    assert dashboard.status_code == 200
    assert Decimal(dashboard.json()["registered_user_amount"]) == Decimal("0")
    assert login(client).status_code == 200
    assert client.post("/api/v1/offers/mock-game/click").status_code == 402


def test_package_routes_require_admin_permissions(client):
    assert client.get("/api/v1/admin/package-purchases").status_code == 401
    assert login(client).status_code == 200
    assert client.get("/api/v1/admin/package-purchases").status_code == 401


def test_standalone_deposits_and_wallet_package_purchases_are_retired(client):
    assert login(client).status_code == 200
    standalone_deposit = client.post(
        "/api/v1/deposits",
        json={
            "amount_bdt": "1200.00",
            "payment_method": "BKASH",
            "payment_reference": "WALLET-DEPOSIT-001",
        },
    )
    assert standalone_deposit.status_code == 410
    assert "Choose a package" in standalone_deposit.json()["error"]["message"]
    assert client.get("/api/v1/wallet").json()["available_balance"] == "0E-8"

    purchase = client.post(
        "/api/v1/package-purchases/wallet",
        json={"package_code": "BASIC"},
    )
    assert purchase.status_code == 410
    assert "manual payment" in purchase.json()["error"]["message"]


def test_deposit_is_blocked_while_package_is_active_and_reference_cannot_be_reused(client):
    activate_package(client, "ACTIVE-PACKAGE-DEPOSIT-001")
    response = client.post(
        "/api/v1/deposits",
        json={
            "amount_bdt": "1200.00",
            "payment_method": "BKASH",
            "payment_reference": "ACTIVE-DEPOSIT-001",
        },
    )
    assert response.status_code == 410


def test_package_purchase_requires_configured_rate_and_snapshots_amount(client):
    assert login(client).status_code == 200
    data = {
        "package_code": "BASIC",
        "payment_method": "NAGAD",
        "payment_reference": "PACKAGE-FX-SNAPSHOT-001",
    }
    unavailable = client.post("/api/v1/package-purchases", json=data)
    assert unavailable.status_code == 503

    configure_payout_rate(client, "125.50")
    catalog = client.get("/api/v1/packages").json()
    assert Decimal(catalog["packages"][0]["payment_amount_bdt"]) == Decimal("1255.00")
    purchase = client.post("/api/v1/package-purchases", json=data)
    assert purchase.status_code == 201
    assert Decimal(purchase.json()["payment_amount_bdt"]) == Decimal("1255.00")
    assert Decimal(purchase.json()["usd_bdt_rate"]) == Decimal("125.50")


def test_package_payment_reference_cannot_be_reused(client):
    assert login(client).status_code == 200
    configure_payout_rate(client)
    first = client.post(
        "/api/v1/package-purchases",
        json={
            "package_code": "BASIC",
            "payment_method": "NAGAD",
            "payment_reference": "CROSS-FLOW-REF-001",
        },
    )
    assert first.status_code == 201
    duplicate = client.post(
        "/api/v1/package-purchases",
        json={
            "package_code": "STANDARD",
            "payment_method": "NAGAD",
            "payment_reference": "CROSS-FLOW-REF-001",
        },
    )
    assert duplicate.status_code == 409
