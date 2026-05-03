"""
Tests for core/structured_log.py - Correlation ID feature.
"""

import sys
import os
import json
import time
from datetime import datetime
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.structured_log import ModuleLogger, log_structured, parse_structured_log


@pytest.mark.unit
class TestCorrelationId:
    """Test correlation ID functionality."""

    def test_generate_correlation_id(self):
        """Test that generate_correlation_id returns a valid UUID string."""
        logger = ModuleLogger("test_module")
        corr_id = logger.generate_correlation_id()
        
        assert isinstance(corr_id, str)
        assert len(corr_id) > 0
        # Should be a valid UUID format (basic check)
        parts = corr_id.split('-')
        assert len(parts) == 5  # UUID has 5 parts

    def test_set_correlation_id_auto_generate(self):
        """Test set_correlation_id with None generates a new ID."""
        logger = ModuleLogger("test_module")
        corr_id = logger.set_correlation_id(None)
        
        assert isinstance(corr_id, str)
        assert logger._correlation_id == corr_id

    def test_set_correlation_id_explicit(self):
        """Test set_correlation_id with an explicit ID."""
        logger = ModuleLogger("test_module")
        explicit_id = "test-corr-12345"
        result = logger.set_correlation_id(explicit_id)
        
        assert result == explicit_id
        assert logger._correlation_id == explicit_id

    def test_clear_correlation_id(self):
        """Test clear_correlation_id removes the ID."""
        logger = ModuleLogger("test_module")
        logger.set_correlation_id("some-id")
        assert logger._correlation_id is not None
        
        logger.clear_correlation_id()
        assert logger._correlation_id is None

    def test_log_structured_includes_correlation_id(self):
        """Test that log_structured includes correlation_id when provided."""
        # Capture log output
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger("srt2web.structured")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        try:
            log_structured(
                module="test_module",
                stage="test_stage",
                level="info",
                correlation_id="test-corr-123",
                message="Test message"
            )
            
            log_output = log_capture.getvalue()
            # Parse the JSON from log output
            # Find JSON in the log line
            start = log_output.find('{')
            end = log_output.rfind('}') + 1
            json_str = log_output[start:end]
            log_data = json.loads(json_str)
            
            assert "correlation_id" in log_data
            assert log_data["correlation_id"] == "test-corr-123"
        finally:
            logger.removeHandler(handler)

    def test_module_logger_includes_correlation_id(self):
        """Test that ModuleLogger._log includes correlation_id."""
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        test_logger = logging.getLogger("srt2web.test_module")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            logger = ModuleLogger("test_module")
            logger.set_correlation_id("my-corr-id")
            
            # Log something - this should include correlation_id
            logger.info("test_stage", message="Test with correlation")
            
            log_output = log_capture.getvalue()
            start = log_output.find('{')
            end = log_output.rfind('}') + 1
            if start != -1 and end > start:
                json_str = log_output[start:end]
                log_data = json.loads(json_str)
                # correlation_id should be included from context
                assert log_data.get("correlation_id") == "my-corr-id"
        finally:
            test_logger.removeHandler(handler)

    def test_module_logger_without_correlation_id(self):
        """Test that ModuleLogger works without correlation_id set."""
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        test_logger = logging.getLogger("srt2web.test_module2")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            logger = ModuleLogger("test_module2")
            # Don't set correlation_id
            
            logger.info("test_stage", message="Test without correlation")
            
            log_output = log_capture.getvalue()
            start = log_output.find('{')
            end = log_output.rfind('}') + 1
            if start != -1 and end > start:
                json_str = log_output[start:end]
                log_data = json.loads(json_str)
                # correlation_id should NOT be present
                assert "correlation_id" not in log_data
        finally:
            test_logger.removeHandler(handler)

    def test_time_stage_includes_correlation_id(self):
        """Test that time_stage context manager includes correlation_id."""
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        test_logger = logging.getLogger("srt2web.test_module3")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            logger = ModuleLogger("test_module3")
            logger.set_correlation_id("stage-corr-id")
            
            with logger.time_stage("test_operation") as ctx:
                pass
            
            log_output = log_capture.getvalue()
            start = log_output.find('{')
            end = log_output.rfind('}') + 1
            if start != -1 and end > start:
                json_str = log_output[start:end]
                log_data = json.loads(json_str)
                assert log_data.get("correlation_id") == "stage-corr-id"
                assert "duration_ms" in log_data
        finally:
            test_logger.removeHandler(handler)

    def test_parse_structured_log_with_correlation_id(self):
        """Test parse_structured_log extracts correlation_id."""
        log_line = 'INFO:srt2web:{"module": "test", "stage": "test", "correlation_id": "abc-123", "timestamp": 1234567890}'
        
        result = parse_structured_log(log_line)
        
        assert result is not None
        assert result.get("correlation_id") == "abc-123"

    def test_parse_structured_log_without_correlation_id(self):
        """Test parse_structured_log works without correlation_id."""
        log_line = 'INFO:srt2web:{"module": "test", "stage": "test", "timestamp": 1234567890}'
        
        result = parse_structured_log(log_line)
        
        assert result is not None
        assert "correlation_id" not in result


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
