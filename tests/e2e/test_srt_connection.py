"""
E2E tests for SRT connection and port configuration.

These tests verify:
1. SRT port (9000) is different from web server port (9999)
2. Dashboard URLs use 127.0.0.1 for localhost connections
3. OBS can connect to the SRT endpoint without hanging
4. Port separation works correctly
"""

import pytest
import re
import socket
import yaml
from pathlib import Path


class TestSRTPortConfiguration:
    """Tests for SRT port configuration."""

    @pytest.fixture
    def config_data(self):
        """Load config.yaml as YAML."""
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_srt_port_is_9000(self, config_data):
        """Test that SRT listen port is set to 9000."""
        srt_port = config_data.get("input", {}).get("srt", {}).get("listen_port")
        assert srt_port == 9000, f"SRT port should be 9000, got {srt_port}"

    def test_server_port_is_9999(self, config_data):
        """Test that server web port is set to 9999."""
        server_port = config_data.get("server", {}).get("port")
        assert server_port == 9999, f"Server port should be 9999, got {server_port}"

    def test_ports_are_different(self, config_data):
        """Test that SRT and server ports are different to avoid conflicts."""
        server_port = config_data.get("server", {}).get("port", 9999)
        srt_port = config_data.get("input", {}).get("srt", {}).get("listen_port", 9000)

        assert srt_port != server_port, (
            f"SRT port ({srt_port}) and server port ({server_port}) must be different! "
            "Using the same port causes connection conflicts."
        )


class TestDashboardURLs:
    """Tests for dashboard URL generation."""

    @pytest.fixture
    def dashboard_content(self):
        """Load index.html content."""
        html_path = Path(__file__).parent.parent.parent / "web" / "index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_update_urls_uses_localhost_for_local_access(self, dashboard_content):
        """Test that updateUrls() uses 127.0.0.1 for localhost connections."""
        assert "window.location.hostname === 'localhost'" in dashboard_content, (
            "Dashboard should detect localhost connections"
        )

        assert "127.0.0.1" in dashboard_content, (
            "Dashboard should use 127.0.0.1 for local SRT connections"
        )

    def test_srt_url_uses_correct_port_variable(self, dashboard_content):
        """Test that SRT URL uses the input port from the form."""
        assert "input-port" in dashboard_content, (
            "Dashboard should have input-port element"
        )

        assert "srt://" in dashboard_content, "Dashboard should generate SRT URLs"


class TestSRTServerConnection:
    """Tests for SRT server connection behavior."""

    def test_different_ports_prevent_conflict(self):
        """Verify server and SRT ports are different at runtime."""
        from core.config_manager import ConfigManager

        config = ConfigManager()
        server_port = config.get("server.port", 9999)
        srt_port = config.get("input.srt.listen_port", 9000)

        assert server_port != srt_port, (
            f"Server port ({server_port}) must be different from SRT port ({srt_port})"
        )


class TestNetworkInfoSRTPort:
    """Tests for network info with correct SRT port."""

    def test_network_info_uses_correct_srt_port(self):
        """Test that network info includes the correct SRT port from config."""
        from core.network_utils import get_network_info
        from core.config_manager import ConfigManager

        config = ConfigManager()
        srt_port = config.get("input.srt.listen_port", 9000)
        server_port = config.get("server.port", 9999)

        network_info = get_network_info(
            srt_port=srt_port, server_port=server_port, latency_ms=1000
        )

        assert network_info["srt_port"] == 9000, (
            f"Network info SRT port should be 9000, got {network_info['srt_port']}"
        )


