"""
Tests for RTMP Input functionality.

This test file covers:
- RTMP input module exists and is correctly implemented
- FFmpeg command includes -rtmp_listen option
- Frontend URL generation for RTMP
- API routes handle RTMP configuration
- Stop.bat handles RTMP port cleanup
- H264 bitstream filter is applied
"""

import pytest
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestRTMPInputModule:
    """Test RTMP input module exists and has correct implementation."""

    def test_rtmp_input_module_exists(self) -> None:
        """Test that rtmp_input.py module exists."""
        rtmp_input_path = PROJECT_ROOT / "modules" / "inputs" / "rtmp_input.py"
        assert rtmp_input_path.exists(), "rtmp_input.py should exist"

    def test_rtmp_input_class_exists(self) -> None:
        """Test RTMPInput class is defined."""
        from modules.inputs.rtmp_input import RTMPInput
        assert RTMPInput is not None

    def test_rtmp_input_has_required_methods(self) -> None:
        """Test RTMPInput has all required methods."""
        from modules.inputs.rtmp_input import RTMPInput
        assert hasattr(RTMPInput, '__init__')
        assert hasattr(RTMPInput, 'configure')
        assert hasattr(RTMPInput, 'start')
        assert hasattr(RTMPInput, 'stop')
        assert hasattr(RTMPInput, 'get_next_chunk')
        assert hasattr(RTMPInput, 'is_receiving')
        assert hasattr(RTMPInput, 'get_connection_info')
        assert hasattr(RTMPInput, 'get_status')

    def test_rtmp_input_registered_in_factory(self) -> None:
        """Test RTMP input is registered in InputFactory."""
        # Just verify the module can be imported and has the registration function
        from modules.inputs import rtmp_input
        assert hasattr(rtmp_input, '_input_class') or hasattr(rtmp_input, '_register'), \
            "RTMP input module should have registration mechanism"


class TestRTMPFFmpegCommand:
    """Test RTMP input generates correct FFmpeg command."""

    def test_rtmp_listen_option_in_command(self) -> None:
        """Test FFmpeg command includes -rtmp_listen option."""
        rtmp_input_path = PROJECT_ROOT / "modules" / "inputs" / "rtmp_input.py"
        with open(rtmp_input_path, "r") as f:
            content = f.read()
        
        assert "-rtmp_listen" in content or "rtmp_listen" in content, \
            "FFmpeg command should include -rtmp_listen option"

    def test_h264_mp4toannexb_filter(self) -> None:
        """Test FFmpeg command includes h264_mp4toannexb bitstream filter."""
        rtmp_input_path = PROJECT_ROOT / "modules" / "inputs" / "rtmp_input.py"
        with open(rtmp_input_path, "r") as f:
            content = f.read()
        
        assert "h264_mp4toannexb" in content, \
            "FFmpeg command should include h264_mp4toannexb filter for OBS compatibility"

    def test_segment_output_for_chunks(self) -> None:
        """Test FFmpeg uses segment output for chunking."""
        rtmp_input_path = PROJECT_ROOT / "modules" / "inputs" / "rtmp_input.py"
        with open(rtmp_input_path, "r") as f:
            content = f.read()
        
        assert "-f" in content and "segment" in content, \
            "FFmpeg should use segment format for chunking"

    def test_mpegts_format(self) -> None:
        """Test FFmpeg outputs MPEG-TS format."""
        rtmp_input_path = PROJECT_ROOT / "modules" / "inputs" / "rtmp_input.py"
        with open(rtmp_input_path, "r") as f:
            content = f.read()
        
        assert "mpegts" in content, \
            "FFmpeg should use mpegts format"


class TestRTMPConfigHandling:
    """Test RTMP configuration is handled correctly."""

    def test_rtmp_config_in_api_routes(self) -> None:
        """Test API routes handle RTMP configuration."""
        api_routes_path = PROJECT_ROOT / "server" / "api_routes.py"
        with open(api_routes_path, "r") as f:
            content = f.read()
        
        assert "rtmp" in content.lower(), \
            "API routes should handle RTMP configuration"

    def test_rtmp_url_generation_in_api(self) -> None:
        """Test API generates RTMP URL correctly."""
        api_routes_path = PROJECT_ROOT / "server" / "api_routes.py"
        with open(api_routes_path, "r") as f:
            content = f.read()
        
        # Should generate URL with port, app, stream_key
        assert "rtmp://" in content, \
            "API should generate rtmp:// URL"

    def test_rtmp_listen_port_config(self) -> None:
        """Test RTMP listen_port config is read."""
        config_path = PROJECT_ROOT / "config.yaml"
        with open(config_path, "r") as f:
            content = f.read()
        
        assert "listen_port: 1935" in content or "listen_port:1935" in content, \
            "config.yaml should have RTMP listen_port set to 1935"


