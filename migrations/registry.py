"""
Migration registry and tracking system.

Manages the state of applied migrations in MongoDB.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from migrations.config import config
from migrations.exceptions import (
    MigrationAlreadyAppliedError,
    MigrationChecksumError,
    MigrationNotFoundError,
)
from migrations.logger import MigrationLogger


class MigrationRegistry:
    """
    Manages migration tracking in MongoDB.

    Uses a dedicated collection to store metadata about applied migrations,
    including checksums for integrity verification.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db
        self._collection = db[config.MIGRATION_LOG_COLLECTION]
        self._logger = MigrationLogger()

    async def initialize(self):
        """Initialize migration tracking collection with indexes."""
        # Create unique index on migration_id
        await self._collection.create_index(
            "migration_id", unique=True, background=True
        )
        # Create index on applied_at for sorting
        await self._collection.create_index("applied_at", background=True)

    async def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """
        Get list of all applied migrations, sorted by application order.

        Returns:
            List of migration log entries from MongoDB.
        """
        cursor = self._collection.find().sort("applied_at", 1)
        return await cursor.to_list(length=None)

    async def get_applied_migration_ids(self) -> List[str]:
        """Get list of IDs of applied migrations."""
        migrations = await self.get_applied_migrations()
        return [m["migration_id"] for m in migrations]

    async def is_applied(self, migration_id: str) -> bool:
        """Check if a migration has been applied."""
        count = await self._collection.count_documents({"migration_id": migration_id})
        return count > 0

    async def verify_checksum(self, migration_id: str, checksum: str) -> bool:
        """
        Verify that a migration file hasn't been modified.

        Args:
            migration_id: The migration identifier
            checksum: Current checksum of the file

        Returns:
            True if checksum matches or migration not yet applied
        """
        entry = await self._collection.find_one({"migration_id": migration_id})
        if entry is None:
            return True  # Not yet applied, no checksum to verify

        stored_checksum = entry.get("checksum")
        if stored_checksum and stored_checksum != checksum:
            return False

        return True

    async def register_migration(
        self,
        migration_id: str,
        description: str,
        checksum: str,
        author: str,
        duration_ms: float,
        success: bool = True,
        metadata: Optional[Dict] = None,
    ):
        """
        Register a migration as applied.

        Args:
            migration_id: Unique migration identifier
            description: Human-readable description
            checksum: File checksum for integrity
            author: Who created the migration
            duration_ms: Execution time in milliseconds
            success: Whether migration succeeded
            metadata: Additional metadata
        """
        if await self.is_applied(migration_id):
            raise MigrationAlreadyAppliedError(
                f"Migration {migration_id} is already applied", migration_id
            )

        entry = {
            "migration_id": migration_id,
            "description": description,
            "checksum": checksum,
            "author": author,
            "applied_at": datetime.now(timezone.utc),
            "execution_time_ms": duration_ms,
            "success": success,
            "metadata": metadata or {},
        }

        await self._collection.insert_one(entry)
        self._logger.success(f"Registered migration in log", migration_id)

    async def unregister_migration(self, migration_id: str):
        """
        Remove a migration from the applied list (for rollback).

        Args:
            migration_id: Migration to unregister
        """
        result = await self._collection.delete_one({"migration_id": migration_id})
        if result.deleted_count == 0:
            raise MigrationNotFoundError(
                f"Migration {migration_id} not found in applied migrations",
                migration_id,
            )

    async def get_last_migration(self) -> Optional[Dict[str, Any]]:
        """Get the most recently applied migration."""
        cursor = self._collection.find().sort("applied_at", -1).limit(1)
        migrations = await cursor.to_list(length=1)
        return migrations[0] if migrations else None

    async def get_migration_info(self, migration_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a specific migration."""
        return await self._collection.find_one({"migration_id": migration_id})

    async def clear_all(self):
        """
        Clear all migration history. USE WITH CAUTION.

        This is mainly useful for testing or resetting environments.
        """
        await self._collection.delete_many({})
        self._logger.warning("Cleared all migration history")

    @staticmethod
    def compute_checksum(file_path: str) -> str:
        """Compute SHA256 checksum of a migration file."""
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
