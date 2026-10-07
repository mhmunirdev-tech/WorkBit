from __future__ import annotations

import html
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings

RESEND_API_URL = "https://api.resend.com/emails"


class EmailDeliveryError(RuntimeError):
    pass


class ResendEmailService:
    def _send(self, recipient: str, subject: str, text: str, html_content: str) -> None:
        if (settings.email_provider or "").strip().lower() not in {"resend", ""}:
            raise EmailDeliveryError("The configured email provider is unsupported.")
        if not settings.email_api_key or not settings.email_from_address:
            logging.error("Resend email delivery is not configured")
            raise EmailDeliveryError(
                "Set EMAIL_API_KEY and EMAIL_FROM_ADDRESS to enable email delivery."
            )

        payload = json.dumps({
            "from": settings.email_from_address,
            "to": [recipient],
            "subject": subject,
            "text": text,
            "html": html_content,
        }).encode("utf-8")
        request = Request(
            RESEND_API_URL,
            data=payload,
            headers={
                "Authorization": "Bearer " + settings.email_api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                if not 200 <= response.status < 300:
                    logging.error("Resend rejected email delivery status=%s", response.status)
                    raise EmailDeliveryError("The email provider rejected the message.")
        except HTTPError as error:
            logging.error("Resend rejected email delivery status=%s", error.code)
            raise EmailDeliveryError("The email provider rejected the message.") from error
        except (URLError, TimeoutError, OSError) as error:
            logging.error("Resend email delivery request failed: %s", type(error).__name__)
            raise EmailDeliveryError("The email provider could not be reached.") from error

    def send_verification(self, recipient: str, token: str) -> None:
        link = f"{settings.frontend_origin.rstrip('/')}/verify-email?{urlencode({'token': token})}"
        safe_link = html.escape(link, quote=True)
        self._send(
            recipient,
            "Verify your WorkBit email",
            f"Verify your email address by opening this link: {link}",
            (
                "<p>Thanks for joining WorkBit. Verify your email address to activate your account.</p>"
                f'<p><a href="{safe_link}">Verify email address</a></p>'
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


email_service = ResendEmailService()
