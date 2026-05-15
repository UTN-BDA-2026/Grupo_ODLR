"""
Database interface.

Abstract interface for database operations.
Follows the Interface Segregation Principle.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Optional


class DatabaseInterface(ABC):
    """
    Abstract interface for database connections.

    Defines the contract that any database implementation must fulfill.
    This allows swapping database implementations without affecting other layers.
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the database.

        Raises:
            ConnectionError: If connection fails.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close database connection gracefully.

        Should handle cleanup of resources.
        """
        pass

    @abstractmethod
    async def ping(self) -> bool:
        """
        Check if database connection is alive.

        Returns:
            True if connected, False otherwise.
        """
        pass

    @abstractmethod
    def get_database(self, name: Optional[str] = None) -> Any:
        """
        Get database instance.

        Args:
            name: Database name (optional, uses default if not provided).

        Returns:
            Database instance.
        """
        pass

    @abstractmethod
    def get_collection(self, collection_name: str) -> Any:
        """
        Get a specific collection/table.

        Args:
            collection_name: Name of the collection.

        Returns:
            Collection instance.
        """
        pass

    @abstractmethod
    async def start_transaction(self) -> Any:
        """
        Start a database transaction.

        Returns:
            Transaction context manager.
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict:
        """
        Perform comprehensive health check.

        Returns:
            Dictionary with health status information.
        """
        pass


class SessionManagerInterface(ABC):
    """
    Abstract interface for session management.

    Manages database sessions/connections lifecycle.
    """

    @abstractmethod
    async def get_session(self) -> AsyncGenerator[Any, None]:
        """
        Get a database session.

        Yields:
            Database session for operations.

        This method should be used as a FastAPI dependency.
        """
        pass

    @abstractmethod
    async def close_session(self, session: Any) -> None:
        """
        Close a database session.

        Args:
            session: Session to close.
        """
        pass
