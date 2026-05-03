"""
Tests for config deduplication and fallback logic.

Verifies that:
- Input chunk_duration falls back to pipeline when not set
- Input chunk_duration is preserved when explicitly set
- Per-input chunk_duration values work correctly
"""

import pytest
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from core.config_schema import SRT2WebConfig


@pytest.mark.unit
class TestChunkDurationFallback:
    """Test chunk_duration fallback logic."""
    
    def test_input_uses_pipeline_chunk_when_not_set(self) -> None:
        """When input chunk_duration is NOT set, should use pipeline value."""
        config_data = {
            "pipeline": {"chunk_duration_sec": 10},
            "input": {
                "srt": {},  # No chunk_duration_sec set
                "rtmp": {},
                "file": {}
            }
        }
        
        config = SRT2WebConfig.from_dict(config_data)
        
        # Should fall back to pipeline value (10)
        assert config.input.srt.chunk_duration_sec == 10
        assert config.input.rtmp.chunk_duration_sec == 10
        assert config.input.file.chunk_duration_sec == 10
    
    def test_input_preserves_explicit_chunk_value(self) -> None:
        """When input chunk_duration IS set, should preserve it."""
        config_data = {
            "pipeline": {"chunk_duration_sec": 10},
            "input": {
                "srt": {"chunk_duration_sec": 5},
                "rtmp": {"chunk_duration_sec": 8},
                "file": {"chunk_duration_sec": 12}
            }
        }
        
        config = SRT2WebConfig.from_dict(config_data)
        
        # Should preserve the explicit values
        assert config.input.srt.chunk_duration_sec == 5
        assert config.input.rtmp.chunk_duration_sec == 8
        assert config.input.file.chunk_duration_sec == 12
    
    def test_partial_input_chunk_values(self) -> None:
        """When some inputs have chunk_duration and others don't."""
        config_data = {
            "pipeline": {"chunk_duration_sec": 10},
            "input": {
                "srt": {"chunk_duration_sec": 5},
                "rtmp": {},  # Not set
                "file": {"chunk_duration_sec": 12}
            }
        }
        
        config = SRT2WebConfig.from_dict(config_data)
        
        # Explicit values preserved, missing ones fallback
        assert config.input.srt.chunk_duration_sec == 5
        assert config.input.rtmp.chunk_duration_sec == 10  # Fallback to pipeline
        assert config.input.file.chunk_duration_sec == 12
    
    def test_srt_input_config_has_chunk_duration_field(self) -> None:
        """Verify SRTInputConfig has chunk_duration_sec field."""
        config_data = {
            "pipeline": {"chunk_duration_sec": 10},
            "input": {
                "srt": {"chunk_duration_sec": 7}
            }
        }
        
        config = SRT2WebConfig.from_dict(config_data)
        
        # Should have the field and value should be preserved
        assert hasattr(config.input.srt, 'chunk_duration_sec')
        assert config.input.srt.chunk_duration_sec == 7
    
    def test_subtitle_generator_uses_pipeline_chunk(self) -> None:
        """Subtitle generator should always use pipeline chunk_duration."""
        config_data = {
            "pipeline": {"chunk_duration_sec": 10},
            "modules": {
                "subtitle_generator": {
                    "enabled": True,
                    "format": "webvtt"
                }
            }
        }
        
        config = SRT2WebConfig.from_dict(config_data)
        
        # Subtitle should sync with pipeline
        assert config.modules.subtitle_generator.chunk_duration == 10


class TestConfigDeduplication:
    """Test that config values are properly deduplicated."""
    
    def test_to_dict_includes_all_chunk_durations(self) -> None:
        """to_dict() should include all chunk_duration values."""
        config_data = {
            "pipeline": {"chunk_duration_sec": 10},
            "input": {
                "srt": {"chunk_duration_sec": 5}
            }
        }
        
        config = SRT2WebConfig.from_dict(config_data)
        result = config.to_dict()
        
        # Should have chunk_duration in input.srt
        assert "input" in result
        assert "srt" in result["input"]
        assert result["input"]["srt"].get("chunk_duration_sec") == 5
    
    def test_full_config_roundtrip(self) -> None:
        """Test that full config survives roundtrip (load -> validate -> save -> load)."""
        original_data = {
            "pipeline": {"chunk_duration_sec": 10},
            "input": {
                "srt": {"chunk_duration_sec": 7},
                "rtmp": {"chunk_duration_sec": 8},
                "file": {"chunk_duration_sec": 9}
            },
            "modules": {
                "subtitle_generator": {"enabled": True, "format": "webvtt"}
            }
        }
        
        # First round
        config1 = SRT2WebConfig.from_dict(original_data)
        dict1 = config1.to_dict()
        
        # Second round
        config2 = SRT2WebConfig.from_dict(dict1)
        dict2 = config2.to_dict()
        
        # Values should be preserved
        assert dict2["input"]["srt"]["chunk_duration_sec"] == 7
        assert dict2["input"]["rtmp"]["chunk_duration_sec"] == 8
        assert dict2["input"]["file"]["chunk_duration_sec"] == 9
        assert dict2["pipeline"]["chunk_duration_sec"] == 10
