"""
Logging configuration for migrations.
"""

import logging
import sys
from datetime import datetime


def get_migration_logger() -> logging.Logger:
    """Get configured logger for migrations."""
    logger = logging.getLogger("migrations")

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


class MigrationLogger:
    """Structured logging for migrations."""

    def __init__(self):
        self._logger = get_migration_logger()

    def info(self, message: str, migration_id: str = None):
        prefix = f"[{migration_id}] " if migration_id else ""
        self._logger.info(f"{prefix}{message}")

    def error(self, message: str, migration_id: str = None):
        prefix = f"[{migration_id}] " if migration_id else ""
        self._logger.error(f"{prefix}{message}")

    def warning(self, message: str, migration_id: str = None):
        prefix = f"[{migration_id}] " if migration_id else ""
        self._logger.warning(f"{prefix}{message}")

    def success(self, message: str, migration_id: str = None):
        prefix = f"[{migration_id}] " if migration_id else ""
        self._logger.info(f"{prefix}✓ {message}")

    def start_migration(self, migration_id: str, direction: str = "up"):
        self.info(f"Starting {direction} migration...", migration_id)

    def complete_migration(self, migration_id: str, duration_ms: float):
        self.success(f"Completed in {duration_ms:.2f}ms", migration_id)

    def skipped(self, migration_id: str, reason: str):
        self.warning(f"Skipped: {reason}", migration_id)
