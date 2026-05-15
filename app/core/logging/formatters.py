"""Log formatters following OCP.

Open for extension: New formatters can be added without modifying existing code.
Closed for modification: Existing formatters remain stable.
"""

import json
import logging
from datetime import datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    OCP: Extends logging.Formatter, doesn't modify it.
    DRY: Reuses parent class structure.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format.

        Returns:
            JSON string.
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "pathname": record.pathname,
            "lineno": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
            }:
                log_data[key] = value

        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter.

    OCP: Alternative formatter following same interface.
    KISS: Simple, readable format for development.
    """

    def __init__(self) -> None:
        """Initialize with default format."""
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as readable text.

        Args:
            record: Log record to format.

        Returns:
            Formatted string.
        """
        # Format base message
        formatted = super().format(record)

        # Add extra context if present
        extra_fields = []
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "asctime",
                "message",
                "getMessage",
            }:
                extra_fields.append(f"{key}={value}")

        if extra_fields:
            formatted += f" | {' '.join(extra_fields)}"

        return formatted
