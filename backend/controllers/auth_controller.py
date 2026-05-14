"""
Auth controller — Login, register, email verification OTP, password reset OTP.
"""
import logging
import os
import re
import sqlite3
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status, Depends
from pydantic import BaseModel, EmailStr

from backend.auth.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
)
from backend.auth.dependencies import (
    require_user,
    public_user_from_row,
    user_row_email_verified,
    user_row_is_active,
)
from backend.db.repository import (
    AUTH_OTP_PURPOSE_RESET,
    AUTH_OTP_PURPOSE_VERIFY,
    create_user,
    delete_auth_otp_row,
    delete_user_by_email,
    get_auth_otp_row,
    get_user_by_email,
    set_user_email_verified,
    update_last_login,
    update_user_password_by_email,
    upsert_auth_otp,
)
from backend.services.email_service import (
    EmailNotConfiguredError,
    EmailSendError,
    dev_otp_log_enabled,
    generate_otp,
    is_email_delivery_configured,
    otp_expired,
    otp_expires_at_iso,
    send_password_reset_otp_email,
    send_test_otp_email,
    send_verification_otp_email,
)

logger = logging.getLogger(__name__)

router = APIRouter()

CODE_SENT_MESSAGE = "Verification code sent to your email."


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str
    confirm_password: str


class UserResponse(BaseModel):
    id: int
    email: str | None
    username: str | None = None
    full_name: str | None
    role: str
    last_login_date: str | None = None
    email_verified: bool = True


def _normalize_email(raw: str) -> str:
    return (raw or "").strip().lower()


def _normalize_otp(raw: str) -> str:
    s = re.sub(r"\s+", "", (raw or "").strip())
    return s


def _test_email_endpoint_allowed() -> bool:
    """Avoid open relay in production unless explicitly enabled."""
    if (os.environ.get("APP_ENV") or "").strip().lower() == "production":
        return (os.environ.get("SMARTRIVER_ALLOW_TEST_EMAIL") or "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
    return True


@router.get("/test-email")
def test_email_sending(email: str = Query(..., description="Recipient inbox to receive a test OTP email")):
    """
    Temporary: verify Gmail/SMTP without full registration.
    Disabled when APP_ENV=production unless SMARTRIVER_ALLOW_TEST_EMAIL=1.

    Correct URL (this app mounts auth under /api/v1):
    http://localhost:8000/api/v1/auth/test-email?email=you@gmail.com
    """
    if not _test_email_endpoint_allowed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test email is disabled in production. Set SMARTRIVER_ALLOW_TEST_EMAIL=1 to allow.",
        )
    to = _normalize_email(email)
    if not to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email query parameter required")
    test_otp = "123456"
    try:
        send_test_otp_email(to, test_otp)
    except EmailNotConfiguredError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    except EmailSendError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email sending failed: {e}",
        ) from e
    return {
        "status": "success",
        "message": f"Test email sent to {to}. Check inbox (and spam).",
        "dev_mode": dev_otp_log_enabled(),
    }


def _registration_otp_email_task(email: str, otp: str) -> None:
    """Runs after HTTP response; SMTP must not block /auth/register."""
    try:
        send_verification_otp_email(email, otp)
    except EmailNotConfiguredError as e:
        logger.error("registration OTP: email not available post-response: %s", e)
        delete_user_by_email(email)
    except EmailSendError:
        logger.exception("registration OTP: send failed; removing unverified user %s", email)
        delete_user_by_email(email)


def _verification_resend_email_task(email: str, otp: str) -> None:
    try:
        send_verification_otp_email(email, otp)
    except EmailNotConfiguredError:
        logger.error("resend verification: email not configured for %s", email)
    except EmailSendError:
        logger.exception("resend verification: send failed for %s", email)


def _password_reset_email_task(email: str, otp: str) -> None:
    try:
        send_password_reset_otp_email(email, otp)
    except EmailNotConfiguredError:
        logger.error("password reset OTP: email not configured for %s", email)
    except EmailSendError:
        logger.exception("password reset OTP: send failed for %s", email)


