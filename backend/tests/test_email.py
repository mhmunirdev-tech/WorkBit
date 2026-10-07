import json
from urllib.request import Request

import pytest

from app.core.config import settings
from app.services.email import EmailDeliveryError, ResendEmailService


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_resend_sends_verification_link_without_logging_token(monkeypatch):
    monkeypatch.setattr(settings, "email_provider", "resend")
    monkeypatch.setattr(settings, "email_api_key", "test-api-key")
    monkeypatch.setattr(settings, "email_from_address", "WorkBit <verify@example.com>")
    monkeypatch.setattr(settings, "frontend_origin", "https://workbit.example")
    sent = {}

    def fake_urlopen(request: Request, timeout: int):
        sent["url"] = request.full_url
        sent["authorization"] = request.get_header("Authorization")
        sent["timeout"] = timeout
        sent["body"] = json.loads(request.data)
        return FakeResponse()

    monkeypatch.setattr("app.services.email.urlopen", fake_urlopen)
    ResendEmailService().send_verification("user@example.com", "single-use-token")

    assert sent["url"] == "https://api.resend.com/emails"
    assert sent["authorization"] == "Bearer test-api-key"
    assert sent["timeout"] == 10
    assert sent["body"]["from"] == "WorkBit <verify@example.com>"
    assert sent["body"]["to"] == ["user@example.com"]
    assert "https://workbit.example/verify-email?token=single-use-token" in sent["body"]["text"]
    assert "single-use-token" not in sent["body"]["subject"]

def test_resend_sends_password_reset_link(monkeypatch):
    monkeypatch.setattr(settings, "email_provider", "resend")
    monkeypatch.setattr(settings, "email_api_key", "test-api-key")
    monkeypatch.setattr(settings, "email_from_address", "WorkBit <verify@example.com>")
    monkeypatch.setattr(settings, "frontend_origin", "https://workbit.example")
    sent = {}

    def fake_urlopen(request: Request, timeout: int):
        sent["body"] = json.loads(request.data)
        return FakeResponse()

    monkeypatch.setattr("app.services.email.urlopen", fake_urlopen)
    ResendEmailService().send_password_reset("user@example.com", "reset-token")

    assert "https://workbit.example/reset-password?token=reset-token" in sent["body"]["text"]


@pytest.mark.parametrize(
    ("api_key", "from_address"),
    [(None, "WorkBit <verify@example.com>"), ("test-api-key", None)],
)
def test_resend_requires_api_key_and_verified_sender(monkeypatch, api_key, from_address):
    monkeypatch.setattr(settings, "email_provider", "resend")
    monkeypatch.setattr(settings, "email_api_key", api_key)
    monkeypatch.setattr(settings, "email_from_address", from_address)

    with pytest.raises(EmailDeliveryError):
        ResendEmailService().send_verification("user@example.com", "token")
