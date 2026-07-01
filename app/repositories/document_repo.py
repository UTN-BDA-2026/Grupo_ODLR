# app/repositories/document_repo.py

import re
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.interfaces.repository import RepositoryInterface
from app.models.document import DocumentCreateDocument, DocumentDocument, DocumentUpdateDocument
from bson import ObjectId


class DocumentRepository(
    RepositoryInterface[DocumentDocument, DocumentCreateDocument, DocumentUpdateDocument]
):
    """Repository responsible for document persistence."""

    collection_name = "documents"

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[self.collection_name]

    def _parse_object_id(self, id: str) -> ObjectId | None:
        try:
            return ObjectId(id)
        except InvalidId:
            return None

    def _to_model(self, document: dict | None) -> DocumentDocument | None:
        if document is None:
            return None

        return DocumentDocument(
            id=str(document["_id"]),
            filename=document["filename"],
            text=document["text"],
            checksum=document["checksum"],
            owner_id=document.get("owner_id", ""),
            created_at=document.get("created_at", datetime.min),
            updated_at=document.get("updated_at", datetime.min),
        )

    async def get_by_id(self, id: str) -> Optional[DocumentDocument]:
        object_id = self._parse_object_id(id)
        if object_id is None:
            return None

        return self._to_model(await self.collection.find_one({"_id": object_id}))

    async def get_by_field(
        self, field: str, value: Any, skip: int = 0, limit: int = 0
    ) -> list[DocumentDocument]:
        cursor = self.collection.find({field: value}).skip(skip).limit(limit)
        documents = await cursor.to_list(length=None)
        return [self._to_model(doc) for doc in documents]

    async def get_all(self, skip: int = 0, limit: int = 0) -> list[DocumentDocument]:
        cursor = self.collection.find({}).skip(skip).limit(limit)
        documents = await cursor.to_list(length=None)
        return [self._to_model(doc) for doc in documents]

    async def get_by_owner(
        self,
        owner_id: str,
        skip: int = 0,
        limit: int = 0,
        search: Optional[str] = None,
        order: str = "desc",
    ) -> list[DocumentDocument]:
        query: dict[str, Any] = {"owner_id": owner_id}
        if search:
            query["filename"] = {"$regex": re.escape(search), "$options": "i"}

        direction = -1 if order == "desc" else 1
        cursor = (
            self.collection.find(query)
            .sort("created_at", direction)
            .skip(skip)
            .limit(limit)
        )
        documents = await cursor.to_list(length=None)
        return [self._to_model(doc) for doc in documents]

    async def list_all(
        self,
        owner_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 0,
        search: Optional[str] = None,
        order: str = "desc",
    ) -> list[DocumentDocument]:
        """Listado de documentos para el panel administrativo.

        Si se pasa owner_id, el filtro por propietario + sort por created_at
        usa el índice compuesto ix_documents_owner_created {owner_id, created_at}.
        Sin owner_id se recorre toda la colección (vista global de admin):
        el filename usa $regex no anclado, que no aprovecha índice.
        """
        query: dict[str, Any] = {}
        if owner_id:
            query["owner_id"] = owner_id
        if search:
            query["filename"] = {"$regex": re.escape(search), "$options": "i"}

        direction = -1 if order == "desc" else 1
        cursor = (
            self.collection.find(query)
            .sort("created_at", direction)
            .skip(skip)
            .limit(limit)
        )
        documents = await cursor.to_list(length=None)
        return [self._to_model(doc) for doc in documents]

    async def create(self, obj_in: DocumentCreateDocument) -> DocumentDocument:
        document = obj_in.model_dump()
        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return self._to_model(document)

    async def update(self, id: str, obj_in: DocumentUpdateDocument) -> Optional[DocumentDocument]:
        object_id = self._parse_object_id(id)
        if object_id is None:
            return None

        update_data = obj_in.model_dump(exclude_unset=True, exclude_none=True)
        if update_data:
            await self.collection.update_one({"_id": object_id}, {"$set": update_data})

        return await self.get_by_id(id)

    async def delete(self, id: str) -> bool:
        object_id = self._parse_object_id(id)
        if object_id is None:
            return False

        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    async def exists(self, field: str, value: Any) -> bool:
        return await self.collection.find_one({field: value}) is not None

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        return await self.collection.count_documents(filters or {})

    async def find_by_checksum_and_owner(self, checksum: str, owner_id: str) -> Optional[DocumentDocument]:
        return self._to_model(await self.collection.find_one({"checksum": checksum, "owner_id": owner_id}))
    
    async def find_by_id(self, document_id: str) -> dict | None:
        return await self.collection.find_one({"_id": ObjectId(document_id)})

    async def update_summary(self, document_id: str, summary: str) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"summary": summary}}
        )