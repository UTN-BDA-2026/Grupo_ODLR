"""Internal user document models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserDocument(BaseModel):
    """Normalized user document stored in MongoDB."""

    id: str
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    role_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreateDocument(BaseModel):
    """Payload used internally to persist a new user."""

    email: EmailStr
    username: str
    full_name: Optional[str] = None
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    role_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdateDocument(BaseModel):
    """Partial internal update payload for user documents."""

    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    hashed_password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    role_ids: Optional[list[str]] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
