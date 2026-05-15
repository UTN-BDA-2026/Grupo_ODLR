"""Internal document models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DocumentDocument(BaseModel):
    """Normalized document stored in MongoDB."""

    id: str
    filename: str
    text: str
    checksum: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentCreateDocument(BaseModel):
    """Payload used internally to persist a new document."""

    filename: str
    text: str
    checksum: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentUpdateDocument(BaseModel):
    """Partial internal update payload for document records."""

    filename: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
