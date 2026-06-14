# app/api/v1/endpoints/pdf.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.endpoints.auth import get_current_user
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
    current_user=Depends(get_current_user),
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
    current_user=Depends(get_current_user),
):
    return await document_service.list_documents(session, skip=skip, limit=limit)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
    current_user=Depends(get_current_user),
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
    current_user=Depends(get_current_user),
):
    try:
        return await document_service.update_document(session, document_id, data)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    try:
        await document_service.delete_document(session, document_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/upload-audited", response_model=DocumentResponse)
async def upload_pdf_audited(
    file: UploadFile = File(...),
    session: AsyncIOMotorDatabase = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """
    Sube un PDF con registro de auditoría transaccional.

    Usa una transacción MongoDB para garantizar que el documento
    y su log de auditoría se crean atómicamente.
    Si cualquiera falla, ambos se revierten (rollback automático).
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF.")

    file_bytes = await file.read()

    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="El archivo no es un PDF válido.")

    return await document_service.upload_pdf_with_audit(session, file_bytes, file.filename)