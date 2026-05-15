"""
Tests for the migration system.
"""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["DEBUG"] = "true"

from migrations.config import MigrationConfig
from migrations.exceptions import (
    MigrationAlreadyAppliedError,
    MigrationError,
    MigrationExecutionError,
    MigrationNotFoundError,
)
from migrations.registry import MigrationRegistry
from migrations.runner import MigrationRunner


@pytest.fixture
def mock_db():
    """Create a mock MongoDB database."""
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=MagicMock())
    return db


@pytest.fixture
def mock_collection():
    """Create a mock collection."""
    return MagicMock()


class TestMigrationConfig:
    """Tests for MigrationConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MigrationConfig()

        assert config.MIGRATION_LOG_COLLECTION == "_migration_log"
        assert config.MIGRATION_LOCK_COLLECTION == "_migration_lock"
        assert config.LOCK_TIMEOUT_SECONDS == 300
        assert config.VALIDATE_CHECKSUMS is True

    def test_migrations_dir_exists(self):
        """Test migrations directory property."""
        config = MigrationConfig()

        assert config.MIGRATIONS_DIR.exists()
        assert config.MIGRATIONS_DIR.name == "versions"


class TestMigrationRegistry:
    """Tests for MigrationRegistry."""

    @pytest.mark.asyncio
    async def test_is_applied_true(self, mock_db):
        """Test checking if migration is applied."""
        mock_collection = AsyncMock()
        mock_collection.count_documents.return_value = 1
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        registry = MigrationRegistry(mock_db)
        registry._collection = mock_collection

        result = await registry.is_applied("001_test")

        assert result is True
        mock_collection.count_documents.assert_called_once_with(
            {"migration_id": "001_test"}
        )

    @pytest.mark.asyncio
    async def test_is_applied_false(self, mock_db):
        """Test checking if migration is not applied."""
        mock_collection = AsyncMock()
        mock_collection.count_documents.return_value = 0
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        registry = MigrationRegistry(mock_db)
        registry._collection = mock_collection

        result = await registry.is_applied("001_test")

        assert result is False

    @pytest.mark.asyncio
    async def test_register_migration_success(self, mock_db):
        """Test registering a migration."""
        mock_collection = AsyncMock()
        mock_collection.count_documents.return_value = 0  # Not applied yet
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        registry = MigrationRegistry(mock_db)
        registry._collection = mock_collection

        await registry.register_migration(
            migration_id="001_test",
            description="Test migration",
            checksum="abc123",
            author="test@test.com",
            duration_ms=100.0,
            success=True,
        )

        mock_collection.insert_one.assert_called_once()
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["migration_id"] == "001_test"
        assert call_args["description"] == "Test migration"
        assert call_args["success"] is True

    @pytest.mark.asyncio
    async def test_register_migration_already_applied(self, mock_db):
        """Test registering an already applied migration."""
        mock_collection = AsyncMock()
        mock_collection.count_documents.return_value = 1  # Already applied
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        registry = MigrationRegistry(mock_db)
        registry._collection = mock_collection

        with pytest.raises(MigrationAlreadyAppliedError):
            await registry.register_migration(
                migration_id="001_test",
                description="Test migration",
                checksum="abc123",
                author="test@test.com",
                duration_ms=100.0,
            )


class TestMigrationRunner:
    """Tests for MigrationRunner."""

    @pytest.mark.asyncio
    async def test_discover_migrations(self, tmp_path):
        """Test discovering migration files."""
        runner = MigrationRunner()

        # Create temporary migration files
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()

        (versions_dir / "001_first.py").write_text("# first")
        (versions_dir / "002_second.py").write_text("# second")
        (versions_dir / "_private.py").write_text("# private - should be ignored")

        runner._migrations_dir = versions_dir
        migrations = runner._discover_migrations()

        assert len(migrations) == 2
        assert migrations[0][0] == "001_first"
        assert migrations[1][0] == "002_second"

    @pytest.mark.asyncio
    async def test_discover_empty_directory(self):
        """Test discovering migrations in empty directory."""
        runner = MigrationRunner()
        migrations = runner._discover_migrations()

        # Should find the example migrations in the actual versions directory
        assert len(migrations) > 0


class TestMigrationFunctions:
    """Tests for migration file functions."""

    def test_migration_file_syntax(self):
        """Test that migration files have valid syntax."""
        from pathlib import Path
        import ast

        versions_dir = Path(__file__).parent.parent / "migrations" / "versions"

        for py_file in versions_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            content = py_file.read_text()

            # Should parse without errors
            tree = ast.parse(content)

            # Should have up and down functions
            names = [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.AsyncFunctionDef)
            ]
            assert "up" in names, f"{py_file.name} missing up() function"
            assert "down" in names, f"{py_file.name} missing down() function"

    @pytest.mark.asyncio
    async def test_user_role_migration_creates_indexes_and_seeds_roles(self):
        """User/role migration should create indexes and default roles."""
        runner = MigrationRunner()
        module = runner._load_migration_module(
            runner._migrations_dir / "005_create_users_and_roles.py"
        )

        db = MagicMock()
        db.users = MagicMock()
        db.roles = MagicMock()

        db.users.update_many = AsyncMock(return_value=MagicMock(modified_count=0))
        db.users.create_index = AsyncMock()
        db.roles.create_index = AsyncMock()
        db.roles.update_one = AsyncMock()

        await module.up(db)

        db.users.create_index.assert_any_call(
            "email", background=True, name="idx_users_email_unique", unique=True
        )
        db.users.create_index.assert_any_call(
            "username", background=True, name="idx_users_username_unique", unique=True
        )
        db.roles.create_index.assert_any_call(
            "name", background=True, name="idx_roles_name_unique", unique=True
        )
        assert db.roles.update_one.await_count == 2

    @pytest.mark.asyncio
    async def test_user_role_migration_down_drops_indexes(self):
        """User/role migration down should remove indexes and seeded roles."""
        runner = MigrationRunner()
        module = runner._load_migration_module(
            runner._migrations_dir / "005_create_users_and_roles.py"
        )

        db = MagicMock()
        db.users = MagicMock()
        db.roles = MagicMock()

        db.users.drop_index = AsyncMock()
        db.roles.drop_index = AsyncMock()
        db.users.update_many = AsyncMock(return_value=MagicMock(modified_count=0))
        db.roles.delete_many = AsyncMock(return_value=MagicMock(deleted_count=2))

        await module.down(db)

        db.users.drop_index.assert_any_call("idx_users_email_unique")
        db.users.drop_index.assert_any_call("idx_users_username_unique")
        db.roles.drop_index.assert_any_call("idx_roles_name_unique")
        db.roles.delete_many.assert_called_once()


class TestCLI:
    """Tests for CLI."""

    def test_create_parser(self):
        """Test CLI argument parser."""
        from migrations.cli import create_parser

        parser = create_parser()

        # Get all subcommands from the parser
        subcommands = [
            cmd
            for action in parser._subparsers._actions
            if hasattr(action, "_name_parser_map")
            for cmd in action._name_parser_map.keys()
        ]

        # Verify all required commands exist
        required_commands = ["status", "migrate", "rollback", "create", "verify"]
        for cmd in required_commands:
            assert cmd in subcommands, f"Missing command: {cmd}"


class TestExceptions:
    """Tests for custom exceptions."""

    def test_migration_error_with_id(self):
        """Test MigrationError with migration ID."""
        error = MigrationExecutionError("Test error", "001_test")

        assert str(error) == "Test error"
        assert error.migration_id == "001_test"

    def test_migration_error_without_id(self):
        """Test MigrationError without migration ID."""
        error = MigrationError("Test error")

        assert str(error) == "Test error"
        assert error.migration_id is None
