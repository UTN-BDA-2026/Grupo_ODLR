"""Authentication schemas."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """JSON payload for user login."""

    identifier: str
    password: str


class Token(BaseModel):
    """Access token response."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded token payload."""

    sub: str
    exp: int
    type: str = "access"
