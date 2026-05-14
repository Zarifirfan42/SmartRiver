"""
Auth service — JWT creation/verification and password hashing.
Uses python-jose for JWT and passlib (bcrypt) for passwords.
"""
import os
from typing import Optional, Any
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from jose import jwt, JWTError

# Secret for JWT signing. Set JWT_SECRET_KEY in env for production.
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", os.environ.get("SECRET_KEY", "smartriver-dev-secret-change-in-production"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash password for storage. Bcrypt limits input to 72 bytes."""
    if len(password) > 72:
        password = password[:72]
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password against stored hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token. data should include 'sub' (user id) and optionally 'email', 'role'."""
    # Drop None values — some jose/JSON paths reject null claims and can raise during encode.
    to_encode = {k: v for k, v in data.items() if v is not None}
    expire_dt = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    # python-jose expects numeric exp (Unix seconds); datetime can cause encode/decode issues.
    to_encode["exp"] = int(expire_dt.timestamp())
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT. Returns payload or None if invalid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
