"""Tests for logging configuration."""

import json
import logging
from unittest.mock import patch

from minecraft_tools.logging_config import StructuredFormatter, setup_logging


class TestStructuredFormatter:
    """Test structured logging formatter."""

    def test_format_basic_message(self):
        """Test formatting a basic log message."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test_logger"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_format_with_exception(self):
        """Test formatting a log message with exception."""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "ERROR"
        assert data["message"] == "Error occurred"
        assert "exception" in data
        assert "ValueError: Test error" in data["exception"]


class TestSetupLogging:
    """Test logging setup function."""

    def test_setup_logging_default(self):
        """Test default logging setup."""
        with patch("logging.root") as mock_root:
            setup_logging()

        mock_root.setLevel.assert_called_with(logging.INFO)

    def test_setup_logging_debug_level(self):
        """Test logging setup with debug level."""
        with patch("logging.root") as mock_root:
            setup_logging(level="DEBUG")

        mock_root.setLevel.assert_called_with(logging.DEBUG)

    def test_setup_logging_structured(self):
        """Test structured logging setup."""
        with patch("logging.root") as mock_root:
            setup_logging(structured=True)

        # Verify handler was added
        assert len(mock_root.handlers) == 1
        handler = mock_root.handlers[0]
        assert isinstance(handler.formatter, StructuredFormatter)

    def test_logger_suppression(self):
        """Test that noisy loggers are suppressed."""
        with patch("logging.getLogger") as mock_get_logger:
            setup_logging()

            # Verify specific loggers were configured
            expected_calls = [
                "discord.ext.commands.bot",
                "discord.client",
                "boto3",
                "botocore",
            ]

            for logger_name in expected_calls:
                mock_get_logger.assert_any_call(logger_name)
