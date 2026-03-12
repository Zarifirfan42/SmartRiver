"""
Auth controller — Login, register, and current user (JWT).
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr

from backend.auth.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
)
from backend.auth.dependencies import get_current_user, require_user
from backend.db.repository import get_user_by_email, create_user

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str | None
    full_name: str | None
    role: str


@router.post("/login")
def login(body: LoginRequest):
    """
    Authenticate with email and password. Returns JWT and user info.
    """
    email = (body.email or "").strip().lower()
    if not email or not body.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password required")

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(
        data={"sub": str(user["id"]), "email": user.get("email"), "role": user.get("role", "public")}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user.get("email"),
            "full_name": user.get("full_name"),
            "role": user.get("role", "public"),
        },
    }


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

    token = create_access_token(
        data={"sub": str(user["id"]), "email": user.get("email"), "role": user.get("role", "public")}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user.get("email"),
            "full_name": user.get("full_name"),
            "role": user.get("role", "public"),
        },
    }


@router.get("/me", response_model=UserResponse)
def get_me(user: dict = Depends(require_user)):
    """Return current user from JWT. 401 if not authenticated."""
    return user
