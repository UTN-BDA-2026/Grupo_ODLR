"""
Configuration for the migration system.
"""

import os
from pathlib import Path
from typing import Optional

from app.core.config import settings


class MigrationConfig:
    """Configuration settings for migrations."""

    # Collection name for migration tracking
    MIGRATION_LOG_COLLECTION: str = "_migration_log"

    # Collection name for distributed locks
    MIGRATION_LOCK_COLLECTION: str = "_migration_lock"

    # Lock timeout in seconds
    LOCK_TIMEOUT_SECONDS: int = 300  # 5 minutes

    # Path to migrations directory
    @property
    def MIGRATIONS_DIR(self) -> Path:
        return Path(__file__).parent / "versions"

    # Path to local state file (backup)
    @property
    def LOCAL_STATE_FILE(self) -> Path:
        return Path(__file__).parent / ".migrations.json"

    # MongoDB connection settings (from app config)
    @property
    def MONGODB_URL(self) -> str:
        return settings.MONGODB_URL

    @property
    def MONGODB_DB_NAME(self) -> str:
        return settings.MONGODB_DB_NAME

    # Whether to create backups before migrations
    CREATE_BACKUPS: bool = (
        os.getenv("MIGRATION_CREATE_BACKUPS", "false").lower() == "true"
    )

    # Backup directory
    BACKUP_DIR: Optional[Path] = Path(
        os.getenv("MIGRATION_BACKUP_DIR", str(Path(__file__).parent / "backups"))
    )

    # Dry run mode (simulate without executing)
    DRY_RUN: bool = os.getenv("MIGRATION_DRY_RUN", "false").lower() == "true"

    # Validate checksums on migration files
    VALIDATE_CHECKSUMS: bool = True

    # Auto-retry failed migrations
    AUTO_RETRY: bool = False

    # Max retries
    MAX_RETRIES: int = 3


# Global config instance
config = MigrationConfig()
