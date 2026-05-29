"""Document service.

Handles business logic for PDF document CRUD operations.
"""

from datetime import datetime, timezone
from typing import List

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import ConflictException, NotFoundException
from app.db.database import db as mongo_db  # instancia singleton de MongoDatabase
from app.models.document import DocumentCreateDocument, DocumentDocument, DocumentUpdateDocument
from app.repositories.audit_repository import AuditRepository
from app.repositories.document_repo import DocumentRepository
from app.schemas.document import DocumentResponse, DocumentUpdate
from app.services.pdf_service import calculate_checksum, extract_text_from_bytes



class DocumentService:
    """Service for PDF document CRUD operations."""

    def _get_repository(self, session: AsyncIOMotorDatabase) -> DocumentRepository:
        return DocumentRepository(session)

    def _to_response(self, document: DocumentDocument) -> DocumentResponse:
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            text=document.text,
            checksum=document.checksum,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    async def upload_pdf(
        self, session: AsyncIOMotorDatabase, file_bytes: bytes, filename: str
    ) -> DocumentResponse:
        repository = self._get_repository(session)

        checksum = calculate_checksum(file_bytes)
        existing = await repository.find_by_checksum(checksum)
        if existing:
            raise ConflictException(
                f"El documento ya existe en la base de datos con id: {existing.id}"
            )

        text = extract_text_from_bytes(file_bytes)

        now = datetime.now(timezone.utc)
        create_doc = DocumentCreateDocument(
            filename=filename,
            text=text,
            checksum=checksum,
            created_at=now,
            updated_at=now,
        )
        created = await repository.create(create_doc)
        return self._to_response(created)

    async def upload_pdf_with_audit(
        self,
        session: AsyncIOMotorDatabase,
        file_bytes: bytes,
        filename: str,
    ) -> DocumentResponse:
        """
        Sube un PDF y registra auditoría en una transacción atómica.

        Garantía ACID: si cualquiera de las dos operaciones falla,
        ambas se revierten. No puede quedar un documento sin su
        registro de auditoría ni viceversa.

        La diferencia con upload_pdf es que este método abre una
        transacción multi-documento usando start_transaction().
        """
        # Validaciones ANTES de la transacción
        # (mantener las transacciones lo más cortas posible)
        checksum = calculate_checksum(file_bytes)
        repository = self._get_repository(session)

        existing = await repository.find_by_checksum(checksum)
        if existing:
            raise ConflictException(
                f"El documento ya existe con id: {existing.id}"
            )

        text = extract_text_from_bytes(file_bytes)
        now = datetime.now(timezone.utc)

        # Abrir transacción usando el start_transaction() de MongoDatabase
        async with mongo_db.start_transaction() as tx_session:

            # Operación 1: insertar documento
            create_data = DocumentCreateDocument(
                filename=filename,
                text=text,
                checksum=checksum,
                created_at=now,
                updated_at=now,
            ).model_dump()

            result = await mongo_db.get_database()["documents"].insert_one(
                create_data, session=tx_session
            )

            # Operación 2: registrar auditoría
            # Si esta línea falla → la Operación 1 también se revierte
            audit_repo = AuditRepository(session)
            await audit_repo.log(
                action="upload",
                document_id=str(result.inserted_id),
                filename=filename,
                checksum=checksum,
                session=tx_session,
            )

        # Retornar el documento creado
        created_doc = DocumentDocument(
            id=str(result.inserted_id),
            filename=filename,
            text=text,
            checksum=checksum,
            created_at=now,
            updated_at=now,
        )
        return self._to_response(created_doc)

    async def get_document_by_id(
        self, session: AsyncIOMotorDatabase, doc_id: str
    ) -> DocumentResponse:
        repository = self._get_repository(session)
        document = await repository.get_by_id(doc_id)
        if document is None:
            raise NotFoundException("Document not found")
        return self._to_response(document)

    async def list_documents(
        self, session: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100
    ) -> List[DocumentResponse]:
        repository = self._get_repository(session)
        documents = await repository.get_all(skip=skip, limit=limit)
        return [self._to_response(doc) for doc in documents]

    async def update_document(
        self, session: AsyncIOMotorDatabase, doc_id: str, data: DocumentUpdate
    ) -> DocumentResponse:
        repository = self._get_repository(session)
        existing = await repository.get_by_id(doc_id)
        if existing is None:
            raise NotFoundException("Document not found")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_response(existing)

        update_data["updated_at"] = datetime.now(timezone.utc)
        updated = await repository.update(doc_id, DocumentUpdateDocument(**update_data))
        if updated is None:
            raise NotFoundException("Document not found")

        return self._to_response(updated)

    async def delete_document(
        self, session: AsyncIOMotorDatabase, doc_id: str
    ) -> None:
        repository = self._get_repository(session)
        deleted = await repository.delete(doc_id)
        if not deleted:
            raise NotFoundException("Document not found")


document_service = DocumentService()