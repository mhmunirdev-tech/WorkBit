import base64
import hashlib
import hmac
from decimal import Decimal
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.database.session import SessionLocal
from app.models import OfferConversion, User, Wallet
from conftest import activate_package

CALLBACK_URL = "https://api.workbitbd.com/api/v1/postbacks/theoremreach"
API_KEY = "test-theoremreach-api-key"
SECRET_KEY = "test-theoremreach-secret"
PARTNER_ID = "test-theoremreach-placement"
PLACEMENT_ID = "test-theoremreach-currency-placement"


def configure_theoremreach(monkeypatch):
    monkeypatch.setattr(settings, "theoremreach_enabled", True)
    monkeypatch.setattr(settings, "theoremreach_surveys_api_enabled", True)
    monkeypatch.setattr(settings, "theoremreach_api_key", API_KEY)
    monkeypatch.setattr(settings, "theoremreach_secret_key", SECRET_KEY)
    monkeypatch.setattr(settings, "theoremreach_partner_id", PARTNER_ID)
    monkeypatch.setattr(settings, "theoremreach_placement_id", PLACEMENT_ID)
    monkeypatch.setattr(settings, "theoremreach_callback_url", CALLBACK_URL)
    monkeypatch.setattr(settings, "theoremreach_currency_name_singular", "Credit")
    monkeypatch.setattr(settings, "theoremreach_currency_name_plural", "Credits")
    monkeypatch.setattr(settings, "theoremreach_exchange_rate", Decimal("10"))
    monkeypatch.setattr(settings, "theoremreach_decimals_to_display", 2)


class MockTheoremReachResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.theoremreach.com")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("upstream error", request=request, response=response)

    def json(self):
        return self.payload


class MockTheoremReachClient:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.request_url = ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, url):
        self.request_url = url
        return MockTheoremReachResponse(self.payload, self.status_code)


def theoremreach_survey_entry(user_id, survey_id=123):
    return (
        "https://theoremreach.com/respondent_entry/surveys_api"
        f"?api_key={API_KEY}&user_id={user_id}&survey_id={survey_id}&quota_ids%5B%5D=456"
    )


def mock_theoremreach_surveys(monkeypatch, mock_client):
    monkeypatch.setattr(
        "app.services.theoremreach_surveys.httpx.AsyncClient",
        lambda **_kwargs: mock_client,
    )


def login_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "workbit-user@example.com", "password": "WorkBitDev123!"},
    )
    assert response.status_code == 200


def get_user_id():
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "workbit-user@example.com"))
        assert user is not None
        return user.id
    finally:
        db.close()


def get_wallet_balance():
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == "workbit-user@example.com"))
        assert user is not None
        wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id))
        assert wallet is not None
        return Decimal(wallet.available_balance), Decimal(wallet.pending_balance)
    finally:
        db.close()


