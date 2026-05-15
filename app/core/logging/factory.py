"""Logger factory following SRP.

Single Responsibility: Only creates and configures loggers.
Factory Pattern: Centralizes logger creation.
"""

import logging
import sys
from typing import Literal

from app.core.logging.formatters import JsonFormatter, TextFormatter


class LoggerFactory:
    """Factory for creating configured loggers.

    SRP: Only responsible for logger creation and configuration.
    DRY: Centralizes all logger setup logic.

    Attributes:
        level: Default log level.
        format_type: Output format (text or json).
        propagate: Whether loggers propagate to parent.
    """

    def __init__(
        self,
        level: int = logging.INFO,
        format_type: Literal["text", "json"] = "text",
        propagate: bool = False,
    ) -> None:
        """Initialize factory with configuration.

        Args:
            level: Default log level.
            format_type: Output format type.
            propagate: Propagation setting.
        """
        self._level = level
        self._format_type = format_type
        self._propagate = propagate
        self._formatter = self._create_formatter()

    def _create_formatter(self) -> logging.Formatter:
        """Create formatter based on configuration.

        Returns:
            Configured formatter.
        """
        if self._format_type == "json":
            return JsonFormatter()
        return TextFormatter()

    def _create_handler(self) -> logging.Handler:
        """Create console handler.

        Returns:
            Configured console handler.
        """
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self._formatter)
        return handler

    def create_logger(self, name: str) -> logging.Logger:
        """Create and configure a logger.

        DRY: All loggers created through this method.

        Args:
            name: Logger name.

        Returns:
            Configured logger.
        """
        logger = logging.getLogger(name)
        logger.setLevel(self._level)
        logger.propagate = self._propagate

        # Ensure idempotent and consistent configuration.
        logger.handlers.clear()
        logger.addHandler(self._create_handler())

        return logger
