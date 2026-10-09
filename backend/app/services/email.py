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
        provider = (settings.email_provider or "resend").strip().lower()
        if provider not in {"resend", "brevo"}:
            raise EmailDeliveryError("The configured email provider is unsupported.")
        if not settings.email_api_key or not settings.email_from_address:
            logging.error("%s email delivery is not configured", provider)
            raise EmailDeliveryError(
                "Set EMAIL_API_KEY and EMAIL_FROM_ADDRESS to enable email delivery."
            )

        sender_name, sender_email = parseaddr(settings.email_from_address)
        if not sender_email or "@" not in sender_email:
            raise EmailDeliveryError(
                "EMAIL_FROM_ADDRESS must contain a valid sender email address."
            )

        if provider == "brevo":
            payload_data = {
                "sender": {"name": sender_name or "WorkBit", "email": sender_email},
                "to": [{"email": recipient}],
                "subject": subject,
                "htmlContent": html_content,
            }
            endpoint = BREVO_API_URL
            headers = {
                "api-key": settings.email_api_key,
                "Content-Type": "application/json",
            }
        else:
            payload_data = {
                "from": settings.email_from_address,
                "to": [recipient],
                "subject": subject,
                "text": text,
                "html": html_content,
            }
            endpoint = RESEND_API_URL
            headers = {
                "Authorization": "Bearer " + settings.email_api_key,
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
            response_code = "unknown"
            try:
                response_body = json.loads(error.read())
                candidate = response_body.get("code") if isinstance(response_body, dict) else None
                if isinstance(candidate, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", candidate):
                    response_code = candidate
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            logging.error(
                "%s rejected email delivery status=%s code=%s",
                provider,
                error.code,
                response_code,
            )
            raise EmailDeliveryError("The email provider rejected the message.") from error
        except (URLError, TimeoutError, OSError) as error:
            logging.error(
                "%s email delivery request failed: %s",
                provider,
                type(error).__name__,
            )
            raise EmailDeliveryError("The email provider could not be reached.") from error

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