def callback_url(**overrides):
    values = {
        "user_id": get_user_id(),
        "tx_id": "theoremreach-reward-1",
        "currency": "1.25",
        "reward": "12.5",
        "partner_id": PARTNER_ID,
        "external_transaction_id": "theoremreach-session-1",
    }
    values.update(overrides)
    query = urlencode(values)
    signing_url = f"{CALLBACK_URL}?{query}"
    digest = hmac.new(
        SECRET_KEY.encode("utf-8"),
        signing_url.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    signature = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"/api/v1/postbacks/theoremreach?{query}&hash={signature}"


def test_theoremreach_wall_url_requires_auth_and_active_package(client, monkeypatch):
    configure_theoremreach(monkeypatch)
    assert client.get("/api/v1/offers/providers/theoremreach/wall-url").status_code == 401
    login_user(client)
    assert client.get("/api/v1/offers/providers/theoremreach/wall-url").status_code == 402

    activate_package(client, "THEOREMREACH-WALL-001")
    response = client.get("/api/v1/offers/providers/theoremreach/wall-url")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    wall_url = response.json()["wall_url"]
    query = parse_qs(urlsplit(wall_url).query)
    assert urlsplit(wall_url).path == "/respondent_entry/direct"
    assert query["api_key"] == [API_KEY]
    assert query["user_id"] == [get_user_id()]
    assert query["external_id"] == [get_user_id()]
    assert query["partner_id"] == [PARTNER_ID]
    assert query["placement_id"] == [PLACEMENT_ID]
    assert query["exchange_rate"] == ["10"]
    assert query["currency_name_plural"] == ["Credits"]
    assert "hash" in query
    assert SECRET_KEY not in wall_url


def test_theoremreach_partner_id_is_optional_and_placement_id_is_distinct(client, monkeypatch):
    configure_theoremreach(monkeypatch)
    monkeypatch.setattr(settings, "theoremreach_partner_id", None)
    login_user(client)
    activate_package(client, "THEOREMREACH-WALL-OPTIONAL-PARTNER")

    response = client.get("/api/v1/offers/providers/theoremreach/wall-url")

    assert response.status_code == 200
    query = parse_qs(urlsplit(response.json()["wall_url"]).query)
    assert query["placement_id"] == [PLACEMENT_ID]
    assert "partner_id" not in query


def test_theoremreach_surveys_api_returns_signed_individual_survey_cards(
    client, monkeypatch
):
    configure_theoremreach(monkeypatch)
    assert client.get("/api/v1/offers/providers/theoremreach/surveys").status_code == 401
    login_user(client)
    assert client.get("/api/v1/offers/providers/theoremreach/surveys").status_code == 402
    activate_package(client, "THEOREMREACH-SURVEY-CARDS")

    mock_client = MockTheoremReachClient(
        {
            "surveys": [
                {
                    "campaign_id": 123,
                    "quota_id": 456,
                    "quota_ids": [456],
                    "rank": 900,
                    "loi": 12,
                    "cpi": "1.25",
                    "incidence": 45,
                    "entry_link": theoremreach_survey_entry(get_user_id()),
                }
            ]
        }
    )
    mock_theoremreach_surveys(monkeypatch, mock_client)

    response = client.get("/api/v1/offers/providers/theoremreach/surveys")

    assert response.status_code == 200
    result = response.json()
    assert len(result["surveys"]) == 1
    survey = result["surveys"][0]
    assert survey["survey_id"] == 123
    assert survey["title"] == "Survey #123"
    assert survey["estimated_time_minutes"] == 12
    assert Decimal(survey["user_reward_usd"]) > 0
    entry_url = survey["entry_url"]
    unsigned_entry_url, supplied_hash = entry_url.rsplit("&hash=", 1)
    expected_hash = base64.urlsafe_b64encode(
        hmac.new(
            SECRET_KEY.encode(),
            unsigned_entry_url.encode(),
            hashlib.sha1,
        ).digest()
    ).decode().rstrip("=")
    assert supplied_hash == expected_hash
    entry_query = parse_qs(urlsplit(entry_url).query)
    assert entry_query["transaction_id"]
    assert entry_query["partner_id"] == [PARTNER_ID]
    assert entry_query["placement_id"] == [PLACEMENT_ID]
    assert SECRET_KEY not in response.text
    assert response.headers["cache-control"] == "no-store"
    api_query = parse_qs(urlsplit(mock_client.request_url).query)
    assert api_query["api_key"] == [API_KEY]
    assert api_query["user_id"] == [get_user_id()]
    assert api_query["country_code"]
    assert "hash" in api_query


def test_theoremreach_surveys_api_requires_publisher_access(client, monkeypatch):
    configure_theoremreach(monkeypatch)
    login_user(client)
    activate_package(client, "THEOREMREACH-SURVEY-CARDS-ACCESS")
    mock_theoremreach_surveys(
        monkeypatch,
        MockTheoremReachClient({"error": "Publisher API access denied."}, status_code=403),
    )

    response = client.get("/api/v1/offers/providers/theoremreach/surveys")

    assert response.status_code == 503
    assert "enabled by your account manager" in response.json()["error"]["message"]


def test_theoremreach_debug_callback_does_not_change_wallet(client, monkeypatch):
    configure_theoremreach(monkeypatch)
    monkeypatch.setattr(settings, "theoremreach_enabled", False)
    url = callback_url(
        debug="true",
        user_id="",
        tx_id="",
        currency="",
        partner_id="",
    )
    initial_balance = get_wallet_balance()

    response = client.get(url)

    assert response.status_code == 200
    assert get_wallet_balance() == initial_balance

    live_callback = client.get(callback_url())
    assert live_callback.status_code == 503
    assert get_wallet_balance() == initial_balance


def test_theoremreach_verified_callback_credits_once_and_reverses_once(client, monkeypatch):
    configure_theoremreach(monkeypatch)
    activate_package(client, "THEOREMREACH-CALLBACK-001")
    initial_balance = get_wallet_balance()

    first = client.get(callback_url())
    assert first.status_code == 200
    credited_balance = get_wallet_balance()
    assert credited_balance != initial_balance
    assert client.get(callback_url()).status_code == 200
    assert get_wallet_balance() == credited_balance

    reversal_url = callback_url(currency="-1.25", reversal="true")
    reversal = client.get(reversal_url)
    assert reversal.status_code == 200
    reversed_balance = get_wallet_balance()
    assert reversed_balance == initial_balance
    assert client.get(reversal_url).status_code == 200
    assert get_wallet_balance() == reversed_balance

    db = SessionLocal()
    try:
        conversion = db.scalar(
            select(OfferConversion).where(
                OfferConversion.network_id == "theoremreach",
                OfferConversion.external_transaction_id == "theoremreach-reward-1",
            )
        )
        assert conversion is not None
        assert conversion.status == "REVERSED"
    finally:
        db.close()


def test_theoremreach_rejects_bad_hash_duplicate_parameters_and_mismatched_reversal(
    client, monkeypatch
):
    configure_theoremreach(monkeypatch)
    valid_url = callback_url()
    invalid_hash = client.get(valid_url.replace("currency=1.25", "currency=1.26"))
    assert invalid_hash.status_code == 403

    duplicate_parameter = client.get(f"{valid_url}&currency=1.25")
    assert duplicate_parameter.status_code == 400

    mismatched_reversal = client.get(callback_url(reversal="true"))
    assert mismatched_reversal.status_code == 403
