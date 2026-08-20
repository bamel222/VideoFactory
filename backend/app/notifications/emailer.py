from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

import httpx

from app.core.config import get_settings

logger = logging.getLogger("video_factory.notifications")

settings = get_settings()


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    """Send an email via the configured provider (resend | sendgrid | smtp).

    A no-op (logged) when no provider is configured, so notifications never
    crash the pipeline.
    """
    if not to:
        return
    provider = (settings.email_provider or "").strip().lower()
    if provider == "resend":
        _send_resend(to, subject, text, html)
    elif provider == "sendgrid":
        _send_sendgrid(to, subject, text, html)
    elif provider == "smtp":
        _send_smtp(to, subject, text, html)
    else:
        logger.info("email skipped (no provider configured): %s", subject)


def _from_address() -> tuple[str, str]:
    name, addr = parseaddr(settings.email_from)
    return (addr or "no-reply@videofactory.ai", name or "")


def _send_resend(to: str, subject: str, text: str, html: str | None) -> None:
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY manquante")
    from_addr, from_name = _from_address()
    payload = {
        "from": formataddr((from_name, from_addr)) if from_name else from_addr,
        "to": [to],
        "subject": subject,
        "text": text,
    }
    if html:
        payload["html"] = html
    resp = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()


def _send_sendgrid(to: str, subject: str, text: str, html: str | None) -> None:
    if not settings.sendgrid_api_key:
        raise RuntimeError("SENDGRID_API_KEY manquante")
    from_addr, from_name = _from_address()
    content = [{"type": "text/plain", "value": text}]
    if html:
        content.append({"type": "text/html", "value": html})
    payload = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": from_addr, "name": from_name} if from_name else {"email": from_addr},
        "subject": subject,
        "content": content,
    }
    resp = httpx.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()


def _send_smtp(to: str, subject: str, text: str, html: str | None) -> None:
    if not settings.smtp_host:
        raise RuntimeError("SMTP_HOST manquant")
    from_addr, from_name = _from_address()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name, from_addr)) if from_name else from_addr
    msg["To"] = to
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    if settings.smtp_use_tls:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as s:
            s.starttls(context=ctx)
            if settings.smtp_username:
                s.login(settings.smtp_username, settings.smtp_password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as s:
            if settings.smtp_username:
                s.login(settings.smtp_username, settings.smtp_password)
            s.send_message(msg)
