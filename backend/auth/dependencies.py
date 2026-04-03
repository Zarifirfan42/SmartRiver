"""
Auth dependencies: get_current_user, require_admin for FastAPI Depends().
Validates JWT and loads user from repository.
"""
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def user_row_is_active(row: dict) -> bool:
    """SQLite may store is_active as 0/1/NULL; .get('is_active', True) is wrong when the key exists with NULL."""
    v = row.get("is_active")
    if v is None:
        return True
    if isinstance(v, bool):
        return v
    try:
        return int(v) != 0
    except (TypeError, ValueError):
        return True


def _normalize_role(row: dict) -> str:
    """Never return None — UserResponse requires a string."""
    r = row.get("role")
    if r is None:
        return "public"
    s = str(r).strip().lower()
    if s == "admin":
        return "admin"
    return "public"


def _text_or_none(v) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        return v.strip() or None
    return str(v).strip() or None


def public_user_from_row(row: dict) -> dict:
    """Safe user dict for API responses and JWT-backed /me (no password_hash)."""
    try:
        uid = int(row["id"])
    except (KeyError, TypeError, ValueError):
        uid = 0
    return {
        "id": uid,
        "email": _text_or_none(row.get("email")),
        "full_name": _text_or_none(row.get("full_name")),
        "role": _normalize_role(row),
    }


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Validate JWT and return user dict from repository. Returns None if no token or invalid."""
    if not credentials or not credentials.credentials:
        return None
    token = (credentials.credentials or "").strip()
    if not token:
        return None
    try:
        from backend.auth.auth_service import decode_token
        from backend.db.repository import get_user_by_id

        payload = decode_token(token)
        if not payload:
            return None
        user_id = payload.get("sub")
        if user_id is None:
            return None
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return None
        user = get_user_by_id(uid)
        if not user or not user_row_is_active(user):
            return None
        return public_user_from_row(user)
    except Exception:
        logger.exception("get_current_user: unexpected error (treating as unauthenticated)")
        return None


def require_admin(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Require authenticated admin user. Raises 401/403 otherwise."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


def require_user(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Require any authenticated user. Raises 401 if not logged in."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user
