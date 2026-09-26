"""Outbound email (verification). Falls back to structured logs when SMTP is unset."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def send_verification_email(*, to_email: str, verify_url: str) -> None:
    subject = "Verify your CloudMLOps account"
    hours = settings.email_verification_expire_hours
    body = (
        "Welcome to CloudMLOps.\n\n"
        f"Open this link to verify your email (expires in {hours} hours):\n"
        f"{verify_url}\n"
    )
    if not settings.smtp_host:
        logger.info(
            "email verification link (SMTP not configured)",
            extra={"to": to_email, "verify_url": verify_url},
        )
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
