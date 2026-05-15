"""
Health check schemas.

Pydantic models for health check responses.
Follows the Single Responsibility Principle.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class HealthCheckDetail(BaseModel):
    """
    Detail of an individual health check.

    Contains the status and metadata for a specific component check.
    """

    status: str = Field(..., description="Status: 'pass', 'fail', or 'warn'")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional check details"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "pass",
                "response_time_ms": 15.2,
                "details": {"ping_ms": 12.5},
            }
        }
    )


class HealthCheckResponse(BaseModel):
    """
    Health check response schema.

    Defines the structure of health check data returned to clients.
    Includes overall status and individual component checks.
    """

    status: str = Field(
        ..., description="Overall status: 'healthy', 'degraded', or 'unhealthy'"
    )
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="UTC timestamp of the check")
    environment: str = Field(..., description="Current environment")
    checks: Dict[str, HealthCheckDetail] = Field(
        ..., description="Individual component checks"
    )
    uptime_seconds: Optional[float] = Field(
        default=None, description="Application uptime in seconds"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "environment": "production",
                "checks": {
                    "database": {
                        "status": "pass",
                        "response_time_ms": 15.2,
                        "details": {"connected": True, "ping_ms": 12.5},
                    },
                    "migrations": {
                        "status": "pass",
                        "response_time_ms": 5.1,
                        "details": {"pending_count": 0, "applied_count": 4},
                    },
                },
                "uptime_seconds": 3600,
            }
        }
    )
