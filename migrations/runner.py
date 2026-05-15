"""
Migration execution engine.

Orchestrates the discovery, validation, and execution of migrations.
"""

import asyncio
import importlib.util
import inspect
import time
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings
from migrations.config import config
from migrations.exceptions import (
    MigrationAlreadyAppliedError,
    MigrationError,
    MigrationExecutionError,
    MigrationLockError,
    MigrationNotAppliedError,
    MigrationNotFoundError,
)
from migrations.logger import MigrationLogger
from migrations.registry import MigrationRegistry


# Type aliases for migration functions
MigrationFunction = Callable[[AsyncIOMotorDatabase], Any]


class MigrationRunner:
    """
    Core engine for executing MongoDB migrations.

    Responsibilities:
    - Discover available migrations from the versions directory
    - Track which migrations have been applied
    - Execute migrations in order (up or down)
    - Handle transactions and rollback
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self._db = db
        self._registry: Optional[MigrationRegistry] = None
        self._logger = MigrationLogger()
        self._migrations_dir = config.MIGRATIONS_DIR

    async def _ensure_db(self):
        """Ensure database connection is established."""
        if self._db is None:
            client = AsyncIOMotorClient(settings.MONGODB_URL)
            self._db = client[settings.MONGODB_DB_NAME]

        if self._registry is None:
            self._registry = MigrationRegistry(self._db)
            await self._registry.initialize()

    def _discover_migrations(self) -> List[Tuple[str, Path]]:
        """
        Discover all migration files in the versions directory.

        Returns:
            List of (migration_id, file_path) tuples, sorted by migration_id.
        """
        migrations = []

        if not self._migrations_dir.exists():
            self._logger.warning(
                f"Migrations directory not found: {self._migrations_dir}"
            )
            return migrations

        for file_path in sorted(self._migrations_dir.glob("*.py")):
            if file_path.name.startswith("_"):
                continue

            # Extract migration ID from filename (e.g., "001_create_indexes.py" -> "001_create_indexes")
            migration_id = file_path.stem
            migrations.append((migration_id, file_path))

        return migrations

    def _load_migration_module(self, file_path: Path) -> ModuleType:
        """Load a migration file as a Python module."""
        spec = importlib.util.spec_from_file_location(
            f"migrations.versions.{file_path.stem}", file_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    async def _acquire_lock(self) -> bool:
        """
        Acquire distributed lock to prevent concurrent migrations.

        Uses MongoDB's atomic operations for distributed locking.
        """
        lock_collection = self._db[config.MIGRATION_LOCK_COLLECTION]

        try:
            # Try to insert lock document
            await lock_collection.insert_one(
                {
                    "_id": "migration_lock",
                    "acquired_at": datetime.utcnow(),
                    "expires_at": datetime.utcnow().timestamp()
                    + config.LOCK_TIMEOUT_SECONDS,
                }
            )
            return True
        except Exception:
            # Lock already exists
            # Check if it's expired
            existing = await lock_collection.find_one({"_id": "migration_lock"})
            if (
                existing
                and existing.get("expires_at", 0) < datetime.utcnow().timestamp()
            ):
                # Lock expired, remove and retry
                await lock_collection.delete_one({"_id": "migration_lock"})
                return await self._acquire_lock()
            return False

    async def _release_lock(self):
        """Release the distributed lock."""
        lock_collection = self._db[config.MIGRATION_LOCK_COLLECTION]
        await lock_collection.delete_one({"_id": "migration_lock"})

    async def _execute_migration(
        self, migration_id: str, module: ModuleType, direction: str = "up"
    ):
        """
        Execute a single migration.

        Args:
            migration_id: The migration identifier
            module: Loaded migration module
            direction: "up" or "down"
        """
        func_name = direction
        func = getattr(module, func_name, None)

        if func is None:
            if direction == "down":
                self._logger.warning(
                    f"No down() function found, migration not reversible", migration_id
                )
                return
            else:
                raise MigrationExecutionError(
                    f"Migration {migration_id} has no up() function", migration_id
                )

        # Verify it's a coroutine function
        if not inspect.iscoroutinefunction(func):
            raise MigrationExecutionError(
                f"Migration {migration_id} up() must be async", migration_id
            )

        # Get migration metadata
        description = getattr(
            module, "description", migration_id.replace("_", " ").title()
        )
        author = getattr(module, "author", "unknown")

        # Compute checksum
        file_path = self._migrations_dir / f"{migration_id}.py"
        checksum = self._registry.compute_checksum(str(file_path))

        # Verify checksum if already applied
        if direction == "up" and await self._registry.is_applied(migration_id):
            if not await self._registry.verify_checksum(migration_id, checksum):
                raise MigrationExecutionError(
                    f"Migration {migration_id} file has been modified after being applied",
                    migration_id,
                )
            self._logger.skipped(migration_id, "already applied")
            return

        # Execute with timing
        start_time = time.time()
        self._logger.start_migration(migration_id, direction)

        try:
            if config.DRY_RUN:
                self._logger.warning(
                    f"DRY RUN: Would execute {direction} migration", migration_id
                )
                return

            # Execute the migration
            await func(self._db)

            duration_ms = (time.time() - start_time) * 1000

            # Register in log for 'up', unregister for 'down'
            if direction == "up":
                await self._registry.register_migration(
                    migration_id=migration_id,
                    description=description,
                    checksum=checksum,
                    author=author,
                    duration_ms=duration_ms,
                    success=True,
                )
            else:
                await self._registry.unregister_migration(migration_id)

            self._logger.complete_migration(migration_id, duration_ms)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._logger.error(
                f"Failed after {duration_ms:.2f}ms: {str(e)}", migration_id
            )
            raise MigrationExecutionError(
                f"Migration {migration_id} failed: {str(e)}", migration_id
            ) from e

    async def status(self) -> Dict[str, Any]:
        """
        Get current migration status.

        Returns:
            Dictionary with status information including:
            - applied_count: Number of applied migrations
            - pending_count: Number of pending migrations
            - last_applied: Last migration that was applied
            - pending: List of pending migration IDs
        """
        await self._ensure_db()

        discovered = self._discover_migrations()
        applied_ids = await self._registry.get_applied_migration_ids()

        pending = [mid for mid, _ in discovered if mid not in applied_ids]

        last_applied = await self._registry.get_last_migration()

        return {
            "total_migrations": len(discovered),
            "applied_count": len(applied_ids),
            "pending_count": len(pending),
            "last_applied": last_applied["migration_id"] if last_applied else None,
            "last_applied_at": last_applied["applied_at"] if last_applied else None,
            "pending": pending,
        }

    async def migrate(self, target: Optional[str] = None, dry_run: bool = False):
        """
        Execute pending migrations.

        Args:
            target: Optional target migration to stop at
            dry_run: If True, only show what would be executed
        """
        await self._ensure_db()

        # Acquire lock
        if not await self._acquire_lock():
            raise MigrationLockError(
                "Could not acquire migration lock. Another migration may be running."
            )

        try:
            if dry_run:
                self._logger.warning("=== DRY RUN MODE ===")
                config.DRY_RUN = True

            discovered = self._discover_migrations()
            applied_ids = await self._registry.get_applied_migration_ids()

            # Determine which migrations to run
            to_apply = []
            for mid, path in discovered:
                if mid in applied_ids:
                    continue
                to_apply.append((mid, path))
                if target and mid == target:
                    break

            if not to_apply:
                self._logger.info("No pending migrations")
                return

            self._logger.info(f"Found {len(to_apply)} pending migration(s)")

            # Execute each migration
            for mid, path in to_apply:
                module = self._load_migration_module(path)
                await self._execute_migration(mid, module, "up")

            self._logger.success("All migrations completed successfully")

        finally:
            await self._release_lock()
            config.DRY_RUN = False

    async def rollback(
        self, target: Optional[str] = None, steps: int = 1, dry_run: bool = False
    ):
        """
        Rollback migrations.

        Args:
            target: Rollback to this specific migration (inclusive)
            steps: Number of migrations to rollback
            dry_run: If True, only show what would be executed
        """
        await self._ensure_db()

        # Acquire lock
        if not await self._acquire_lock():
            raise MigrationLockError(
                "Could not acquire migration lock. Another migration may be running."
            )

        try:
            if dry_run:
                self._logger.warning("=== DRY RUN MODE ===")
                config.DRY_RUN = True

            # Get applied migrations in reverse order
            applied = await self._registry.get_applied_migrations()
            applied_ids = [m["migration_id"] for m in applied]

            if not applied_ids:
                self._logger.info("No migrations to rollback")
                return

            # Determine which migrations to rollback
            to_rollback = []
            if target:
                # Rollback to specific migration
                if target not in applied_ids:
                    raise MigrationNotAppliedError(
                        f"Target migration {target} has not been applied", target
                    )
                target_idx = applied_ids.index(target)
                to_rollback = applied_ids[target_idx + 1 :]
                to_rollback.reverse()
            else:
                # Rollback N steps
                to_rollback = applied_ids[-steps:]
                to_rollback.reverse()

            if not to_rollback:
                self._logger.info("No migrations to rollback")
                return

            self._logger.info(f"Rolling back {len(to_rollback)} migration(s)")

            # Execute rollback for each
            for mid in to_rollback:
                path = self._migrations_dir / f"{mid}.py"
                if not path.exists():
                    self._logger.warning(
                        f"Migration file not found, skipping rollback", mid
                    )
                    await self._registry.unregister_migration(mid)
                    continue

                module = self._load_migration_module(path)
                await self._execute_migration(mid, module, "down")

            self._logger.success("Rollback completed successfully")

        finally:
            await self._release_lock()
            config.DRY_RUN = False

    async def verify(self) -> List[Dict[str, Any]]:
        """
        Verify integrity of applied migrations.

        Returns:
            List of issues found (empty if all OK)
        """
        await self._ensure_db()

        issues = []
        applied = await self._registry.get_applied_migrations()

        for entry in applied:
            mid = entry["migration_id"]
            path = self._migrations_dir / f"{mid}.py"

            if not path.exists():
                issues.append(
                    {
                        "migration_id": mid,
                        "issue": "file_missing",
                        "message": f"Migration file {mid}.py not found",
                    }
                )
                continue

            # Verify checksum
            current_checksum = self._registry.compute_checksum(str(path))
            if entry.get("checksum") != current_checksum:
                issues.append(
                    {
                        "migration_id": mid,
                        "issue": "checksum_mismatch",
                        "message": "Migration file has been modified",
                    }
                )

        return issues

    async def create(self, description: str) -> str:
        """
        Create a new migration file from template.

        Args:
            description: Human-readable description

        Returns:
            The migration ID created
        """
        # Generate migration ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_desc = description.lower().replace(" ", "_").replace("-", "_")[:50]
        migration_id = f"{timestamp}_{safe_desc}"

        # Ensure directory exists
        self._migrations_dir.mkdir(parents=True, exist_ok=True)

        file_path = self._migrations_dir / f"{migration_id}.py"

        # Template content
        template = f'''"""
{description}

Created: {datetime.now().isoformat()}
"""

migration_id = "{migration_id}"
description = "{description}"
created_at = "{datetime.now().isoformat()}"
author = "developer"


async def up(db):
    """
    Apply the migration.

    Args:
        db: AsyncIOMotorDatabase instance
    """
    # TODO: Implement migration
    pass


async def down(db):
    """
    Revert the migration.

    Args:
        db: AsyncIOMotorDatabase instance
    """
    # TODO: Implement rollback
    pass
'''

        file_path.write_text(template, encoding="utf-8")
        self._logger.success(f"Created migration: {file_path}")

        return migration_id
