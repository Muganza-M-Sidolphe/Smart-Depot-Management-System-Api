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


def send_email(
    to: str | list[str],
    subject: str,
    body: str,
    html: str | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> None:
    """Send an email. ``attachments`` is a list of (filename, content, mimetype)."""
    recipients = [to] if isinstance(to, str) else list(to)
    if not recipients:
        return

    if not settings.emails_enabled:
        logger.warning(
            "[email disabled] would send to %s | subject: %s | attachments: %s\n%s",
            ", ".join(recipients),
            subject,
            [a[0] for a in (attachments or [])],
            body,
        )
        return

    message = EmailMessage()
    message["From"] = f"{settings.email_from_name} <{settings.email_from}>"
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype="html")
    for filename, content, mimetype in attachments or []:
        maintype, _, subtype = mimetype.partition("/")
        message.add_attachment(content, maintype=maintype, subtype=subtype or "octet-stream", filename=filename)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user:
                # Gmail app passwords are shown with spaces for readability; strip them.
                server.login(settings.smtp_user, settings.smtp_password.replace(" ", ""))
            server.send_message(message)
        logger.info("Sent email to %s (%s)", ", ".join(recipients), subject)
    except Exception:  # noqa: BLE001 - don't let email failures break the request
        logger.exception("Failed to send email to %s", ", ".join(recipients))


def send_password_reset_email(to: str, name: str, reset_url: str, expire_minutes: int) -> None:
    """Email a user a password-reset link."""
    subject = f"Reset your {settings.app_name} password"
    body = (
        f"Hi {name or 'there'},\n\n"
        f"We received a request to reset your password.\n\n"
        f"Reset it here (link valid for {expire_minutes} minutes):\n{reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email — your "
        f"password will not change.\n"
    )
    html = (
        f"<p>Hi {name or 'there'},</p>"
        f"<p>We received a request to reset your password.</p>"
        f'<p><a href="{reset_url}">Reset your password</a> '
        f"(valid for {expire_minutes} minutes).</p>"
        f"<p>If you did not request this, you can safely ignore this email — your "
        f"password will not change.</p>"
    )
    send_email(to, subject, body, html)


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
