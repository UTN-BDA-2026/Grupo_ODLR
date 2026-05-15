"""
User service.

Handles business logic for user operations.
Follows the Single Responsibility Principle.
"""

from datetime import datetime, timezone
from typing import List

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.user import UserCreateDocument, UserDocument, UserUpdateDocument
from app.core.security import hash_password
from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate, UserResponse


class UserService:
    """
    Service for user management operations.

    Encapsulates business logic for user CRUD operations.
    """

    collection_name = "users"

    def _get_repository(self, session: AsyncIOMotorDatabase) -> UserRepository:
        return UserRepository(session)

    def _hash_password(self, password: str) -> str:
        return hash_password(password)

    def _to_response(self, document: UserDocument) -> UserResponse:
        return UserResponse(
            id=document.id,
            email=document.email,
            username=document.username,
            full_name=document.full_name,
            is_active=document.is_active,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    async def create_user(
        self, session: AsyncIOMotorDatabase, user_data: UserCreate
    ) -> UserResponse:
        """
        Create a new user.

        Args:
            session: Database session
            user_data: User creation data

        Returns:
            Created user response
        """
        repository = self._get_repository(session)
        if await repository.email_exists(str(user_data.email)):
            raise ConflictException("Email already registered")
        if await repository.username_exists(user_data.username):
            raise ConflictException("Username already registered")

        now = datetime.now(timezone.utc)
        document = UserCreateDocument(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=self._hash_password(user_data.password),
            is_active=True,
            is_superuser=False,
            role_ids=[],
            created_at=now,
            updated_at=now,
        )

        created_user = await repository.create(document)
        return self._to_response(created_user)

    async def get_user_by_id(
        self, session: AsyncIOMotorDatabase, user_id: str
    ) -> UserResponse:
        """
        Get user by ID.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            User response or None if not found
        """
        repository = self._get_repository(session)
        document = await repository.get_by_id(user_id)
        if document is None:
            raise NotFoundException("User not found")

        return self._to_response(document)

    async def list_users(
        self, session: AsyncIOMotorDatabase, skip: int = 0, limit: int = 100
    ) -> List[UserResponse]:
        """
        List users with pagination.

        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of user responses
        """
        repository = self._get_repository(session)
        documents = await repository.get_all(skip=skip, limit=limit)
        return [self._to_response(document) for document in documents]

    async def update_user(
        self, session: AsyncIOMotorDatabase, user_id: str, user_data: UserUpdate
    ) -> UserResponse:
        """
        Update an existing user.

        Args:
            session: Database session
            user_id: User ID to update
            user_data: Update data

        Returns:
            Updated user response
        """
        repository = self._get_repository(session)
        existing_user = await repository.get_by_id(user_id)
        if existing_user is None:
            raise NotFoundException("User not found")

        update_data = user_data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_response(existing_user)

        email = update_data.get("email")
        if email is not None and await repository.email_exists(str(email), exclude_id=user_id):
            raise ConflictException("Email already registered")

        username = update_data.get("username")
        if username is not None and await repository.username_exists(
            username, exclude_id=user_id
        ):
            raise ConflictException("Username already registered")

        if "password" in update_data:
            update_data["hashed_password"] = self._hash_password(
                update_data.pop("password")
            )

        update_data["updated_at"] = datetime.now(timezone.utc)

        updated_user = await repository.update(
            user_id, UserUpdateDocument(**update_data)
        )
        if updated_user is None:
            raise NotFoundException("User not found")

        return self._to_response(updated_user)

    async def delete_user(self, session: AsyncIOMotorDatabase, user_id: str) -> None:
        """
        Delete a user.

        Args:
            session: Database session
            user_id: User ID to delete
        """
        repository = self._get_repository(session)
        deleted = await repository.delete(user_id)
        if not deleted:
            raise NotFoundException("User not found")


# Singleton instance
user_service = UserService()
