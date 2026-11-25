from decimal import Decimal


def admin_login(client):
    response = client.post(
        "/api/v1/auth/admin/login",
        json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"},
    )
    assert response.status_code == 200


def user_login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"},
    )
    assert response.status_code == 200


def create_product(client, price="1000.00", stock=4):
    category = client.post(
        "/api/v1/admin/marketplace/categories",
        json={
            "name": "Work tools",
            "slug": "work-tools",
            "description": "Useful tools",
            "sort_order": 1,
        },
    )
    assert category.status_code == 201
    product = client.post(
        "/api/v1/admin/marketplace/products",
        json={
            "category_id": category.json()["id"],
            "sku": "TOOL-001",
            "name": "Focus planner",
            "slug": "focus-planner",
            "description": "A simple planner",
            "price": price,
            "stock_quantity": stock,
            "is_active": True,
            "featured": True,
            "sort_order": 1,
        },
    )
    assert product.status_code == 201
    return product.json()


def test_product_affiliate_reward_is_credited_once_after_delivery(client):
    admin_login(client)
    payout_settings = client.put("/api/v1/admin/payout-settings", json={"usd_bdt_rate": "100.00"})
    assert payout_settings.status_code == 200
    product = create_product(client)

    user_login(client)
    link = client.get("/api/v1/marketplace/referral-link", params={"product": product["slug"]})
    assert link.status_code == 200
    assert "ref=WBUSER001" in link.json()["url"]
    added = client.post(
        "/api/v1/marketplace/cart/items",
        json={"product_id": product["id"], "quantity": 2},
    )
    assert added.status_code == 201
    order = client.post(
        "/api/v1/marketplace/orders",
        json={
            "shipping_name": "WorkBit Buyer",
            "shipping_phone": "01700000000",
            "shipping_address": "Dhaka address",
            "shipping_city": "Dhaka",
            "referral_code": "WBADMIN01",
        },
    )
    assert order.status_code == 201
    order_data = order.json()
    assert order_data["affiliate_commission_bdt"] == "100.00"
    assert order_data["affiliate_reward_status"] == "PENDING"

    admin_login(client)
    delivered = None
    for next_status in ("CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED"):
        delivered = client.patch(
            f"/api/v1/admin/marketplace/orders/{order_data['id']}",
            json={"status": next_status},
        )
        assert delivered.status_code == 200
    assert delivered is not None
    assert delivered.json()["affiliate_reward_status"] == "CREDITED"
    assert Decimal(delivered.json()["affiliate_reward_amount"]) == Decimal("1.00")

    duplicate = client.patch(
        f"/api/v1/admin/marketplace/orders/{order_data['id']}",
        json={"status": "DELIVERED"},
    )
    assert duplicate.status_code == 200



def test_self_referral_does_not_create_affiliate_reward(client):
    admin_login(client)
    product = create_product(client, price="100.00", stock=1)
    user_login(client)
    assert client.post(
        "/api/v1/marketplace/cart/items",
        json={"product_id": product["id"], "quantity": 1},
    ).status_code == 201
    order = client.post(
        "/api/v1/marketplace/orders",
        json={
            "shipping_name": "Development User",
            "shipping_phone": "01700000000",
            "shipping_address": "Dhaka address",
            "shipping_city": "Dhaka",
            "referral_code": "WBUSER001",
        },
    )
    assert order.status_code == 201
    assert order.json()["affiliate_referrer_id"] is None
    assert order.json()["affiliate_reward_status"] == "NOT_ELIGIBLE"
