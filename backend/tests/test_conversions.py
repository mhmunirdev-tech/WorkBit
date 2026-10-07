from app.services.rate_limit import _hits

def create_click(client):
    _hits.clear()
    assert client.post("/api/v1/auth/login", json={"email":"workbit-user@example.com", "password":"WorkBitDev123!"}).status_code == 200
    click = client.post("/api/v1/offers/mock-game/click").json()
    return click["click_id"]

def payload(click_id, transaction="mock-tx-1", status="PENDING"):
    return {"transaction_id":transaction,"click_id":click_id,"offer_id":"mock-game","payout":"0.50","currency":"USD","status":status}

def test_normalized_conversion_never_credits_wallet(client):
    click_id = create_click(client)
    response = client.post("/api/v1/postbacks/mock", json=payload(click_id))
    assert response.status_code == 202 and response.json()["status"] == "PENDING"
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["available_balance"] == "0E-8" and dashboard["pending_balance"] == "0E-8"

def test_postback_rejects_unknown_provider_and_unknown_click(client):
    assert client.post("/api/v1/postbacks/adgem", json=payload("a" * 32)).status_code == 503
    assert client.post("/api/v1/postbacks/mock", json=payload("a" * 32)).status_code == 400

def test_duplicate_and_reversal_transition(client):
    click_id = create_click(client)
    assert client.post("/api/v1/postbacks/mock", json=payload(click_id, "mock-tx-2")).status_code == 202
    assert client.post("/api/v1/postbacks/mock", json=payload(click_id, "mock-tx-2")).status_code == 409
    reversal = client.post("/api/v1/postbacks/mock", json=payload(click_id, "mock-tx-2", "REVERSED"))
    assert reversal.status_code == 202 and reversal.json()["status"] == "REVERSED"

def test_postback_requires_valid_payload_and_matching_offer(client):
    click_id = create_click(client)
    assert client.post("/api/v1/postbacks/mock", json={"click_id":click_id}).status_code == 422
    bad = payload(click_id, "mock-tx-3"); bad["offer_id"] = "mock-survey"
    assert client.post("/api/v1/postbacks/mock", json=bad).status_code == 400
