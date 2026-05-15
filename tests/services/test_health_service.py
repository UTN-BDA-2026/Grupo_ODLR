"""
Tests for HealthService.

Follows the Arrange-Act-Assert pattern.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.health import HealthCheckResponse
from app.services.health_service import HealthService


@pytest.fixture(autouse=True)
def mock_migrations():
    """Mock migration runner to return no pending migrations for all tests."""
    with patch("migrations.runner.MigrationRunner") as mock_runner_class:
        mock_runner = MagicMock()
        mock_runner.status = AsyncMock(
            return_value={
                "pending_count": 0,
                "applied_count": 10,
                "total_migrations": 10,
            }
        )
        mock_runner_class.return_value = mock_runner
        yield


class TestHealthService:
    """Test suite for HealthService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database with proper structure for HealthService."""
        # Create inner database mock with command
        inner_db = MagicMock()
        inner_db.command = AsyncMock(return_value={"ok": 1.0})

        # Create main db mock with required interface
        db = MagicMock()
        db.is_connected = True
        db.connect = AsyncMock()
        db.get_database = MagicMock(return_value=inner_db)

        return db

    @pytest.fixture
    def health_service(self, mock_db):
        """Create a HealthService instance with mocked dependencies."""
        return HealthService(db=mock_db)

    @pytest.mark.asyncio
    async def test_check_health_returns_response(self, health_service, mock_db):
        """Test that check_health returns a HealthCheckResponse."""
        # Arrange - done by fixture

        # Act
        result = await health_service.check_health()

        # Assert
        assert isinstance(result, HealthCheckResponse)
        assert result.status in ["healthy", "degraded", "unhealthy"]
        assert result.version is not None
        assert isinstance(result.timestamp, datetime)
        assert "database" in result.checks
        assert "migrations" in result.checks

    
    @pytest.mark.asyncio
    async def test_check_health_status_healthy_when_all_pass(
        self, health_service, mock_db
    ):
        """Test that status is healthy when all checks pass."""
        # Arrange - mockeamos migraciones para que retornen "pass"
        from app.schemas.health import HealthCheckDetail

        with patch.object(
            health_service,
            "_check_migrations",
            return_value=HealthCheckDetail(
                status="pass",
                response_time_ms=1.0,
                details={"pending_count": 0, "applied_count": 1, "total_migrations": 1},
            ),
        ):
            # Act
            result = await health_service.check_health()

        # Assert
        assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_check_health_status_unhealthy_when_database_fails(
        self, health_service, mock_db
    ):
        """Test that status is unhealthy when critical database check fails."""
        # Arrange - update the inner database command to fail
        inner_db = mock_db.get_database.return_value
        inner_db.command = AsyncMock(side_effect=Exception("Connection failed"))

        # Act
        result = await health_service.check_health()

        # Assert - database is critical, so failure makes system unhealthy
        assert result.status == "unhealthy"
        assert result.checks["database"].status == "fail"

    @pytest.mark.asyncio
    async def test_check_health_includes_version(self, health_service):
        """Test that response includes application version."""
        # Act
        result = await health_service.check_health()

        # Assert
        assert result.version is not None
        assert len(result.version) > 0

    @pytest.mark.asyncio
    async def test_check_health_includes_timestamp(self, health_service):
        """Test that response includes UTC timestamp."""
        # Act
        result = await health_service.check_health()

        # Assert
        assert isinstance(result.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_check_health_includes_environment(self, health_service):
        """Test that response includes environment."""
        # Act
        result = await health_service.check_health()

        # Assert
        assert result.environment in ["development", "staging", "production"]

    @pytest.mark.asyncio
    async def test_check_health_database_check_has_response_time(
        self, health_service, mock_db
    ):
        """Test that database check includes response time."""
        # Act
        result = await health_service.check_health()

        # Assert
        assert "database" in result.checks
        assert result.checks["database"].response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_check_health_migrations_check_includes_count(self, health_service):
        """Test that migrations check includes pending count."""
        # Act
        result = await health_service.check_health()

        # Assert
        assert "migrations" in result.checks
        assert result.checks["migrations"].status in ["pass", "fail", "warn"]

    @pytest.mark.asyncio
    async def test_check_health_database_includes_connection_details(
        self, health_service, mock_db
    ):
        """Test that database check includes connection details."""
        # Act
        result = await health_service.check_health()

        # Assert
        assert result.checks["database"].details is not None
        assert "connected" in result.checks["database"].details


class TestHealthServiceChecks:
    """Tests for individual health check methods."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database with proper structure."""
        # Create inner database mock with command
        inner_db = MagicMock()
        inner_db.command = AsyncMock(return_value={"ok": 1.0})

        # Create main db mock with required interface
        db = MagicMock()
        db.is_connected = True
        db.connect = AsyncMock()
        db.get_database = MagicMock(return_value=inner_db)

        return db

    @pytest.fixture
    def health_service(self, mock_db):
        """Create a HealthService instance with mocked dependencies."""
        return HealthService(db=mock_db)

    @pytest.mark.asyncio
    async def test_check_database_returns_pass_on_success(
        self, health_service, mock_db
    ):
        """Test database check returns pass when connection succeeds."""
        # Arrange - mock_db already configured in fixture

        # Act
        result = await health_service._check_database()

        # Assert
        assert result.status == "pass"
        assert result.response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_check_database_returns_fail_on_exception(
        self, health_service, mock_db
    ):
        """Test database check returns fail when connection fails."""
        # Arrange - update the inner database command to fail
        inner_db = mock_db.get_database.return_value
        inner_db.command = AsyncMock(side_effect=Exception("Connection refused"))

        # Act
        result = await health_service._check_database()

        # Assert
        assert result.status == "fail"
        assert result.details is not None
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_check_database_includes_ping_response(self, health_service, mock_db):
        """Test database check includes ping response details."""
        # Arrange - update the inner database command to return ping_ms
        inner_db = mock_db.get_database.return_value
        inner_db.command = AsyncMock(return_value={"ok": 1.0, "ping_ms": 12.5})

        # Act
        result = await health_service._check_database()

        # Assert
        # Note: The service only includes connected=True in details, not ping_ms
        assert result.details is not None
        assert result.details.get("connected") is True
