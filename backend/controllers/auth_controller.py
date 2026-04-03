"""
Auth controller — Login, register, and current user (JWT).
"""
import logging
import sqlite3
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr

from backend.auth.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
)
from backend.auth.dependencies import (
    get_current_user,
    require_user,
    public_user_from_row,
    user_row_is_active,
)
from backend.db.repository import get_user_by_email, create_user, update_user_password_by_email

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str
    confirm_password: str


class UserResponse(BaseModel):
    id: int
    email: str | None
    full_name: str | None
    role: str


def _login_handler(body: LoginRequest) -> dict:
    print(
        "📥 Login request received:",
        {"email": (body.email or "").strip(), "password_provided": bool(body.password)},
    )
    email = (body.email or "").strip().lower()
    if not email or not body.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password required")

    print("🔍 Checking user in DB:", email)
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
        print("🔍 User lookup result: not found")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    print("🔍 User lookup result: found id=", user.get("id"))
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
        print("🔐 Password verify completed:", ok)
    except Exception as pe:
        print("❌ LOGIN ERROR (password verify):", str(pe))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

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
    print("✅ Login success for:", safe.get("email"))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": safe,
    }


@router.post("/login")
def login(body: LoginRequest):
    """
    Authenticate with email and password. Returns JWT and user info.
    """
    try:
        return _login_handler(body)
    except HTTPException:
        raise
    except Exception as e:
        print("❌ LOGIN ERROR:", str(e))
        logger.exception("login: unexpected error")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication temporarily unavailable. Please try again.",
        )


@router.post("/register")
def register(body: RegisterRequest):
    """
    Register a new user (role: public). Returns JWT and user info.
    """
    email = (body.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email required")
    if not body.password or len(body.password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters")

    try:
        user = create_user(
            email=email,
            password_hash=hash_password(body.password),
            full_name=body.full_name or None,
            role="public",
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

    safe = public_user_from_row(user)
    try:
        token = create_access_token(
            data={"sub": str(safe["id"]), "email": safe.get("email"), "role": safe["role"]}
        )
    except Exception:
        logger.exception("register: create_access_token failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable. Please try again.",
        )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": safe,
    }


@router.get("/me", response_model=UserResponse)
def get_me(user: dict = Depends(require_user)):
    """Return current user from JWT. 401 if not authenticated."""
    try:
        return UserResponse(
            id=int(user["id"]),
            email=user.get("email"),
            full_name=user.get("full_name"),
            role=str(user.get("role") or "public"),
        )
    except Exception:
        logger.exception("get_me: response build failed for user_id=%s", user.get("id"))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load user profile. Please sign in again.",
        )


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest):
    """
    Forgot password: set new password by email. No login required.
    Checks email exists, validates new_password == confirm_password, hashes with bcrypt, updates in DB.
    """
    email = (body.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email required")
    if not body.new_password or len(body.new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 6 characters")
    if body.new_password != body.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    updated = update_user_password_by_email(email, hash_password(body.new_password))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
    return {"message": "Password reset successful. Please login."}