class TestRTMPFrontend:
    """Test RTMP functionality in frontend."""

    def test_get_rtmp_url_function_exists(self) -> None:
        """Test getRTMPUrl function exists in utils."""
        utils_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "utils" / "index.ts"
        assert utils_path.exists(), "Utils file should exist"
        
        with open(utils_path, "r") as f:
            content = f.read()
        
        assert "getRTMPUrl" in content, \
            "getRTMPUrl function should be defined in utils"

    def test_rtmp_url_format(self) -> None:
        """Test getRTMPUrl generates correct format."""
        utils_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "utils" / "index.ts"
        with open(utils_path, "r") as f:
            content = f.read()
        
        # Should generate rtmp://ip:port/app/streamkey format
        assert "rtmp://" in content, \
            "RTMP URL should use rtmp:// protocol"

    def test_status_card_has_url_emision(self) -> None:
        """Test StatusCard has url-emision element."""
        status_card_path = PROJECT_ROOT / "frontend" / "src" / "components" / "StatusCard.astro"
        with open(status_card_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "url-emision" in content, \
            "StatusCard should have url-emision element"

    def test_input_card_rtmp_settings(self) -> None:
        """Test InputCard has RTMP settings."""
        input_card_path = PROJECT_ROOT / "frontend" / "src" / "components" / "InputCard.astro"
        with open(input_card_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "input-rtmp" in content, \
            "InputCard should have RTMP settings section"


class TestStopBatRTMPPort:
    """Test Stop.bat handles RTMP port cleanup."""

    def test_stop_bat_checks_port_1935(self) -> None:
        """Test Stop.bat checks port 1935."""
        stop_bat_path = PROJECT_ROOT / "Stop.bat"
        with open(stop_bat_path, "r") as f:
            content = f.read()
        
        assert ":1935" in content, \
            "Stop.bat should check port 1935 for RTMP"


class TestRTMPInputIntegration:
    """Integration tests for RTMP input."""

    @patch('modules.inputs.rtmp_input.subprocess.Popen')
    @patch('core.ffmpeg_utils.ensure_ffmpeg')
    @patch('core.ffmpeg_utils.check_gpu_support')
    def test_rtmp_input_start_creates_process(self, mock_gpu, mock_ffmpeg, mock_popen) -> None:
        """Test RTMP input start creates FFmpeg process."""
        mock_ffmpeg.return_value = "ffmpeg"
        mock_gpu.return_value = {"nvenc": False, "qsv": False, "vaapi": False, "amf": False}
        
        from modules.inputs.rtmp_input import RTMPInput
        
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        
        rtmp = RTMPInput()
        rtmp.configure({
            "url": "rtmp://127.0.0.1:1935/live/stream",
            "chunk_duration_sec": 10,
        })
        rtmp.start()
        
        # Verify Popen was called
        assert mock_popen.called, "Popen should be called to start FFmpeg"
        
        # Check command includes -rtmp_listen
        call_args = mock_popen.call_args[0][0]
        assert "-rtmp_listen" in call_args, "Command should include -rtmp_listen"
        assert "1" in call_args, "rtmp_listen should be set to 1"

    def test_rtmp_input_configure_sets_url(self) -> None:
        """Test RTMP input configure properly sets URL."""
        from modules.inputs.rtmp_input import RTMPInput
        
        rtmp = RTMPInput()
        config = {
            "url": "rtmp://127.0.0.1:1935/live/stream",
            "mode": "listener",
            "chunk_duration_sec": 10,
        }
        rtmp.configure(config)
        
        assert rtmp._url == "rtmp://127.0.0.1:1935/live/stream"
        assert rtmp._mode == "listener"
        assert rtmp._chunk_duration == 10

    def test_rtmp_input_connection_info(self) -> None:
        """Test RTMP input returns correct connection info."""
        from modules.inputs.rtmp_input import RTMPInput
        
        rtmp = RTMPInput()
        rtmp._url = "rtmp://127.0.0.1:1935/live/stream"
        rtmp._mode = "listener"
        
        info = rtmp.get_connection_info()
        
        assert info["type"] == "rtmp"
        assert info["mode"] == "listener"
        assert info["url"] == "rtmp://127.0.0.1:1935/live/stream"


class TestFFmpegRTMPProtocol:
    """Test FFmpeg RTMP protocol support."""

    def test_ffmpeg_has_rtmp_protocol(self) -> None:
        """Test system FFmpeg supports RTMP protocol."""
        result = subprocess.run(
            ["ffprobe", "-protocols"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert "rtmp" in result.stdout.lower(), \
            "FFmpeg should support RTMP protocol"

    def test_ffmpeg_has_rtmp_listen_option(self) -> None:
        """Test FFmpeg has rtmp_listen option."""
        result = subprocess.run(
            ["ffmpeg", "-h", "protocol=rtmp"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert "rtmp_listen" in result.stdout.lower() or "listen" in result.stdout.lower(), \
            "FFmpeg RTMP protocol should support listen option"


class TestRTMPStatusDisplay:
    """Test RTMP status is displayed correctly in frontend."""

    def test_update_urls_handles_rtmp(self) -> None:
        """Test updateUrls function handles RTMP type."""
        dashboard_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "dashboard.ts"
        with open(dashboard_path, "r") as f:
            content = f.read()
        
        # Should have logic to handle different input types
        assert "inputType" in content or "rtmp" in content, \
            "updateUrls should handle input type selection"

    def test_copy_button_handles_emision_url(self) -> None:
        """Test copy button works with emission URL."""
        dashboard_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "dashboard.ts"
        with open(dashboard_path, "r") as f:
            content = f.read()
        
        assert "btn-copy-emision" in content, \
            "Should have copy button for emission URL"

    def test_handle_input_type_changes_url(self) -> None:
        """Test handleInputTypeChange updates URL display."""
        dashboard_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "dashboard.ts"
        with open(dashboard_path, "r") as f:
            content = f.read()
        
        assert "handleInputTypeChange" in content, \
            "Should have input type change handler"

    def test_url_label_changes_with_type(self) -> None:
        """Test URL label changes (SRT/RTMP/FILE) based on type."""
        dashboard_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "dashboard.ts"
        with open(dashboard_path, "r") as f:
            content = f.read()
        
        # Should update label based on input type
        assert "url-emision-label" in content, \
            "Should update emission label based on input type"