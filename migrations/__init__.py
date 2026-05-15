"""
MongoDB Migration System for PDF Extract API.

A professional, production-ready migration framework for MongoDB.
Uses pure async functions as migration units.

Usage:
    python -m migrations status
    python -m migrations migrate
    python -m migrations rollback
    python -m migrations create "description"
"""

__version__ = "1.0.0"
__all__ = ["MigrationRunner", "MigrationRegistry", "MigrationError"]

from migrations.runner import MigrationRunner
from migrations.registry import MigrationRegistry
from migrations.exceptions import MigrationError
