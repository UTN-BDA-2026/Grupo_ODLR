"""
Health check endpoints.

Handles HTTP requests for health monitoring.
Follows the Single Responsibility Principle.
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.schemas.health import HealthCheckResponse
from app.services.health_service import HealthService, health_service

router = APIRouter()


def get_health_service() -> HealthService:
    """
    Dependency provider for HealthService.

    Returns:
        HealthService singleton instance
    """
    return health_service


@router.get(
    "/",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="""
    Comprehensive health check endpoint that verifies:
    - Database connectivity
    - Migration status
    - Application uptime

    Returns 200 for healthy/degraded status.
    Returns 503 for unhealthy status (critical failures).
    """,
    responses={
        status.HTTP_200_OK: {
            "description": "System is healthy or degraded",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "version": "1.0.0",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "environment": "production",
                        "checks": {
                            "database": {
                                "status": "pass",
                                "response_time_ms": 15.2,
                                "details": {"connected": True},
                            },
                            "migrations": {
                                "status": "pass",
                                "response_time_ms": 5.1,
                                "details": {"pending_count": 0},
                            },
                        },
                        "uptime_seconds": 3600,
                    }
                }
            },
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "System is unhealthy (critical failures)",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "version": "1.0.0",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "environment": "production",
                        "checks": {
                            "database": {
                                "status": "fail",
                                "response_time_ms": 0,
                                "details": {"error": "Connection refused"},
                            }
                        },
                        "uptime_seconds": 3600,
                    }
                }
            },
        },
    },
)
async def health_check(
    service: HealthService = Depends(get_health_service),
) -> HealthCheckResponse:
    """
    Perform comprehensive health check.

    Verifies all critical and non-critical components of the application.

    Args:
        service: HealthService instance (injected via dependency)

    Returns:
        HealthCheckResponse with status of all components

    Raises:
        HTTPException: If health check cannot be performed
    """
    result = await service.check_health()

    # Return 503 for unhealthy status
    if result.status == "unhealthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=result.model_dump(mode="json"),
        )

    return result


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="""
    Lightweight readiness check for orchestrators.

    Returns 200 if the application is ready to accept requests.
    Returns 503 if the application is not ready (e.g., database unavailable).
    """,
    responses={
        status.HTTP_200_OK: {"description": "Application is ready"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Application is not ready"
        },
    },
)
async def readiness_check(service: HealthService = Depends(get_health_service)) -> dict:
    """
    Lightweight readiness check.

    Used by Kubernetes and other orchestrators to determine
    if the application is ready to accept traffic.

    Args:
        service: HealthService instance (injected via dependency)

    Returns:
        Simple JSON with ready status
    """
    is_healthy = await service.is_healthy()

    if not is_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"ready": False}
        )

    return {"ready": True}


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="""
    Lightweight liveness check for orchestrators.

    Returns 200 if the application is running.
    Used by Kubernetes to detect and restart crashed containers.
    """,
    responses={status.HTTP_200_OK: {"description": "Application is alive"}},
)
async def liveness_check() -> dict:
    """
    Lightweight liveness check.

    This endpoint should always return 200 as long as
    the application process is running.

    Returns:
        Simple JSON indicating the application is alive
    """
    return {"alive": True}
