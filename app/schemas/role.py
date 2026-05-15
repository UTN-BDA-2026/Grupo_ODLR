"""Role schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RoleBase(BaseModel):
    """Base role schema."""

    name: str
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(RoleBase):
    """Role creation schema."""


class RoleUpdate(BaseModel):
    """Role update schema."""

    description: Optional[str] = None
    permissions: Optional[list[str]] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(RoleBase):
    """Role response schema."""

    id: str
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleInDB(RoleBase):
    """Role document schema used internally."""

    id: str
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
