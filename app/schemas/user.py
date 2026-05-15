"""
User schemas.

Pydantic models for user data validation and serialization.
Follows the Single Responsibility Principle.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    """
    Base user schema.

    Contains common fields for all user schemas.
    """

    email: EmailStr
    username: str
    full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    """
    User creation schema.

    Validates data for creating a new user.
    """

    password: str


class UserUpdate(BaseModel):
    """
    User update schema.

    Validates data for updating an existing user.
    All fields are optional for partial updates.
    """

    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    """
    User response schema.

    Defines the structure of user data returned to clients.
    Excludes sensitive information like password.
    """

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserInDB(UserBase):
    """
    User in database schema.

    Includes all fields stored in the database.
    Used internally, not exposed to clients.
    """

    id: str
    hashed_password: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
