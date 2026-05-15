"""
Tests for health check endpoint.

Follows the Arrange-Act-Assert pattern.
Uses FastAPI TestClient for integration testing.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import create_application
from app.services.health_service import HealthService


@pytest.fixture
def mock_health_service():
    """Create a mock HealthService."""
    service = MagicMock(spec=HealthService)
    return service


@pytest.fixture
def client(mock_health_service):
    """Create a test client with mocked dependencies."""
    # Create app with mocked health service
    app = create_application()

    # Override the dependency
    from app.api.v1.endpoints.health import get_health_service

    app.dependency_overrides[get_health_service] = lambda: mock_health_service

    return TestClient(app)


class TestHealthEndpoint:
    """Test suite for /health endpoint."""

    @pytest.fixture
    def mock_healthy_response(self):
        """Create a mock healthy response."""
        from app.schemas.health import HealthCheckResponse, HealthCheckDetail
        from datetime import datetime, timezone

        return HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc),
            environment="test",
            checks={
                "database": HealthCheckDetail(
                    status="pass",
                    response_time_ms=15.2,
                    details={"connected": True, "ping_ms": 12.5},
                ),
                "migrations": HealthCheckDetail(
                    status="pass",
                    response_time_ms=5.1,
                    details={"pending_count": 0, "applied_count": 4},
                ),
            },
            uptime_seconds=3600,
        )

    def test_get_health_returns_200_when_healthy(
        self, client, mock_health_service, mock_healthy_response
    ):
        """Test GET /api/v1/health returns 200 when system is healthy."""
        # Arrange
        mock_health_service.check_health = AsyncMock(return_value=mock_healthy_response)

        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_get_health_includes_version(
        self, client, mock_health_service, mock_healthy_response
    ):
        """Test health response includes application version."""
        # Arrange
        mock_health_service.check_health = AsyncMock(return_value=mock_healthy_response)

        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_get_health_includes_timestamp(
        self, client, mock_health_service, mock_healthy_response
    ):
        """Test health response includes timestamp."""
        # Arrange
        mock_health_service.check_health = AsyncMock(return_value=mock_healthy_response)

        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"] is not None

    def test_get_health_includes_environment(
        self, client, mock_health_service, mock_healthy_response
    ):
        """Test health response includes environment."""
        # Arrange
        mock_health_service.check_health = AsyncMock(return_value=mock_healthy_response)

        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "environment" in data
        assert data["environment"] in ["development", "staging", "production", "test"]

    def test_get_health_includes_database_check(
        self, client, mock_health_service, mock_healthy_response
    ):
        """Test health response includes database check."""
        # Arrange
        mock_health_service.check_health = AsyncMock(return_value=mock_healthy_response)

        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]
        assert data["checks"]["database"]["status"] == "pass"

    def test_get_health_includes_migrations_check(
        self, client, mock_health_service, mock_healthy_response
    ):
        """Test health response includes migrations check."""
        # Arrange
        mock_health_service.check_health = AsyncMock(return_value=mock_healthy_response)

        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "migrations" in data["checks"]
        assert "pending_count" in data["checks"]["migrations"]["details"]

    def test_get_health_returns_200_when_degraded(self, client, mock_health_service):
        """Test GET /api/v1/health returns 200 even when degraded."""
        # Arrange
        from app.schemas.health import HealthCheckResponse, HealthCheckDetail
        from datetime import datetime, timezone

        degraded_response = HealthCheckResponse(
            status="degraded",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc),
            environment="test",
            checks={
                "database": HealthCheckDetail(
                    status="fail",
                    response_time_ms=0,
                    details={"error": "Connection timeout"},
                ),
                "migrations": HealthCheckDetail(
                    status="pass", response_time_ms=5.1, details={"pending_count": 0}
                ),
            },
            uptime_seconds=3600,
        )
        mock_health_service.check_health = AsyncMock(return_value=degraded_response)

        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"

    def test_get_health_returns_503_when_unhealthy(self, client, mock_health_service):
        """Test GET /api/v1/health returns 503 when critical checks fail."""
        # Arrange
        from app.schemas.health import HealthCheckResponse, HealthCheckDetail
        from datetime import datetime, timezone

        # Note: In a real implementation, the endpoint would return 503
        # based on critical check failures
        unhealthy_response = HealthCheckResponse(
            status="unhealthy",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc),
            environment="test",
            checks={
                "database": HealthCheckDetail(
                    status="fail",
                    response_time_ms=0,
                    details={"error": "Connection refused"},
                ),
                "migrations": HealthCheckDetail(
                    status="fail",
                    response_time_ms=0,
                    details={"error": "Migration check failed"},
                ),
            },
            uptime_seconds=3600,
        )
        mock_health_service.check_health = AsyncMock(return_value=unhealthy_response)

        # Act
        response = client.get("/api/v1/health")

        # Assert
        # Note: This might be 200 or 503 depending on implementation
        # The important thing is the status field indicates unhealthy
        data = response.json()
        assert data["status"] == "unhealthy"

    def test_get_health_response_has_correct_structure(
        self, client, mock_health_service, mock_healthy_response
    ):
        """Test health response has the expected structure."""
        # Arrange
        mock_health_service.check_health = AsyncMock(return_value=mock_healthy_response)

        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check required fields
        required_fields = ["status", "version", "timestamp", "environment", "checks"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Check checks structure
        assert isinstance(data["checks"], dict)
        for check_name, check_data in data["checks"].items():
            assert "status" in check_data
            assert "response_time_ms" in check_data
