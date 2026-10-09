import json
from io import BytesIO
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from app.core.config import settings
from app.services.email import EmailDeliveryError, EmailService


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_resend_sends_verification_code_without_a_link(monkeypatch):
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
    EmailService().send_verification("user@example.com", "012345")

    assert sent["url"] == "https://api.resend.com/emails"
    assert sent["authorization"] == "Bearer test-api-key"
    assert sent["timeout"] == 10
    assert sent["body"]["from"] == "WorkBit <verify@example.com>"
    assert sent["body"]["to"] == ["user@example.com"]
    assert sent["body"]["subject"] == "Your WorkBit verification code"
    assert "012345" in sent["body"]["text"]
    assert "012345" in sent["body"]["html"]
    assert "/verify-email?" not in sent["body"]["text"]

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
    EmailService().send_password_reset("user@example.com", "reset-token")

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
        EmailService().send_verification("user@example.com", "token")


def test_brevo_sends_verification_email_with_brevo_payload(monkeypatch):
    monkeypatch.setattr(settings, "email_provider", "brevo")
    monkeypatch.setattr(settings, "email_api_key", "test-brevo-api-key")
    monkeypatch.setattr(settings, "email_from_address", "WorkBit <verify@example.com>")
    monkeypatch.setattr(settings, "frontend_origin", "https://workbit.example")
    sent = {}

    def fake_urlopen(request: Request, timeout: int):
        sent["url"] = request.full_url
        sent["api_key"] = request.get_header("Api-key")
        sent["timeout"] = timeout
        sent["body"] = json.loads(request.data)
        return FakeResponse()

    monkeypatch.setattr("app.services.email.urlopen", fake_urlopen)
    EmailService().send_verification("user@example.com", "012345")

    assert sent["url"] == "https://api.brevo.com/v3/smtp/email"
    assert sent["api_key"] == "test-brevo-api-key"
    assert sent["timeout"] == 10
    assert sent["body"]["sender"] == {"name": "WorkBit", "email": "verify@example.com"}
    assert sent["body"]["to"] == [{"email": "user@example.com"}]
    assert sent["body"]["subject"] == "Your WorkBit verification code"
    assert "012345" in sent["body"]["htmlContent"]
    assert "verify-email?" not in sent["body"]["htmlContent"]
    assert "textContent" not in sent["body"]
    assert "templateId" not in sent["body"]


def test_brevo_sends_password_reset_email_with_html_content(monkeypatch):
    monkeypatch.setattr(settings, "email_provider", "brevo")
    monkeypatch.setattr(settings, "email_api_key", "test-brevo-api-key")
    monkeypatch.setattr(settings, "email_from_address", "WorkBit <verify@example.com>")
    monkeypatch.setattr(settings, "frontend_origin", "https://workbit.example")
    sent = {}

    class BrevoResponse(FakeResponse):
        status = 201

    def fake_urlopen(request: Request, timeout: int):
        sent["url"] = request.full_url
        sent["body"] = json.loads(request.data)
        return BrevoResponse()

    monkeypatch.setattr("app.services.email.urlopen", fake_urlopen)
    EmailService().send_password_reset("user@example.com", "reset-token")

    assert sent["url"] == "https://api.brevo.com/v3/smtp/email"
    assert sent["body"]["subject"] == "Reset your WorkBit password"
    assert "https://workbit.example/reset-password?token=reset-token" in sent["body"]["htmlContent"]
    assert "textContent" not in sent["body"]


def test_brevo_rejects_invalid_from_address_without_sending(monkeypatch):
    monkeypatch.setattr(settings, "email_provider", "brevo")
    monkeypatch.setattr(settings, "email_api_key", "test-brevo-api-key")
    monkeypatch.setattr(settings, "email_from_address", "not-an-email")

    def unexpected_send(*_args, **_kwargs):
        raise AssertionError("Invalid sender must be rejected before calling Brevo.")

    monkeypatch.setattr("app.services.email.urlopen", unexpected_send)
    with pytest.raises(EmailDeliveryError, match="EMAIL_FROM_ADDRESS"):
        EmailService().send_verification("user@example.com", "token")


def test_brevo_rejection_logs_only_provider_status_and_error_code(monkeypatch, caplog):
    monkeypatch.setattr(settings, "email_provider", "brevo")
    monkeypatch.setattr(settings, "email_api_key", "test-brevo-api-key")
    monkeypatch.setattr(settings, "email_from_address", "WorkBit <verify@example.com>")

    def reject_request(*_args, **_kwargs):
        raise HTTPError(
            "https://api.brevo.com/v3/smtp/email",
            401,
            "Unauthorized",
            {},
            BytesIO(b'{"code":"unauthorized","message":"private details"}'),
        )

    monkeypatch.setattr("app.services.email.urlopen", reject_request)
    with pytest.raises(EmailDeliveryError, match="provider rejected"):
        EmailService().send_verification("user@example.com", "secret-token")

    assert "brevo rejected email delivery status=401 code=unauthorized" in caplog.text
    assert "private details" not in caplog.text
    assert "test-brevo-api-key" not in caplog.text
    assert "secret-token" not in caplog.text