def _login_handler(body: LoginRequest) -> dict:
    email = _normalize_email(body.email)
    if not email or not body.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password required")

    try:
        user = get_user_by_email(email)
    except sqlite3.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication database is temporarily unavailable. Please try again.",
        )
    except Exception:
        logger.exception("login: get_user_by_email failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication database is temporarily unavailable. Please try again.",
        )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user_row_is_active(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    password_hash = user.get("password_hash")
    if not password_hash or not isinstance(password_hash, (str, bytes)):
        logger.error("login: user %s has missing or invalid password_hash", email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if isinstance(password_hash, bytes):
        try:
            password_hash = password_hash.decode("utf-8")
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    try:
        ok = verify_password(body.password, password_hash)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user_row_email_verified(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email using the code we sent.",
        )

    safe = public_user_from_row(user)
    try:
        token = create_access_token(
            data={"sub": str(safe["id"]), "email": safe.get("email"), "role": safe["role"]}
        )
    except Exception:
        logger.exception("login: create_access_token failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable. Please try again.",
        )
    try:
        update_last_login(int(safe["id"]))
        refreshed = get_user_by_email(safe.get("email") or "")
        if refreshed:
            safe = public_user_from_row(refreshed)
    except Exception:
        logger.exception("login: update_last_login skipped")
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": safe,
    }


@router.post("/login")
def login(body: LoginRequest):
    """Authenticate with email and password. Returns JWT and user info."""
    try:
        return _login_handler(body)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("login: unexpected error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication temporarily unavailable. Please try again.",
        )


@router.post("/register")
async def register(body: RegisterRequest, background_tasks: BackgroundTasks):
    """
    Register a new public user. Creates the account (unverified), stores a hashed OTP in SQLite
    (table auth_email_otp), and queues OTP delivery in a background task so this handler returns immediately.
    SMTP/SendGrid/console OTP runs after the response is sent.
    Complete activation with POST /auth/verify-email.
    """
    email = _normalize_email(str(body.email))
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email required")
    if not body.password or len(body.password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters")

    if not dev_otp_log_enabled() and not is_email_delivery_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Email is not configured on the server. "
                "Add SMARTRIVER_OTP_DEV_LOG=1 to .env for console OTP, "
                "or set SMTP_HOST + SMTP_USER (or SMTP_USERNAME) + SMTP_PASSWORD, "
                "or SENDGRID_API_KEY."
            ),
        )

    try:
        user = create_user(
            email=email,
            password_hash=hash_password(body.password),
            full_name=body.full_name or None,
            role="public",
            email_verified=False,
        )
    except ValueError as e:
        if "already registered" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except sqlite3.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication database is temporarily unavailable. Please try again.",
        )

    otp = generate_otp()
    otp_hash = hash_password(otp)
    upsert_auth_otp(email, AUTH_OTP_PURPOSE_VERIFY, otp_hash, otp_expires_at_iso())

    background_tasks.add_task(_registration_otp_email_task, email, otp)

    _ = user  # created row stays unverified
    return {
        "message": CODE_SENT_MESSAGE,
        "requires_verification": True,
        "email": email,
    }


