"""Tests for logging formatters.

Tests JSON and Text formatters following OCP.
"""

import json
import logging
from io import StringIO

import pytest


class TestJsonFormatter:
    """Tests for JSON formatter."""

    def test_json_formatter_exists(self):
        """Verify JsonFormatter class exists."""
        from app.core.logging.formatters import JsonFormatter

        formatter = JsonFormatter()
        assert formatter is not None

    def test_json_formatter_outputs_valid_json(self, caplog):
        """Verify formatter outputs valid JSON."""
        from app.core.logging.formatters import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # Should be valid JSON
        parsed = json.loads(output)
        assert "message" in parsed or "msg" in parsed

    def test_json_formatter_includes_standard_fields(self):
        """Verify JSON includes standard log fields."""
        from app.core.logging.formatters import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["name"] == "test.logger"
        assert parsed["level"] == "ERROR"
        assert "timestamp" in parsed
        assert parsed["message"] == "Error occurred"

    def test_json_formatter_includes_extra_fields(self):
        """Verify JSON includes extra context fields."""
        from app.core.logging.formatters import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User action",
            args=(),
            exc_info=None,
        )
        record.user_id = "123"
        record.action = "login"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["user_id"] == "123"
        assert parsed["action"] == "login"


class TestTextFormatter:
    """Tests for text formatter."""

    def test_text_formatter_exists(self):
        """Verify TextFormatter class exists."""
        from app.core.logging.formatters import TextFormatter

        formatter = TextFormatter()
        assert formatter is not None

    def test_text_formatter_outputs_readable_format(self):
        """Verify formatter outputs human-readable text."""
        from app.core.logging.formatters import TextFormatter

        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "Test message" in output
        assert "INFO" in output
        assert "test.logger" in output

    def test_text_formatter_includes_timestamp(self):
        """Verify text format includes timestamp."""
        from app.core.logging.formatters import TextFormatter

        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Debug info",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # Should contain timestamp pattern
        import re

        assert re.search(r"\d{4}-\d{2}-\d{2}", output) is not None
