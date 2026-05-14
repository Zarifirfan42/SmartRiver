"""
Email delivery for verification and password-reset OTPs.

- SendGrid: set SENDGRID_API_KEY
- Gmail / SMTP: SMTP_HOST, SMTP_PORT, SMTP_PASSWORD, and either SMTP_USER or SMTP_USERNAME
- From address: SMTP_FROM or SMTP_FROM_EMAIL; display name: SMTP_FROM_NAME
- Dev mode: SMARTRIVER_OTP_DEV_LOG=1 prints OTP to stdout (no SMTP required)

Loads .env from project root and backend/.env so uvicorn sees the same variables as main.py.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import smtplib
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

logger = logging.getLogger(__name__)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_dotenv_files() -> None:
    try:
        from dotenv import load_dotenv

        root = _project_root()
        load_dotenv(root / "backend" / ".env")
        load_dotenv(root / ".env", override=True)
    except ImportError:
        pass


_load_dotenv_files()


class EmailNotConfiguredError(Exception):
    """No SendGrid key and no complete SMTP settings, and dev OTP log is off."""


class EmailSendError(Exception):
    """Outgoing email failed."""


def _env_bool(name: str, default: bool = False) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return default


def dev_otp_log_enabled() -> bool:
    return _env_bool("SMARTRIVER_OTP_DEV_LOG", False)


def get_otp_expiry_minutes() -> int:
    raw = (
        os.environ.get("OTP_EXPIRE_MINUTES")
        or os.environ.get("OTP_EXPIRY_MINUTES")
        or "10"
    )
    try:
        n = int(str(raw).strip())
        return max(1, min(n, 120))
    except ValueError:
        return 10


def smtp_login_user() -> str:
    """Prefer SMTP_USER; alias SMTP_USERNAME (common in tutorials)."""
    return (os.environ.get("SMTP_USER") or os.environ.get("SMTP_USERNAME") or "").strip()


def smtp_login_password() -> str:
    """Gmail App Passwords may include spaces; SMTP login must use the 16 chars without spaces."""
    raw = os.environ.get("SMTP_PASSWORD") or ""
    return raw.replace(" ", "").strip()


def smtp_from_email() -> str:
    return (
        os.environ.get("SMTP_FROM_EMAIL")
        or os.environ.get("SMTP_FROM")
        or smtp_login_user()
        or ""
    ).strip()


def smtp_from_display_name() -> str:
    return (os.environ.get("SMTP_FROM_NAME") or "SmartRiver System").strip()


def smtp_from_header() -> str:
    addr = smtp_from_email()
    name = smtp_from_display_name()
    if addr and name:
        return f"{name} <{addr}>"
    return addr or name or ""


def is_email_delivery_configured() -> bool:
    if (os.environ.get("SENDGRID_API_KEY") or "").strip():
        return True
    host = (os.environ.get("SMTP_HOST") or "").strip()
    return bool(host and smtp_login_user() and smtp_login_password())


def generate_otp() -> str:
    return f"{secrets.randbelow(900_000) + 100_000:06d}"


def otp_expires_at_iso() -> str:
    return (datetime.utcnow() + timedelta(minutes=get_otp_expiry_minutes())).isoformat()


def _print_dev_otp_banner(to_email: str, otp: str, purpose: str) -> None:
    mins = get_otp_expiry_minutes()
    print("=" * 60)
    print("[SMARTRIVER DEV MODE] OTP Email")
    print(f"  To      : {to_email}")
    print(f"  Purpose : {purpose}")
    print(f"  OTP Code: {otp}")
    print(f"  Expires : {mins} minutes")
    print("=" * 60)


def _otp_html_template(otp: str, purpose_label: str) -> str:
    """HTML body for verification-style OTP emails (Gmail-friendly)."""
    mins = get_otp_expiry_minutes()
    return f"""\
<html>
<body style="font-family: Arial, sans-serif; background-color: #f0f4f8; padding: 30px;">
  <div style="max-width: 500px; margin: auto; background: white;
              border-radius: 12px; padding: 35px; border-top: 6px solid #0077b6;
              box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
    <div style="text-align: center; margin-bottom: 25px;">
      <h1 style="color: #0077b6; margin: 0;">SmartRiver</h1>
      <p style="color: #666; margin: 5px 0;">Predictive River Pollution Monitoring</p>
    </div>
    <p style="color: #333; font-size: 16px;">Hello,</p>
    <p style="color: #333; font-size: 15px;">
      You requested a verification code for <strong style="color: #0077b6;">{purpose_label}</strong>.
      Use the code below to continue:
    </p>
    <div style="text-align: center; margin: 30px 0; background: #f0f8ff; border-radius: 10px;
                padding: 20px; border: 2px dashed #0077b6;">
      <p style="margin: 0; color: #666; font-size: 13px;">Your verification code</p>
      <span style="font-size: 42px; font-weight: bold; letter-spacing: 12px; color: #0077b6;">{otp}</span>
    </div>
    <p style="color: #666; font-size: 14px; text-align: center;">
      This code expires in <strong>{mins} minutes</strong>
    </p>
    <div style="background: #fff3cd; border-radius: 8px; padding: 12px; margin: 20px 0;">
      <p style="margin: 0; color: #856404; font-size: 13px;">
        If you did not request this code, please ignore this email. Do not share this code with anyone.
      </p>
    </div>
    <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
    <p style="color: #999; font-size: 12px; text-align: center; margin: 0;">
      SmartRiver System — Universiti Sains Malaysia
    </p>
  </div>
