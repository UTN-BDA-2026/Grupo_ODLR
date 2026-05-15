"""Internal role document models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RoleDocument(BaseModel):
    """Normalized role document stored in MongoDB."""

    id: str
    name: str
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)
    is_active: bool = True
    is_system: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleCreateDocument(BaseModel):
    """Payload used internally to persist a new role."""

    name: str
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)
    is_active: bool = True
    is_system: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleUpdateDocument(BaseModel):
    """Partial internal update payload for role documents."""

    description: Optional[str] = None
    permissions: Optional[list[str]] = None
    is_active: Optional[bool] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
