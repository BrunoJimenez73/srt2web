"""
Tests for structured JSON logging (F50).
"""

import json
import logging

from core.logging_setup import JSONFormatter, setup_logging


class TestJSONFormatter:
    def test_format_basic(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="srt2web.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Hello world",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "srt2web.test"
        assert parsed["message"] == "Hello world"
        assert "timestamp" in parsed
        assert "module" in parsed

    def test_format_with_correlation_id(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="srt2web.pipeline",
            level=logging.DEBUG,
            pathname="pipeline.py",
            lineno=42,
            msg="Processing chunk",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "abc-123"
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["correlation_id"] == "abc-123"

    def test_format_with_duration_ms(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="srt2web.module",
            level=logging.WARNING,
            pathname="module.py",
            lineno=10,
            msg="Slow operation",
            args=(),
            exc_info=None,
        )
        record.duration_ms = 1500
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["duration_ms"] == 1500

    def test_format_is_valid_json(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="e.py",
            lineno=5,
            msg="Error with special chars: ~!@#$%",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)  # must not raise
        assert parsed["message"] == "Error with special chars: ~!@#$%"


class TestSetupLogging:
    def test_setup_logging_json_format(self, tmp_path):
        log_file = str(tmp_path / "test.json.log")
        setup_logging(log_file=log_file, log_level=logging.DEBUG, log_format="json")
        logger = logging.getLogger("srt2web.f50test")
        logger.info("JSON test message")
        logger.debug("Debug with %s", "params")
        # setup_logging adds handlers to the root logger; child loggers propagate
        root_handler = logging.root.handlers[0] if logging.root.handlers else None
        assert root_handler is not None, "Root logger should have at least one handler after setup_logging"

    def test_json_formatter_is_valid(self):
        fmt = JSONFormatter()
        assert isinstance(fmt, logging.Formatter)
        record = logging.LogRecord("t", logging.INFO, "f.py", 1, "msg", (), None)
        out = fmt.format(record)
        json.loads(out)  # must be valid JSON
