"""Tests for LoggerFactory.

Follows SRP - Factory creates loggers, doesn't configure them directly.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest


class TestLoggerFactory:
    """Tests for LoggerFactory class."""

    def test_factory_creates_logger(self):
        """Verify factory creates logger instances."""
        from app.core.logging.factory import LoggerFactory

        factory = LoggerFactory()
        logger = factory.create_logger("test.module")

        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_factory_configures_log_level(self):
        """Verify factory configures log level from settings."""
        from app.core.logging.factory import LoggerFactory

        factory = LoggerFactory(level=logging.DEBUG)
        logger = factory.create_logger("test.debug")

        assert logger.level == logging.DEBUG

    def test_factory_adds_handlers(self):
        """Verify factory adds handlers to logger."""
        from app.core.logging.factory import LoggerFactory

        factory = LoggerFactory()
        logger = factory.create_logger("test.handlers")

        assert len(logger.handlers) > 0

    def test_factory_prevents_duplicate_handlers(self):
        """Verify factory doesn't add duplicate handlers."""
        from app.core.logging.factory import LoggerFactory

        factory = LoggerFactory()

        # Create logger twice
        logger1 = factory.create_logger("test.duplicate")
        handler_count = len(logger1.handlers)

        logger2 = factory.create_logger("test.duplicate")

        assert len(logger2.handlers) == handler_count

    def test_factory_uses_correct_formatter(self):
        """Verify factory uses configured formatter."""
        from app.core.logging.factory import LoggerFactory
        from app.core.logging.formatters import JsonFormatter

        factory = LoggerFactory(format_type="json")
        logger = factory.create_logger("test.format")

        # Check first handler has JsonFormatter
        if logger.handlers:
            formatter = logger.handlers[0].formatter
            assert isinstance(formatter, JsonFormatter)

    def test_factory_propagate_setting(self):
        """Verify factory configures propagate setting."""
        from app.core.logging.factory import LoggerFactory

        factory = LoggerFactory(propagate=False)
        logger = factory.create_logger("test.propagate")

        assert logger.propagate is False
