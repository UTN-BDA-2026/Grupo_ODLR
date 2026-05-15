"""Security helpers for password hashing and JWT handling."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its stored hash."""
    return pwd_context.verify(password, hashed_password)


def create_access_token(
    subject: str, expires_delta: timedelta | None = None
) -> str:
    """Create a signed JWT access token for the given subject."""
    expires_in = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire_at = datetime.now(timezone.utc) + expires_in
    payload = {
        "sub": subject,
        "exp": expire_at,
        "type": "access",
    }
    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except ExpiredSignatureError as exc:
        raise UnauthorizedException("Token has expired") from exc
    except InvalidTokenError as exc:
        raise UnauthorizedException("Invalid authentication token") from exc

    if payload.get("type") != "access" or not payload.get("sub"):
        raise UnauthorizedException("Invalid authentication token")

    return payload
