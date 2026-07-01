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
from app.services.ollama_service import ollama_service

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
            detail="El archivo debe ser un PDF vÃ¡lido",
        )

    pdf_bytes = await file.read()

    if len(pdf_bytes) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"El archivo supera el tamaÃ±o mÃ¡ximo de "
                   f"{settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    try:
        return await document_service.upload_pdf(session, pdf_bytes, file.filename, current_user.id)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El contenido del archivo no es un PDF vÃ¡lido",
        )


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 0,
    search: str | None = None,
    order: str = "desc",
    session: AsyncIOMotorDatabase = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await document_service.list_documents(
        session, owner_id=current_user.id, skip=skip, limit=limit, search=search, order=order
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    try:
        return await document_service.get_document_by_id(session, document_id, current_user.id)
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
        return await document_service.update_document(session, document_id, data, current_user.id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    try:
        await document_service.delete_document(session, document_id, current_user.id)
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

    Usa una transaccion MongoDB para garantizar que el documento
    y su log de auditori­a se crean automaticamente.
    Si cualquiera falla, ambos se revierten (rollback automÃ¡tico).
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF.")

    file_bytes = await file.read()

    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="El archivo no es un PDF válido.")

    try:
        return await document_service.upload_pdf_with_audit(session, file_bytes, file.filename, current_user.id)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.post("/{document_id}/summary")
async def summarize_pdf(
    document_id: str,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Genera un resumen del PDF usando Ollama (llama3.2:3b)."""
    # 1. Buscar el documento
    try:
        doc = await document_service.get_document_by_id(session, document_id, current_user.id)
    except NotFoundException:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # 2. Verificar que tenga texto extraido
    if not doc.text:
        raise HTTPException(status_code=400, detail="El documento no tiene texto extraido")

    # 3. Llamar a Ollama
    try:
        summary = await ollama_service.summarize(doc.text)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama no disponible: {str(e)}")

    return {"document_id": document_id, "summary": summary}