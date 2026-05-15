"""
Database configuration.

Handles database connections and sessions for MongoDB.
Follows the Dependency Inversion Principle.

IMPORTANT: MongoDB vs Alembic
------------------------------
Alembic is designed for SQL databases (SQLAlchemy) and uses schema migrations
based on DDL (Data Definition Language). MongoDB is schema-less and doesn't use
traditional migrations. Instead, we implement:

1. Schema Evolution Strategy: Documents are versioned and upgraded on-the-fly
2. Custom Migration System: Python-based migrations for data transformations
3. Beanie ODM: Handles document validation and schema changes gracefully

This approach is more idiomatic for NoSQL databases and provides better flexibility.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure

from app.core.config import settings
from app.core.interfaces.database import DatabaseInterface, SessionManagerInterface
from app.core.logging import get_logger

logger = get_logger(__name__)


class MongoDatabase(DatabaseInterface):
    """
    MongoDB database implementation.

    Manages MongoDB connections using Motor (async MongoDB driver).
    Follows the Singleton pattern for connection reuse.
    Implements DatabaseInterface for dependency inversion.
    """

    _instance: Optional["MongoDatabase"] = None
    _client: Optional[AsyncIOMotorClient] = None
    _database: Optional[AsyncIOMotorDatabase] = None
    _is_connected: bool = False

    def __new__(cls) -> "MongoDatabase":
        """Ensure singleton pattern for database connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """
        Establish connection to MongoDB.

        Configures connection pool and starts monitoring.

        Raises:
            ConnectionFailure: If connection to MongoDB fails.
        """
        if self._is_connected:
            logger.debug("Database already connected")
            return

        try:
            logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}")

            # Configure MongoDB client with connection pooling
            self._client = AsyncIOMotorClient(settings.MONGODB_URL)

            # Verify connection
            await self._client.admin.command("ping")
            self._database = self._client[settings.MONGODB_DB_NAME]
            self._is_connected = True

            logger.info(
                f"Successfully connected to MongoDB database: {settings.MONGODB_DB_NAME}"
            )

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise ConnectionFailure(f"Failed to connect to MongoDB: {e}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            raise

    async def disconnect(self) -> None:
        """
        Close MongoDB connection gracefully.

        Handles cleanup of resources and connection pool.
        """
        if not self._is_connected or self._client is None:
            logger.debug("Database not connected, skipping disconnect")
            return

        try:
            logger.info("Closing MongoDB connection")
            self._client.close()
            self._is_connected = False
            self._client = None
            self._database = None
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")
            raise

    async def ping(self) -> bool:
        """
        Check if MongoDB connection is alive.

        Returns:
            True if connected, False otherwise.
        """
        if not self._is_connected or self._client is None:
            return False

        try:
            await self._client.admin.command("ping")
            return True
        except Exception:
            return False

    def get_database(self, name: Optional[str] = None) -> AsyncIOMotorDatabase:
        """
        Get MongoDB database instance.

        Args:
            name: Database name (optional, uses default if not provided).

        Returns:
            MongoDB database instance.

        Raises:
            RuntimeError: If not connected to database.
        """
        if not self._is_connected:
            raise RuntimeError("Database not connected. Call connect() first.")

        if name:
            return self._client[name]
        return self._database

    def get_collection(self, collection_name: str) -> Any:
        """
        Get a specific MongoDB collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            MongoDB collection instance.

        Raises:
            RuntimeError: If not connected to database.
        """
        if not self._is_connected:
            raise RuntimeError("Database not connected. Call connect() first.")

        return self._database[collection_name]

    @asynccontextmanager
    async def start_transaction(self):
        """
        Start a MongoDB transaction.

        MongoDB supports ACID transactions starting from version 4.0.
        Use this for operations that need atomicity.

        Yields:
            Transaction session for atomic operations.

        Example:
            async with db.start_transaction() as session:
                await collection.insert_one(doc, session=session)
                await collection.update_one(filter, update, session=session)
        """
        if not self._is_connected:
            raise RuntimeError("Database not connected. Call connect() first.")

        session = await self._client.start_session()
        try:
            async with session.start_transaction():
                yield session
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            await session.end_session()

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.

        Returns:
            Dictionary with health status information including:
            - connected: Whether database is connected
            - ping_ms: Ping response time in milliseconds
            - database: Database name
            - collections: List of collection names
        """
        import time

        health_status = {
            "connected": False,
            "ping_ms": None,
            "database": settings.MONGODB_DB_NAME,
            "collections": [],
            "error": None,
        }

        if not self._is_connected or self._client is None:
            health_status["error"] = "Database not connected"
            return health_status

        try:
            start_time = time.time()
            await self._client.admin.command("ping")
            end_time = time.time()

            health_status["connected"] = True
            health_status["ping_ms"] = round((end_time - start_time) * 1000, 2)

            # Get collection names
            collections = await self._database.list_collection_names()
            health_status["collections"] = collections

        except Exception as e:
            health_status["error"] = str(e)

        return health_status

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._is_connected

    @property
    def client(self) -> Optional[AsyncIOMotorClient]:
        """Get MongoDB client instance."""
        return self._client


class SessionManager(SessionManagerInterface):
    """
    MongoDB session manager.

    Manages database sessions for FastAPI dependency injection.
    Follows the Dependency Inversion Principle.
    """

    def __init__(self, database: MongoDatabase):
        """
        Initialize session manager.

        Args:
            database: MongoDB database instance.
        """
        self._database = database

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
        """
        Get a database session for FastAPI dependency injection.

        Yields:
            MongoDB database instance.

        Example usage in FastAPI:
            @router.get("/items")
            async def get_items(db: AsyncIOMotorDatabase = Depends(get_db_session)):
                return await db.collection.find().to_list(length=100)
        """
        if not self._database.is_connected:
            await self._database.connect()

        try:
            yield self._database.get_database()
        except Exception as e:
            logger.error(f"Session error: {e}")
            raise

    async def close_session(self, session: Any) -> None:
        """
        Close a database session.

        In MongoDB with Motor, sessions are managed automatically.
        This method is kept for interface compliance.

        Args:
            session: Session to close (not used in MongoDB).
        """
        # Motor handles session cleanup automatically
        pass


# Global instances
db = MongoDatabase()
session_manager = SessionManager(db)


# FastAPI dependency
async def get_db_session() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    FastAPI dependency for database session.

    Usage:
        from fastapi import Depends

        @router.get("/items")
        async def get_items(db: AsyncIOMotorDatabase = Depends(get_db_session)):
            collection = db["items"]
            return await collection.find().to_list(length=100)
    """
    async with session_manager.get_session() as database:
        yield database


async def init_db() -> None:
    """
    Initialize database connection on application startup.

    Should be called in FastAPI lifespan context manager.
    """
    await db.connect()


async def close_db() -> None:
    """
    Close database connection on application shutdown.

    Should be called in FastAPI lifespan context manager.
    """
    await db.disconnect()
