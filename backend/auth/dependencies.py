"""
Auth dependencies: get_current_user, require_admin for FastAPI Depends().
Validates JWT and loads user from repository.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer

security = HTTPBearer(auto_error=False)

# Optional: use OAuth2PasswordBearer if you want to support form/login in Swagger
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Validate JWT and return user dict from repository. Returns None if no token or invalid."""
    if not credentials or not credentials.credentials:
        return None
    token = credentials.credentials
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
    if not user or not user.get("is_active", True):
        return None
    # Return a safe dict for route handlers (no password_hash)
    return {
        "id": user["id"],
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "role": user.get("role", "public"),
    }


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
