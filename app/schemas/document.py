# app/schemas/document.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "filename": "documento.pdf",
                "text": "Contenido del PDF extraído...",
                "checksum": "Numero checksum SHA-256 del PDF",
            }
        }
    )

    id: str = Field(..., description="MongoDB document ID")
    filename: str = Field(..., description="Nombre original del archivo PDF")
    checksum: str = Field(..., description="Checksum SHA-256 del contenido del PDF")
    text: str = Field(..., description="Texto extraído del PDF")


class DocumentResponse(BaseModel):
    """Response schema for document CRUD operations."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="MongoDB document ID")
    filename: str = Field(..., description="Nombre original del archivo PDF")
    checksum: str = Field(..., description="Checksum SHA-256 del contenido del PDF")
    text: str = Field(..., description="Texto extraído del PDF")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")


class DocumentUpdate(BaseModel):
    """Request body for updating a document."""

    filename: Optional[str] = Field(None, description="Nuevo nombre del archivo")
