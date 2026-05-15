"""MongoDB repository for roles."""

from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.interfaces.repository import RepositoryInterface
from app.models.role import RoleCreateDocument, RoleDocument, RoleUpdateDocument


class RoleRepository(
    RepositoryInterface[RoleDocument, RoleCreateDocument, RoleUpdateDocument]
):
    """Repository responsible for role persistence."""

    collection_name = "roles"

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[self.collection_name]

    def _parse_object_id(self, id: str) -> ObjectId | None:
        try:
            return ObjectId(id)
        except InvalidId:
            return None

    def _to_model(self, document: dict | None) -> RoleDocument | None:
        if document is None:
            return None

        return RoleDocument(
            id=str(document["_id"]),
            name=document["name"],
            description=document.get("description"),
            permissions=document.get("permissions", []),
            is_active=document.get("is_active", True),
            is_system=document.get("is_system", False),
            created_at=document["created_at"],
            updated_at=document["updated_at"],
        )

    async def get_by_id(self, id: str) -> Optional[RoleDocument]:
        object_id = self._parse_object_id(id)
        if object_id is None:
            return None

        return self._to_model(await self.collection.find_one({"_id": object_id}))

    async def get_by_field(
        self, field: str, value: Any, skip: int = 0, limit: int = 100
    ) -> list[RoleDocument]:
        cursor = self.collection.find({field: value}).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._to_model(document) for document in documents]

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[RoleDocument]:
        cursor = self.collection.find({}).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._to_model(document) for document in documents]

    async def create(self, obj_in: RoleCreateDocument) -> RoleDocument:
        document = obj_in.model_dump()
        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return self._to_model(document)

    async def update(self, id: str, obj_in: RoleUpdateDocument) -> Optional[RoleDocument]:
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

    async def get_by_name(self, name: str) -> Optional[RoleDocument]:
        return self._to_model(await self.collection.find_one({"name": name}))