</body>
</html>
"""


def _verification_email_bodies(otp: str) -> tuple[str, str]:
    mins = get_otp_expiry_minutes()
    plain = (
        f"Your verification code is: {otp}\n\n"
        f"This code expires in {mins} minutes.\n"
        "If you did not create an account, you can ignore this email.\n"
    )
    html = _otp_html_template(otp, "email verification (registration)")
    return plain, html


def _password_reset_email_bodies(otp: str) -> tuple[str, str]:
    mins = get_otp_expiry_minutes()
    plain = (
        f"Your password reset code is: {otp}\n\n"
        f"This code expires in {mins} minutes.\n"
        "If you did not request a reset, you can ignore this email.\n"
    )
    html = _otp_html_template(otp, "password reset")
    return plain, html

def _send_raw_email(to_email: str, subject: str, plain: str, html: str | None = None) -> None:
    to_email = (to_email or "").strip()
    if not to_email:
        raise EmailSendError("Missing recipient")
    subj = (subject or "").strip() or "SmartRiver"
    plain = plain or ""

    api_key = (os.environ.get("SENDGRID_API_KEY") or "").strip()
    if api_key:
        from_addr = smtp_from_email() or to_email
        content = [{"type": "text/plain", "value": plain}]
        if html:
            content.append({"type": "text/html", "value": html})
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_addr, "name": smtp_from_display_name()},
            "subject": subj,
            "content": content,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status not in (200, 202):
                    raise EmailSendError(f"SendGrid HTTP {resp.status}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error("SendGrid error: %s %s", e.code, err_body)
            raise EmailSendError("Could not send email (SendGrid).") from e
        except OSError as e:
            logger.exception("SendGrid request failed")
            raise EmailSendError("Could not send email (network).") from e
        print(f"[EMAIL] OTP sent successfully to {to_email}")
        return

    host = (os.environ.get("SMTP_HOST") or "").strip()
    port = int((os.environ.get("SMTP_PORT") or "587").strip() or "587")
    user = smtp_login_user()
    password = smtp_login_password()
    use_tls = _env_bool("SMTP_USE_TLS", True)

    if not host or not user or not password:
        raise EmailNotConfiguredError(
            "Email is not configured on the server. "
            "Set SMTP_HOST, SMTP_USER (or SMTP_USERNAME), SMTP_PASSWORD in .env, "
            "or set SMARTRIVER_OTP_DEV_LOG=1 for development."
        )

    from_header = smtp_from_header() or user
    msg = EmailMessage()
    msg["Subject"] = subj
    msg["From"] = from_header
    msg["To"] = to_email
    msg.set_content(plain)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        if use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(host, port, timeout=30, context=ssl.create_default_context()) as server:
                server.ehlo()
                server.login(user, password)
                server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        print(
            "[EMAIL ERROR] Gmail/SMTP authentication failed. "
            "Use a Gmail App Password (16 characters), not your normal password — "
            "https://myaccount.google.com/apppasswords"
        )
        raise EmailSendError("SMTP authentication failed.") from None
    except smtplib.SMTPException as e:
        logger.exception("SMTP send failed")
        raise EmailSendError("Could not send email (SMTP).") from e
    except OSError as e:
        logger.exception("SMTP connection failed")
        raise EmailSendError("Could not send email (SMTP connection).") from e
    print(f"[EMAIL] OTP sent successfully to {to_email}")


def send_verification_otp_email(to_email: str, otp: str) -> None:
    """Send registration verification OTP, or print only in dev mode (no SMTP required)."""
    if dev_otp_log_enabled():
        _print_dev_otp_banner(to_email, otp, "registration / email verification")
        return

    if not is_email_delivery_configured():
        raise EmailNotConfiguredError(
            "Configure SENDGRID_API_KEY or SMTP (SMTP_HOST + SMTP_USER or SMTP_USERNAME + SMTP_PASSWORD), "
            "or set SMARTRIVER_OTP_DEV_LOG=1 in .env for development."
        )

    plain, html = _verification_email_bodies(otp)
    _send_raw_email(to_email, "SmartRiver — verify your email", plain, html)


def send_password_reset_otp_email(to_email: str, otp: str) -> None:
    """Send password-reset OTP, or print only in dev mode (no SMTP required)."""
    if dev_otp_log_enabled():
        _print_dev_otp_banner(to_email, otp, "password reset")
        return

    if not is_email_delivery_configured():
        raise EmailNotConfiguredError(
            "Configure SENDGRID_API_KEY or SMTP (SMTP_HOST + SMTP_USER or SMTP_USERNAME + SMTP_PASSWORD), "
            "or set SMARTRIVER_OTP_DEV_LOG=1 in .env for development."
        )

    plain, html = _password_reset_email_bodies(otp)
    _send_raw_email(to_email, "SmartRiver — reset your password", plain, html)


def send_test_otp_email(to_email: str, otp: str = "123456") -> None:
    """
    Send a one-off test message to verify Gmail/SMTP (same pipeline as verification OTP).
    Remove or disable the /test-email route in production.
    """
    if dev_otp_log_enabled():
        _print_dev_otp_banner(to_email, otp, "SMTP connectivity test")
        return
    if not is_email_delivery_configured():
        raise EmailNotConfiguredError(
            "Set SMTP_HOST, SMTP_USER (or SMTP_USERNAME), and SMTP_PASSWORD (Gmail App Password), "
            "or SENDGRID_API_KEY."
        )
    plain = (
        f"SmartRiver SMTP test.\n\nYour test code is: {otp}\n\n"
        "This is not a real account OTP; it only checks that outbound mail works.\n"
    )
    html = _otp_html_template(otp, "SMTP connectivity test")
    _send_raw_email(to_email, "SmartRiver — Your Verification Code", plain, html)


def otp_expired(expires_at_iso: str) -> bool:
    try:
        exp = datetime.fromisoformat((expires_at_iso or "").strip())
    except ValueError:
        return True
    return datetime.utcnow() > exp
