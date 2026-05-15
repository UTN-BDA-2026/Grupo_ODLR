"""Logging middleware for request correlation.

Adds request IDs and timing to logs for distributed tracing.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation IDs to requests.

    Adds X-Request-ID header for tracing requests through the system.
    Logs request/response timing.

    Attributes:
        header_name: Header name for correlation ID.
    """

    def __init__(self, app, header_name: str = "X-Request-ID") -> None:
        """Initialize middleware.

        Args:
            app: FastAPI application.
            header_name: Correlation ID header name.
        """
        super().__init__(app)
        self._header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response with correlation ID header.
        """
        # Get or generate correlation ID
        correlation_id = request.headers.get(self._header_name) or str(uuid.uuid4())

        # Store in request state for access in endpoints
        request.state.correlation_id = correlation_id

        # Log request start
        start_time = time.time()
        logger.info(
            "Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
            },
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add correlation ID to response
        response.headers[self._header_name] = correlation_id

        # Log request completion
        logger.info(
            "Request completed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses.

    Logs detailed request/response information for debugging.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response.

        Args:
            request: Incoming request.
            call_next: Next handler.

        Returns:
            Response.
        """
        start_time = time.time()

        # Log request
        logger.debug(
            "Incoming request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client": request.client.host if request.client else None,
            },
        )

        # Process
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        logger.debug(
            "Outgoing response",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return response
