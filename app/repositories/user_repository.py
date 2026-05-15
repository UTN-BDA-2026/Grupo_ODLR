"""MongoDB repository for users."""

from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.interfaces.repository import RepositoryInterface
from app.models.user import UserCreateDocument, UserDocument, UserUpdateDocument


class UserRepository(
    RepositoryInterface[UserDocument, UserCreateDocument, UserUpdateDocument]
):
    """Repository responsible for user persistence."""

    collection_name = "users"

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[self.collection_name]

    def _parse_object_id(self, id: str) -> ObjectId | None:
        try:
            return ObjectId(id)
        except InvalidId:
            return None

    def _to_model(self, document: dict | None) -> UserDocument | None:
        if document is None:
            return None

        return UserDocument(
            id=str(document["_id"]),
            email=document["email"],
            username=document["username"],
            full_name=document.get("full_name"),
            hashed_password=document["hashed_password"],
            is_active=document.get("is_active", True),
            is_superuser=document.get("is_superuser", False),
            role_ids=[str(role_id) for role_id in document.get("role_ids", [])],
            created_at=document["created_at"],
            updated_at=document["updated_at"],
        )

    async def get_by_id(self, id: str) -> Optional[UserDocument]:
        object_id = self._parse_object_id(id)
        if object_id is None:
            return None

        return self._to_model(await self.collection.find_one({"_id": object_id}))

    async def get_by_field(
        self, field: str, value: Any, skip: int = 0, limit: int = 100
    ) -> list[UserDocument]:
        cursor = self.collection.find({field: value}).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._to_model(document) for document in documents]

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[UserDocument]:
        cursor = self.collection.find({}).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [self._to_model(document) for document in documents]

    async def create(self, obj_in: UserCreateDocument) -> UserDocument:
        document = obj_in.model_dump()
        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return self._to_model(document)

    async def update(self, id: str, obj_in: UserUpdateDocument) -> Optional[UserDocument]:
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

    async def get_by_email(self, email: str) -> Optional[UserDocument]:
        return self._to_model(await self.collection.find_one({"email": email}))

    async def get_by_username(self, username: str) -> Optional[UserDocument]:
        return self._to_model(await self.collection.find_one({"username": username}))

    async def get_by_identifier(self, identifier: str) -> Optional[UserDocument]:
        return self._to_model(
            await self.collection.find_one(
                {"$or": [{"email": identifier}, {"username": identifier}]}
            )
        )

    async def email_exists(self, email: str, exclude_id: str | None = None) -> bool:
        query: dict[str, Any] = {"email": email}
        if exclude_id is not None:
            object_id = self._parse_object_id(exclude_id)
            if object_id is not None:
                query["_id"] = {"$ne": object_id}

        return await self.collection.find_one(query) is not None

    async def username_exists(
        self, username: str, exclude_id: str | None = None
    ) -> bool:
        query: dict[str, Any] = {"username": username}
        if exclude_id is not None:
            object_id = self._parse_object_id(exclude_id)
            if object_id is not None:
                query["_id"] = {"$ne": object_id}

        return await self.collection.find_one(query) is not None
