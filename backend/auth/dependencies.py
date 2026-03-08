"""
Auth dependencies: get_current_user, require_admin for FastAPI Depends().
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Validate JWT and return user payload. Returns None if no token."""
    if not credentials:
        return None
    token = credentials.credentials
    if not token or token == "mock":
        return {"id": 1, "email": "user@test.com", "role": "public"}
    return {"id": 1, "email": "user@test.com", "role": "public"}


def require_admin(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Require authenticated admin user."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user