@router.post("/verify-email")
def verify_email(body: VerifyEmailRequest):
    """Submit the 6-digit OTP from email; returns JWT when verified."""
    email = _normalize_email(str(body.email))
    otp = _normalize_otp(body.otp)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email required")
    if not otp or len(otp) != 6 or not otp.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter the 6-digit verification code")

    try:
        user = get_user_by_email(email)
    except sqlite3.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication database is temporarily unavailable. Please try again.",
        )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    if user_row_email_verified(user):
        safe = public_user_from_row(user)
        token = create_access_token(
            data={"sub": str(safe["id"]), "email": safe.get("email"), "role": safe["role"]}
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": safe,
            "message": "Email already verified.",
        }

    row = get_auth_otp_row(email, AUTH_OTP_PURPOSE_VERIFY)
    if not row or otp_expired(row["expires_at"]):
        if row:
            delete_auth_otp_row(email, AUTH_OTP_PURPOSE_VERIFY)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code. Request a new code.",
        )

    try:
        ok = verify_password(otp, row["otp_hash"])
    except Exception:
        ok = False
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")

    delete_auth_otp_row(email, AUTH_OTP_PURPOSE_VERIFY)
    set_user_email_verified(int(user["id"]), True)

    refreshed = get_user_by_email(email)
    safe = public_user_from_row(refreshed or user)
    try:
        token = create_access_token(
            data={"sub": str(safe["id"]), "email": safe.get("email"), "role": safe["role"]}
        )
    except Exception:
        logger.exception("verify-email: create_access_token failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable. Please try again.",
        )
    try:
        update_last_login(int(safe["id"]))
    except Exception:
        logger.exception("verify-email: update_last_login skipped")

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": safe,
        "message": "Email verified.",
    }


@router.post("/resend-verification")
async def resend_verification(body: ResendVerificationRequest, background_tasks: BackgroundTasks):
    """Resend verification OTP for an unverified account (OTP send runs in background)."""
    email = _normalize_email(str(body.email))
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email required")

    user = get_user_by_email(email)
    if not user:
        return {"message": CODE_SENT_MESSAGE}

    if user_row_email_verified(user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified")

    if not dev_otp_log_enabled() and not is_email_delivery_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email is not configured on the server.",
        )

    otp = generate_otp()
    upsert_auth_otp(email, AUTH_OTP_PURPOSE_VERIFY, hash_password(otp), otp_expires_at_iso())
    background_tasks.add_task(_verification_resend_email_task, email, otp)

    return {"message": CODE_SENT_MESSAGE}


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    """Request password-reset OTP (same response whether or not the email exists). Send runs in background."""
    email = _normalize_email(body.email)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email required")

    user = get_user_by_email(email)
    if user:
        if not dev_otp_log_enabled() and not is_email_delivery_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email is not configured on the server.",
            )
        otp = generate_otp()
        upsert_auth_otp(email, AUTH_OTP_PURPOSE_RESET, hash_password(otp), otp_expires_at_iso())
        background_tasks.add_task(_password_reset_email_task, email, otp)

    return {"message": CODE_SENT_MESSAGE}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest):
    """Reset password using email + OTP from /auth/forgot-password."""
    email = _normalize_email(body.email)
    otp = _normalize_otp(body.otp)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email required")
    if not otp or len(otp) != 6 or not otp.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter the 6-digit code from your email")
    if not body.new_password or len(body.new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 6 characters")
    if body.new_password != body.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset code")

    row = get_auth_otp_row(email, AUTH_OTP_PURPOSE_RESET)
    if not row or otp_expired(row["expires_at"]):
        if row:
            delete_auth_otp_row(email, AUTH_OTP_PURPOSE_RESET)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset code")

    try:
        ok = verify_password(otp, row["otp_hash"])
    except Exception:
        ok = False
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset code")

    delete_auth_otp_row(email, AUTH_OTP_PURPOSE_RESET)
    updated = update_user_password_by_email(email, hash_password(body.new_password))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    return {"message": "Password reset successful. Please login."}


@router.get("/me", response_model=UserResponse)
def get_me(user: dict = Depends(require_user)):
    """Return current user from JWT. 401 if not authenticated."""
    try:
        return UserResponse(
            id=int(user["id"]),
            email=user.get("email"),
            username=user.get("username"),
            full_name=user.get("full_name"),
            role=str(user.get("role") or "public"),
            last_login_date=user.get("last_login_date"),
            email_verified=bool(user.get("email_verified", True)),
        )
    except Exception:
        logger.exception("get_me: response build failed for user_id=%s", user.get("id"))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load user profile. Please sign in again.",
        )
