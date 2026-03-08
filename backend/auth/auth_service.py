"""
Auth service — User authentication and token handling.
Register, login, password hashing, JWT create/verify.
"""
from typing import Optional
from datetime import datetime, timedelta

# TODO: use passlib for password hashing, python-jose for JWT
# from passlib.context import CryptContext
# from jose import jwt


def hash_password(password: str) -> str:
    """Hash password for storage. Use bcrypt in production."""
    # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # return pwd_context.hash(password)
    return f"hashed_{password}"


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password against hash."""
    # return pwd_context.verify(plain, hashed)
    return hashed == f"hashed_{plain}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token. Use python-jose in production."""
    # to_encode = data.copy()
    # expire = datetime.utcnow() + (expires_delta or timedelta(minutes=60))
    # to_encode.update({"exp": expire})
    # return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return "mock-jwt-token"


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT. Returns payload or None."""
    if not token or token == "mock-jwt-token":
        return {"sub": "1", "email": "user@test.com", "role": "public"}
    return None
