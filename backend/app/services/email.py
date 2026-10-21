from __future__ import annotations

import html
import json
import logging
import re
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings

RESEND_API_URL = "https://api.resend.com/emails"
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _safe_provider_error_details(
    response_body: object,
    api_key: str | None,
) -> tuple[str, str]:
    if not isinstance(response_body, dict):
        return "unknown", "unavailable"

    candidate_code = response_body.get("code") or response_body.get("name")
    code = (
        candidate_code
        if isinstance(candidate_code, str)
        and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", candidate_code)
        else "unknown"
    )
    candidate_message = response_body.get("message")
    if not isinstance(candidate_message, str):
        return code, "unavailable"

    message = candidate_message
    if api_key:
        message = message.replace(api_key, "[redacted]")
    message = re.sub(r"(?i)\bbearer\s+\S+", "Bearer [redacted]", message)
    message = re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[email]",
        message,
        flags=re.IGNORECASE,
    )
    message = re.sub(r"[\r\n\t]+", " ", message)
    return code, message[:300] or "unavailable"


class EmailDeliveryError(RuntimeError):
    pass


class EmailService:
    def _send(
        self,
        recipient: str,
        subject: str,
        text: str,
        html_content: str,
    ) -> None:
        provider = self._provider()
        if not settings.email_from_address:
            logging.error("%s email delivery is not configured", provider)
            raise EmailDeliveryError(
                "Set EMAIL_FROM_ADDRESS and the selected provider's API key to enable email delivery."
            )

        _, sender_email = parseaddr(settings.email_from_address)
        if not sender_email or "@" not in sender_email:
            raise EmailDeliveryError(
                "EMAIL_FROM_ADDRESS must contain a valid sender email address."
            )

        if provider == "resend":
            api_key = settings.resend_api_key
            if not api_key:
                raise EmailDeliveryError("Set RESEND_API_KEY for the selected email provider.")
            payload_data = {
                "from": settings.email_from_address,
                "to": [recipient],
                "subject": subject,
                "text": text,
                "html": html_content,
            }
            endpoint = RESEND_API_URL
            headers = {
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json",
            }
        else:
            api_key = settings.brevo_api_key
            if not api_key:
                raise EmailDeliveryError("Set BREVO_API_KEY for the selected email provider.")
            payload_data = {
                "sender": {
                    "name": parseaddr(settings.email_from_address)[0] or "WorkBit",
                    "email": sender_email,
                },
                "to": [{"email": recipient}],
                "subject": subject,
                "htmlContent": html_content,
                "textContent": text,
            }
            endpoint = BREVO_API_URL
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json",
            }

        payload = json.dumps(payload_data).encode("utf-8")
        request = Request(
            endpoint,
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                if not 200 <= response.status < 300:
                    logging.error(
                        "%s rejected email delivery status=%s",
                        provider,
                        response.status,
                    )
                    raise EmailDeliveryError("The email provider rejected the message.")
        except HTTPError as error:
            response_body = None
            try:
                response_body = json.loads(error.read())
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            response_code, response_message = _safe_provider_error_details(
                response_body,
                api_key,
            )
            logging.error(
                "%s rejected email delivery status=%s code=%s message=%s",
                provider,
                error.code,
                response_code,
                response_message,
            )
            raise EmailDeliveryError("The email provider rejected the message.") from error
        except (URLError, TimeoutError, OSError) as error:
            logging.error(
                "%s email delivery request failed: %s",
                provider,
                type(error).__name__,
            )
            raise EmailDeliveryError("The email provider could not be reached.") from error

    @staticmethod
    def _provider() -> str:
        configured = {
            "resend": bool(settings.resend_api_key and settings.resend_api_key.strip()),
            "brevo": bool(settings.brevo_api_key and settings.brevo_api_key.strip()),
        }
        requested = (settings.email_provider or "").strip().lower()
        if requested:
            if requested not in configured:
                raise EmailDeliveryError(
                    "EMAIL_PROVIDER must be either 'resend' or 'brevo'."
                )
            if not configured[requested]:
                key_name = "RESEND_API_KEY" if requested == "resend" else "BREVO_API_KEY"
                raise EmailDeliveryError(f"Set {key_name} for the selected email provider.")
            return requested

        providers = [provider for provider, is_configured in configured.items() if is_configured]
        if len(providers) == 1:
            return providers[0]
        if not providers:
            raise EmailDeliveryError(
                "Set RESEND_API_KEY or BREVO_API_KEY and EMAIL_FROM_ADDRESS to enable email delivery."
            )
        raise EmailDeliveryError(
            "Multiple email provider API keys are configured. Set EMAIL_PROVIDER to choose one."
        )

    def send_verification(self, recipient: str, token: str) -> None:
        expiry = settings.email_verification_otp_ttl_minutes
        self._send(
            recipient,
            "Your WorkBit verification code",
            f"Your WorkBit email verification code is {token}. It expires in {expiry} minutes.",
            (
                "<p>Thanks for joining WorkBit. Verify your email address to activate your account.</p>"
                f'<p>Your verification code is <strong>{html.escape(token)}</strong>.</p>'
                f"<p>This code expires in {expiry} minutes. Enter it on the WorkBit verification page.</p>"
                "<p>If you did not create a WorkBit account, you can ignore this email.</p>"
            ),
        )

    def send_security_code(self, recipient: str, code: str, action: str) -> None:
        expiry = settings.email_verification_otp_ttl_minutes
        safe_action = html.escape(action)
        safe_code = html.escape(code)
        self._send(
            recipient,
            f"Confirm your WorkBit {action}",
            f"Your WorkBit confirmation code is {code}. It expires in {expiry} minutes.",
            (
                f"<p>Use this code to confirm your {safe_action}.</p>"
                f"<p>Your confirmation code is <strong>{safe_code}</strong>.</p>"
                f"<p>This code expires in {expiry} minutes. If you did not request this, "
                "you can ignore this email.</p>"
            ),
        )

    def send_password_reset(self, recipient: str, token: str) -> None:
        link = f"{settings.frontend_origin.rstrip('/')}/reset-password?{urlencode({'token': token})}"
        safe_link = html.escape(link, quote=True)
        self._send(
            recipient,
            "Reset your WorkBit password",
            f"Reset your password by opening this link: {link}",
            (
                "<p>A password reset was requested for your WorkBit account.</p>"
                f'<p><a href="{safe_link}">Reset password</a></p>'
                "<p>If you did not request this, you can ignore this email.</p>"
            ),
        )


email_service = EmailService()
