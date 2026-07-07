"""Email sending with a development fallback.

When ``SMTP_HOST`` is configured, emails are sent over SMTP. Otherwise they are
logged (so local development works without mail credentials — the generated
password shows up in the server logs).
"""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("app.email")


def send_email(to: str, subject: str, body: str, html: str | None = None) -> None:
    if not settings.emails_enabled:
        logger.warning(
            "[email disabled] would send to %s | subject: %s\n%s",
            to,
            subject,
            body,
        )
        return

    message = EmailMessage()
    message["From"] = f"{settings.email_from_name} <{settings.email_from}>"
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user:
                # Gmail app passwords are shown with spaces for readability; strip them.
                server.login(settings.smtp_user, settings.smtp_password.replace(" ", ""))
            server.send_message(message)
        logger.info("Sent email to %s (%s)", to, subject)
    except Exception:  # noqa: BLE001 - don't let email failures break the request
        logger.exception("Failed to send email to %s", to)


def send_welcome_email(to: str, name: str, password: str) -> None:
    """Email a newly created user their temporary password and a login link."""
    login_url = f"{settings.frontend_url.rstrip('/')}/login"
    subject = f"Your {settings.app_name} account"
    body = (
        f"Hi {name or 'there'},\n\n"
        f"An account has been created for you on {settings.app_name}.\n\n"
        f"Login email: {to}\n"
        f"Temporary password: {password}\n\n"
        f"Sign in here: {login_url}\n\n"
        f"For your security, please change this password after your first login.\n"
    )
    html = (
        f"<p>Hi {name or 'there'},</p>"
        f"<p>An account has been created for you on <strong>{settings.app_name}</strong>.</p>"
        f"<p><strong>Login email:</strong> {to}<br>"
        f"<strong>Temporary password:</strong> {password}</p>"
        f'<p><a href="{login_url}">Sign in to your account</a></p>'
        f"<p>For your security, please change this password after your first login.</p>"
    )
    send_email(to, subject, body, html)
