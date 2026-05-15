"""
Schemas module.

Contains Pydantic models for data validation and serialization.
Follows the Data Transfer Object pattern.
"""

from app.schemas.auth import LoginRequest, Token, TokenPayload
from app.schemas.role import RoleCreate, RoleInDB, RoleResponse, RoleUpdate
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserInDB

__all__ = [
    "LoginRequest",
    "RoleCreate",
    "RoleInDB",
    "RoleResponse",
    "RoleUpdate",
    "Token",
    "TokenPayload",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
]
