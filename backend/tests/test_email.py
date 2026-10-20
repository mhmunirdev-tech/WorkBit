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


@pytest.fixture(autouse=True)
def clear_email_provider_settings(monkeypatch):
    monkeypatch.setattr(settings, "email_provider", None)
    monkeypatch.setattr(settings, "resend_api_key", None)
    monkeypatch.setattr(settings, "brevo_api_key", None)


def test_resend_sends_verification_code_without_a_link(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "test-api-key")
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
    monkeypatch.setattr(settings, "resend_api_key", "test-api-key")
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
    monkeypatch.setattr(settings, "resend_api_key", api_key)
    monkeypatch.setattr(settings, "email_from_address", from_address)

    with pytest.raises(EmailDeliveryError):
        EmailService().send_verification("user@example.com", "token")


def test_resend_rejects_invalid_from_address_without_sending(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "test-api-key")
    monkeypatch.setattr(settings, "email_from_address", "not-an-email")

    def unexpected_send(*_args, **_kwargs):
        raise AssertionError("Invalid sender must be rejected before calling Resend.")

    monkeypatch.setattr("app.services.email.urlopen", unexpected_send)
    with pytest.raises(EmailDeliveryError, match="EMAIL_FROM_ADDRESS"):
        EmailService().send_verification("user@example.com", "token")


def test_resend_rejection_logs_only_provider_status_and_error_code(monkeypatch, caplog):
    monkeypatch.setattr(settings, "resend_api_key", "test-api-key")
    monkeypatch.setattr(settings, "email_from_address", "WorkBit <verify@example.com>")

    def reject_request(*_args, **_kwargs):
        raise HTTPError(
            "https://api.resend.com/emails",
            401,
            "Unauthorized",
            {},
            BytesIO(b'{"code":"unauthorized","message":"private details"}'),
        )

    monkeypatch.setattr("app.services.email.urlopen", reject_request)
    with pytest.raises(EmailDeliveryError, match="provider rejected"):
        EmailService().send_verification("user@example.com", "secret-token")

    assert "resend rejected email delivery status=401 code=unauthorized" in caplog.text
    assert "private details" not in caplog.text
    assert "test-api-key" not in caplog.text
    assert "secret-token" not in caplog.text


def test_email_provider_is_detected_from_single_configured_api_key(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", " ")
    monkeypatch.setattr(settings, "brevo_api_key", "test-brevo-key")

    assert EmailService._provider() == "brevo"


def test_email_provider_is_detected_as_resend_when_only_resend_key_exists(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "test-api-key")

    assert EmailService._provider() == "resend"


def test_email_provider_must_be_selected_when_both_keys_are_configured(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "test-resend-key")
    monkeypatch.setattr(settings, "brevo_api_key", "test-brevo-key")

    with pytest.raises(EmailDeliveryError, match="EMAIL_PROVIDER"):
        EmailService._provider()


def test_explicit_email_provider_selects_its_configured_key(monkeypatch):
    monkeypatch.setattr(settings, "email_provider", "BREVO")
    monkeypatch.setattr(settings, "resend_api_key", "test-resend-key")
    monkeypatch.setattr(settings, "brevo_api_key", "test-brevo-key")
    monkeypatch.setattr(settings, "email_from_address", "WorkBit <verify@example.com>")
    sent = {}

    def fake_urlopen(request: Request, timeout: int):
        sent["url"] = request.full_url
        sent["api_key"] = request.get_header("Api-key")
        sent["body"] = json.loads(request.data)
        return FakeResponse()

    monkeypatch.setattr("app.services.email.urlopen", fake_urlopen)
    EmailService().send_verification("user@example.com", "012345")

    assert sent["url"] == "https://api.brevo.com/v3/smtp/email"
    assert sent["api_key"] == "test-brevo-key"
    assert sent["body"]["to"] == [{"email": "user@example.com"}]
    assert "012345" in sent["body"]["htmlContent"]
