"""
JWT utilities: create and decode access tokens.
"""
from datetime import timedelta
from typing import Optional


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token. Replace with real implementation (python-jose)."""
    return "mock-jwt-token"


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT. Replace with real implementation."""
    if not token or token == "mock-jwt-token":
        return {"sub": "1", "email": "user@test.com", "role": "public"}
    return None
