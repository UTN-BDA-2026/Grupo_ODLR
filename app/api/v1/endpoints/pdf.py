# app/api/v1/endpoints/pdf.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.exceptions import ConflictException, NotFoundException
from app.db.database import get_db_session
from app.schemas.document import DocumentResponse, DocumentUpdate
from app.services.document_service import document_service

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    session: AsyncIOMotorDatabase = Depends(get_db_session),
):
    if not file.filename.endswith(".pdf") or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser un PDF válido",
        )

    pdf_bytes = await file.read()

    if len(pdf_bytes) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"El archivo supera el tamaño máximo de "
                   f"{settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    try:
        return await document_service.upload_pdf(session, pdf_bytes, file.filename)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El contenido del archivo no es un PDF válido",
        )


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
):
    return await document_service.list_documents(session, skip=skip, limit=limit)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
):
    try:
        return await document_service.get_document_by_id(session, document_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    data: DocumentUpdate,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
):
    try:
        return await document_service.update_document(session, document_id, data)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
):
    try:
        await document_service.delete_document(session, document_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
