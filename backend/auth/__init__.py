"""
Auth module: JWT, login, register, dependency for current user.
"""
from backend.auth.dependencies import get_current_user, require_admin  # noqa: F401

__all__ = ["get_current_user", "require_admin"]
