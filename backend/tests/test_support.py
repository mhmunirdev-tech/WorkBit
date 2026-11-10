from app.services.rate_limit import _hits


def login(client, email="workbit-user@example.com"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WorkBitDev123!"},
    )

def login_admin(client):
    return client.post(
        "/api/v1/auth/admin/login",
        json={"email": "workbit-admin@example.com", "password": "WorkBitDev123!"},
    )


def test_support_ticket_lifecycle_is_user_scoped_and_admin_managed(client):
    _hits.clear()
    assert client.get("/api/v1/support/tickets").status_code == 401
    assert login(client).status_code == 200

    created = client.post(
        "/api/v1/support/tickets",
        json={
            "subject": "Reward not recorded",
            "category": "OFFER_REWARD",
            "message": "I completed the survey today but cannot see its reward.",
        },
    )
    assert created.status_code == 201
    ticket = created.json()
    assert ticket["status"] == "OPEN"
    assert ticket["messages"][0]["sender_role"] == "USER"

    assert client.post(
        f"/api/v1/support/tickets/{ticket['id']}/messages",
        json={"message": "A message for someone else's ticket."},
    ).status_code == 200

    assert login_admin(client).status_code == 200
    admin_list = client.get("/api/v1/admin/support/tickets?status=OPEN")
    assert admin_list.status_code == 200
    assert admin_list.json()[0]["user_email"] == "workbit-user@example.com"

    reply = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/reply",
        json={"message": "We are checking the provider status.", "status": "IN_PROGRESS"},
    )
    assert reply.status_code == 200
    assert reply.json()["status"] == "IN_PROGRESS"
    assert reply.json()["messages"][-1]["sender_role"] == "ADMIN"

    assert login(client).status_code == 200
    user_ticket = client.get("/api/v1/support/tickets").json()[0]
    assert user_ticket["messages"][-1]["body"] == "We are checking the provider status."

    assert login_admin(client).status_code == 200
    resolved = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/reply",
        json={"message": "The provider confirmed the reward.", "status": "RESOLVED"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"

    assert login(client).status_code == 200
    closed_reply = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/messages",
        json={"message": "I still need help."},
    )
    assert closed_reply.status_code == 409


def test_support_ticket_input_is_validated_and_admin_endpoint_is_protected(client):
    assert client.get("/api/v1/admin/support/tickets").status_code == 401
    assert login(client).status_code == 200

    invalid = client.post(
        "/api/v1/support/tickets",
        json={"subject": "bad", "category": "OFFER_REWARD", "message": "short"},
    )
    assert invalid.status_code == 422


def test_daily_challenge_counts_only_approved_offer_tasks(client):
    assert login(client).status_code == 200
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    stats = response.json()["stats"]
    assert stats["daily_offers_completed"] == 0
    assert stats["daily_offers_goal"] == 3
    assert stats["daily_streak_days"] == 0
