"""
Logging configuration.

Follows the Single Responsibility Principle for logging setup.
"""

import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure application logging.

    Sets up structured logging for the application.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
