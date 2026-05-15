"""
Health check service.

Provides health monitoring and status reporting.
Follows the Single Responsibility Principle.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import settings
from app.schemas.health import HealthCheckDetail, HealthCheckResponse


class HealthService:
    """
    Service for health checking application components.

    Performs checks on:
    - Database connectivity
    - Migration status
    - Other critical services
    """

    # Track application start time for uptime calculation
    _start_time: float = time.time()

    def __init__(self, db: Any = None):
        """
        Initialize HealthService.

        Args:
            db: Database instance for health checks (optional, will use singleton if not provided)
        """
        self._db = db

    def _get_database(self) -> Any:
        """
        Get database instance.

        Returns:
            Database instance from parameter or singleton
        """
        if self._db is not None:
            return self._db

        # Import here to avoid circular dependencies
        from app.db.database import db as db_singleton

        return db_singleton

    async def _check_database(self) -> HealthCheckDetail:
        """
        Check database connectivity.

        Performs a ping operation to verify database is responsive.

        Returns:
            HealthCheckDetail with status and metrics
        """
        start_time = time.time()

        try:
            db = self._get_database()

            # Ensure database is connected
            if not db.is_connected:
                await db.connect()

            # Get database instance and ping
            database = db.get_database()
            result = await database.command("ping")

            response_time_ms = (time.time() - start_time) * 1000

            if result.get("ok") == 1.0:
                return HealthCheckDetail(
                    status="pass",
                    response_time_ms=round(response_time_ms, 2),
                    details={"connected": True, "ping_ms": round(response_time_ms, 2)},
                )
            else:
                return HealthCheckDetail(
                    status="fail",
                    response_time_ms=round(response_time_ms, 2),
                    details={
                        "connected": False,
                        "error": "Database ping returned unexpected result",
                    },
                )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheckDetail(
                status="fail",
                response_time_ms=round(response_time_ms, 2),
                details={"connected": False, "error": str(e)},
            )

    async def _check_migrations(self) -> HealthCheckDetail:
        """
        Check migration status.

        Verifies if there are pending migrations that need to be applied.

        Returns:
            HealthCheckDetail with status and migration counts
        """
        start_time = time.time()

        try:
            # Import here to avoid circular dependencies
            from migrations.runner import MigrationRunner

            runner = MigrationRunner()
            status = await runner.status()

            response_time_ms = (time.time() - start_time) * 1000

            pending_count = status.get("pending_count", 0)

            # Status is warn if there are pending migrations
            # This is not critical but should be addressed
            if pending_count > 0:
                return HealthCheckDetail(
                    status="warn",
                    response_time_ms=round(response_time_ms, 2),
                    details={
                        "pending_count": pending_count,
                        "applied_count": status.get("applied_count", 0),
                        "total_migrations": status.get("total_migrations", 0),
                        "message": f"{pending_count} pending migration(s) found",
                    },
                )
            else:
                return HealthCheckDetail(
                    status="pass",
                    response_time_ms=round(response_time_ms, 2),
                    details={
                        "pending_count": 0,
                        "applied_count": status.get("applied_count", 0),
                        "total_migrations": status.get("total_migrations", 0),
                    },
                )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheckDetail(
                status="fail",
                response_time_ms=round(response_time_ms, 2),
                details={"error": str(e), "pending_count": -1},
            )

    def _determine_overall_status(self, checks: Dict[str, HealthCheckDetail]) -> str:
        critical_checks = ["database"]

        has_critical_failure = any(
            checks[check].status == "fail"
            for check in critical_checks
            if check in checks
        )

        if has_critical_failure:
            return "unhealthy"

        # ✅ Solo evaluar checks NO críticos
        non_critical_checks = {
            key: check 
            for key, check in checks.items() 
            if key not in critical_checks      # ← esta es la corrección
        }

        has_non_critical_failure = any(
            check.status in ["fail", "warn"] 
            for check in non_critical_checks.values()
        )

        if has_non_critical_failure:
            return "degraded"

        return "healthy"

    async def check_health(self) -> HealthCheckResponse:
        """
        Perform comprehensive health check.

        Executes all configured health checks and returns aggregated status.

        Returns:
            HealthCheckResponse with overall status and individual check details
        """
        # Run all checks concurrently
        database_detail = await self._check_database()
        migrations_detail = await self._check_migrations()

        checks = {"database": database_detail, "migrations": migrations_detail}
        # Calculate uptime
        uptime_seconds = time.time() - self._start_time

        # Determine overall status
        overall_status = self._determine_overall_status(checks)

        return HealthCheckResponse(
            status=overall_status,
            version=settings.APP_VERSION,
            timestamp=datetime.now(timezone.utc),
            environment=settings.ENVIRONMENT,
            checks=checks,
            uptime_seconds=round(uptime_seconds, 2),
        )

    async def is_healthy(self) -> bool:
        """
        Quick health check for simple status queries.

        Returns:
            True if system is healthy, False otherwise
        """
        health = await self.check_health()
        return health.status == "healthy"


# Singleton instance
health_service = HealthService()
