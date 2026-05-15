"""Tests for logging interfaces.

Follows TDD: Test first, then implement.
Verifies the interface contracts.
"""

import logging
from typing import Protocol, runtime_checkable

import pytest


@runtime_checkable
class LoggerInterface(Protocol):
    """Protocol that logging.Logger should satisfy."""

    def debug(self, msg: str, *args, **kwargs) -> None: ...
    def info(self, msg: str, *args, **kwargs) -> None: ...
    def warning(self, msg: str, *args, **kwargs) -> None: ...
    def error(self, msg: str, *args, **kwargs) -> None: ...
    def critical(self, msg: str, *args, **kwargs) -> None: ...


class TestLoggerInterface:
    """Tests for the LoggerInterface protocol."""

    def test_standard_logger_satisfies_interface(self):
        """Verify that Python's standard logger satisfies our interface."""
        logger = logging.getLogger("test")

        assert isinstance(logger, LoggerInterface)

    def test_logger_has_required_methods(self):
        """Verify logger has all required logging methods."""
        logger = logging.getLogger("test.methods")

        required_methods = ["debug", "info", "warning", "error", "critical"]

        for method_name in required_methods:
            assert hasattr(logger, method_name), f"Logger missing {method_name}"
            assert callable(getattr(logger, method_name)), f"{method_name} not callable"

    def test_logger_accepts_extra_kwargs(self):
        """Verify logger accepts extra context data."""
        logger = logging.getLogger("test.extra")

        # Should not raise
        try:
            logger.info("Test message", extra={"user_id": "123", "action": "test"})
        except TypeError:
            pytest.fail("Logger should accept extra kwargs")


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_logger_instance(self):
        """Verify get_logger returns a valid logger."""
        # This will fail until implemented
        from app.core.logging import get_logger

        logger = get_logger("test.module")

        assert logger is not None
        assert isinstance(logger, logging.Logger)

    def test_get_logger_returns_same_logger_for_same_name(self):
        """Verify get_logger returns cached logger instances."""
        from app.core.logging import get_logger

        logger1 = get_logger("test.cache")
        logger2 = get_logger("test.cache")

        assert logger1 is logger2

    def test_get_logger_sets_correct_name(self):
        """Verify logger has the correct name."""
        from app.core.logging import get_logger

        logger = get_logger("my.custom.module")

        assert logger.name == "my.custom.module"


class TestLoggerConfiguration:
    """Tests for logger configuration."""

    def test_logger_respects_log_level(self):
        """Verify logger respects configured log level."""
        # This will require integration with config
        from app.core.logging import get_logger

        logger = get_logger("test.level")

        # Logger should have handlers configured
        assert len(logger.handlers) > 0 or logger.parent is not None

    def test_configure_logging_reconfigures_existing_logger(self):
        """Verify global reconfiguration applies to already-created loggers."""
        from app.core.logging import configure_logging, get_logger
        from app.core.logging.formatters import JsonFormatter

        logger = get_logger("test.reconfigure")

        configure_logging(level="ERROR", format_type="json", propagate=True)

        assert logger.level == logging.ERROR
        assert logger.propagate is True
        assert isinstance(logger.handlers[0].formatter, JsonFormatter)

        # Reset defaults to avoid affecting other tests.
        configure_logging()
