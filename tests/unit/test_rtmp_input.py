"""
Test RTMP Input Module

Tests for RTMP input functionality including pull and push modes.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestRTMPInput:
    """Test RTMP input module."""
    
    def test_rtmp_input_import(self):
        """Test that RTMPInput can be imported."""
        from modules.inputs.rtmp_input import RTMPInput
        assert RTMPInput is not None
    
    def test_rtmp_input_instantiation(self):
        """Test RTMPInput can be instantiated."""
        from modules.inputs.rtmp_input import RTMPInput
        
        config = {
            "url": "rtmp://localhost/live/stream",
            "mode": "pull",
            "listen": False,
            "chunk_duration_sec": 6
        }
        
        input_module = RTMPInput(config)
        assert input_module is not None
        assert input_module._mode == "pull"
        assert input_module._listen == False
    
    def test_rtmp_input_push_mode_config(self):
        """Test RTMPInput push mode configuration."""
        from modules.inputs.rtmp_input import RTMPInput
        
        config = {
            "url": "rtmp://localhost:1935/live/stream",
            "mode": "push",
            "listen": True,
            "chunk_duration_sec": 6
        }
        
        input_module = RTMPInput(config)
        assert input_module._mode == "push"
        assert input_module._listen == True
    
    def test_rtmp_input_factory_registration(self):
        """Test RTMPInput is registered in InputFactory."""
        from core.io_factory import InputFactory
        
        # Force initialization
        InputFactory._ensure_initialized()
        
        available = InputFactory.available()
        assert "rtmp" in available
    
    def test_rtmp_input_module_wrapper(self):
        """Test RTMPInput can be wrapped as a module."""
        from modules.inputs.rtmp_input import RTMPInput
        from modules.io_wrappers import InputModuleWrapper
        
        config = {
            "url": "rtmp://localhost/live/stream",
            "mode": "pull",
            "listen": False,
            "chunk_duration_sec": 6
        }
        
        input_source = RTMPInput(config)
        wrapper = InputModuleWrapper("rtmp_input", input_source, {"enabled": True})
        
        assert hasattr(wrapper, 'is_input_module')
        assert wrapper.is_input_module == True


class TestRTMPOutput:
    """Test RTMP output module."""
    
    def test_rtmp_output_import(self):
        """Test that RTMPOutput can be imported."""
        from modules.outputs.rtmp_output import RTMPOutput
        assert RTMPOutput is not None
    
    def test_rtmp_output_instantiation(self):
        """Test RTMPOutput can be instantiated."""
        from modules.outputs.rtmp_output import RTMPOutput
        
        config = {
            "url": "rtmp://localhost/live/output",
            "video_bitrate": "2500k",
            "audio_bitrate": "128k"
        }
        
        output_module = RTMPOutput(config)
        assert output_module is not None
        assert output_module._url == "rtmp://localhost/live/output"
    
    def test_rtmp_output_factory_registration(self):
        """Test RTMPOutput is registered in OutputFactory."""
        from core.io_factory import OutputFactory
        
        # Force initialization
        OutputFactory._ensure_initialized()
        
        available = OutputFactory.available()
        assert "rtmp" in available
    
    def test_rtmp_output_module_wrapper(self):
        """Test RTMPOutput can be wrapped as a module."""
        from modules.outputs.rtmp_output import RTMPOutput
        from modules.io_wrappers import OutputModuleWrapper
        
        config = {
            "url": "rtmp://localhost/live/output",
            "video_bitrate": "2500k",
            "audio_bitrate": "128k"
        }
        
        output_sink = RTMPOutput(config)
        wrapper = OutputModuleWrapper("rtmp_output", output_sink, {"enabled": True})
        
        assert hasattr(wrapper, 'is_output_module')
        assert wrapper.is_output_module == True


class TestOutputMultiplexer:
    """Test OutputMultiplexer functionality."""
    
    def test_output_multiplexer_import(self):
        """Test that OutputMultiplexer can be imported."""
        from core.output_multiplexer import OutputMultiplexer
        assert OutputMultiplexer is not None
    
    def test_output_multiplexer_instantiation(self):
        """Test OutputMultiplexer can be instantiated."""
        from core.output_multiplexer import OutputMultiplexer
        
        multiplexer = OutputMultiplexer()
        assert multiplexer is not None
        assert multiplexer.enabled == True
        assert len(multiplexer.get_outputs()) == 0
    
    def test_output_multiplexer_add_output(self):
        """Test adding outputs to multiplexer."""
        from core.output_multiplexer import OutputMultiplexer
        from modules.outputs.rtmp_output import RTMPOutput
        from modules.io_wrappers import OutputModuleWrapper
        
        multiplexer = OutputMultiplexer()
        
        # Create a mock output
        config = {"url": "rtmp://localhost/live/output1"}
        output_sink = RTMPOutput(config)
        output_module = OutputModuleWrapper("output1", output_sink, {"enabled": True})
        
        multiplexer.add_output(output_module)
        
        assert len(multiplexer.get_outputs()) == 1
        assert multiplexer.get_outputs()[0].name == "output1"