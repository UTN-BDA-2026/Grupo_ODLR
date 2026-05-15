"""
Repository interface.

Abstract interface for data access operations.
Follows the Interface Segregation Principle.
"""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar, Any, Dict

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class RepositoryInterface(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """
    Generic repository interface.

    Defines standard CRUD operations that any repository must implement.
    Follows the Repository Pattern for data access abstraction.
    """

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[ModelType]:
        """
        Retrieve an entity by its ID.

        Args:
            id: Entity identifier.

        Returns:
            Entity if found, None otherwise.
        """
        pass

    @abstractmethod
    async def get_by_field(
        self, field: str, value: Any, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """
        Retrieve entities by a field value.

        Args:
            field: Field name to filter by.
            value: Value to match.
            skip: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            List of matching entities.
        """
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Retrieve all entities with pagination.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            List of entities.
        """
        pass

    @abstractmethod
    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new entity.

        Args:
            obj_in: Data for the new entity.

        Returns:
            Created entity.
        """
        pass

    @abstractmethod
    async def update(self, id: str, obj_in: UpdateSchemaType) -> Optional[ModelType]:
        """
        Update an existing entity.

        Args:
            id: Entity identifier.
            obj_in: Update data.

        Returns:
            Updated entity if found, None otherwise.
        """
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """
        Delete an entity.

        Args:
            id: Entity identifier.

        Returns:
            True if deleted, False if not found.
        """
        pass

    @abstractmethod
    async def exists(self, field: str, value: Any) -> bool:
        """
        Check if an entity exists with given field value.

        Args:
            field: Field name.
            value: Value to check.

        Returns:
            True if exists, False otherwise.
        """
        pass

    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities, optionally filtered.

        Args:
            filters: Optional filter criteria.

        Returns:
            Number of matching entities.
        """
        pass
