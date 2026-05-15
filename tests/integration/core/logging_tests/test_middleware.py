"""Integration tests for logging middleware.

Tests middleware in real FastAPI application context.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.logging.middleware import (
    CorrelationIdMiddleware,
    RequestLoggingMiddleware,
)


@pytest.fixture
def app():
    """Create test FastAPI app with middleware."""
    application = FastAPI()
    application.add_middleware(CorrelationIdMiddleware)
    application.add_middleware(RequestLoggingMiddleware)

    @application.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    @application.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    return application


@pytest.fixture
async def client(app):
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestCorrelationIdMiddleware:
    """Tests for correlation ID middleware."""

    async def test_adds_correlation_id_header(self, client):
        """Verify middleware adds correlation ID to response."""
        response = await client.get("/test")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    async def test_preserves_existing_correlation_id(self, client):
        """Verify middleware preserves existing correlation ID."""
        existing_id = "existing-correlation-id-123"
        response = await client.get("/test", headers={"X-Request-ID": existing_id})

        assert response.headers["X-Request-ID"] == existing_id

    async def test_different_requests_have_different_ids(self, client):
        """Verify each request gets unique correlation ID."""
        response1 = await client.get("/test")
        response2 = await client.get("/test")

        id1 = response1.headers["X-Request-ID"]
        id2 = response2.headers["X-Request-ID"]

        assert id1 != id2


class TestRequestLoggingMiddleware:
    """Tests for request logging middleware.

    These tests verify the middleware behavior without relying on caplog,
    since our custom logging handlers don't integrate with pytest's caplog.
    Instead, we mock the logger to verify the calls are made correctly.
    """

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        with patch("app.core.logging.middleware.logger") as mock:
            yield mock

    async def test_logs_request_completion(self, app, mock_logger):
        """Verify middleware logs request started and completed."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert response.status_code == 200

        # Verify logger.info was called with "Request started" and "Request completed"
        call_messages = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Request started" in msg for msg in call_messages)
        assert any("Request completed" in msg for msg in call_messages)

    async def test_logs_request_details(self, app, mock_logger):
        """Verify middleware logs request details."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/test")

        # Verify logger.info was called with method and path
        call_args_list = mock_logger.info.call_args_list
        assert len(call_args_list) >= 2  # At least started and completed

        # Check first call has method and path
        first_call = call_args_list[0]
        extra = first_call.kwargs.get("extra", {})
        assert "method" in extra
        assert "path" in extra
        assert extra["method"] == "GET"

    async def test_logs_response_status(self, app, mock_logger):
        """Verify middleware logs response status."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/test")

        # Verify logger.info was called with status_code
        call_args_list = mock_logger.info.call_args_list

        # Check second call (completed) has status_code
        for call in call_args_list:
            extra = call.kwargs.get("extra", {})
            if "status_code" in extra:
                assert extra["status_code"] == 200
                return

        pytest.fail("status_code not found in any log call")


class TestMiddlewareIntegration:
    """Tests for middleware integration."""

    async def test_middleware_chain_executes(self, client):
        """Verify both middlewares execute correctly."""
        response = await client.get("/test")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    async def test_correlation_id_available_in_endpoint(self):
        """Verify correlation ID is accessible in endpoint."""
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        received_id = None

        @app.get("/check")
        async def check_correlation_id(request: Request):
            nonlocal received_id
            received_id = request.state.correlation_id
            return {"correlation_id": received_id}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/check")

        assert response.status_code == 200
        assert received_id is not None