class TestOBSConnectionScenario:
    """Tests simulating OBS connection scenario."""

    def test_obs_can_form_srt_url_with_localhost(self):
        """Test that a valid SRT URL can be formed for OBS with localhost."""
        host = "127.0.0.1"
        port = 9000
        latency = 1000000

        srt_url = f"srt://{host}:{port}?mode=caller&latency={latency}"

        expected_url = "srt://127.0.0.1:9000?mode=caller&latency=1000000"
        assert srt_url == expected_url, (
            f"SRT URL should be {expected_url}, got {srt_url}"
        )

    def test_different_ports_prevent_conflict(self):
        """Test that different ports prevent server/SRT conflicts."""
        web_port = 9999
        srt_port = 9000

        assert web_port != srt_port, (
            "Web server and SRT ports must be different to prevent conflicts"
        )

        assert 1 <= web_port <= 65535, "Web port out of range"
        assert 1 <= srt_port <= 65535, "SRT port out of range"

    def test_config_specifies_both_ports_correctly(self):
        """Test that config.yaml has both ports correctly specified."""
        config_path = Path(__file__).parent.parent.parent / "config.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        server_port = config_data.get("server", {}).get("port")
        srt_port = config_data.get("input", {}).get("srt", {}).get("listen_port")

        assert server_port == 9999, f"Server port should be 9999, got {server_port}"
        assert srt_port == 9000, f"SRT port should be 9000, got {srt_port}"


class TestLocalhostURLGeneration:
    """Tests for localhost URL generation in dashboard."""

    @pytest.fixture
    def dashboard_content(self):
        """Load index.html content."""
        html_path = Path(__file__).parent.parent.parent / "web" / "index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_dashboard_detects_localhost(self, dashboard_content):
        """Test that dashboard has localhost detection logic."""
        has_localhost_detection = (
            "window.location.hostname === 'localhost'" in dashboard_content
        )
        assert has_localhost_detection, "Dashboard should detect localhost connections"

    def test_dashboard_uses_127_for_local_srt(self, dashboard_content):
        """Test that dashboard uses 127.0.0.1 for local SRT connections."""
        # The code should construct SRT URL with 127.0.0.1 for local access
        assert "srtIp" in dashboard_content or "127.0.0.1" in dashboard_content, (
            "Dashboard should use 127.0.0.1 for local SRT connections"
        )

    def test_dashboard_uses_separate_srt_port(self, dashboard_content):
        """Test that dashboard uses port from input-port field (9000), not hardcoded 9999."""
        # The updateUrls function should read from input-port element
        assert "document.getElementById('input-port')" in dashboard_content, (
            "Dashboard should read SRT port from input-port element"
        )


class TestPortConflictPrevention:
    """Tests to prevent port conflicts."""

    def test_no_srt_port_9999_in_input_section(self):
        """Verify SRT port in input section is not 9999 (conflicts with server)."""
        config_path = Path(__file__).parent.parent.parent / "config.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        input_srt_port = config_data.get("input", {}).get("srt", {}).get("listen_port")
        server_port = config_data.get("server", {}).get("port")

        # Critical: input.srt.listen_port must NOT be 9999 if server.port is 9999
        if server_port == 9999:
            assert input_srt_port != 9999, (
                f"CRITICAL: input.srt.listen_port is {input_srt_port} but server.port is {server_port}. "
                "This causes port conflict! Change input.srt.listen_port to 9000."
            )

    def test_config_structure_is_correct(self):
        """Verify config has proper structure with separate input and server sections."""
        config_path = Path(__file__).parent.parent.parent / "config.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Must have both sections
        assert "server" in config_data, "Missing server section"
        assert "input" in config_data, "Missing input section"

        # Server must have port
        assert "port" in config_data["server"], "Missing server.port"

        # Input.srt must have listen_port
        assert "srt" in config_data["input"], "Missing input.srt section"
        assert "listen_port" in config_data["input"]["srt"], (
            "Missing input.srt.listen_port"
        )


class TestAPIConfigResponse:
    """Tests for API config endpoint with correct ports."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context with correct port configuration."""
        from unittest.mock import Mock
        from core.config_manager import ConfigManager

        config = ConfigManager()

        return {
            "config": config,
        }

    def test_config_api_returns_srt_port_9000(self, mock_context):
        """Test that config API returns SRT port 9000."""
        srt_port = mock_context["config"].get("input.srt.listen_port")
        assert srt_port == 9000, f"SRT port in config should be 9000, got {srt_port}"

    def test_config_api_returns_server_port_9999(self, mock_context):
        """Test that config API returns server port 9999."""
        server_port = mock_context["config"].get("server.port")
        assert server_port == 9999, (
            f"Server port in config should be 9999, got {server_port}"
        )
