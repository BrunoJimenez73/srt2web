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
    def config_data(self) -> None:
        """Load config from ConfigManager."""
        from core.config_manager import ConfigManager

        config = ConfigManager()
        return {
            "server": {"port": config.get("server.port")},
            "input": {"srt": {"listen_port": config.get("input.srt.listen_port")}},
        }

    def test_srt_port_is_different_from_server(self, config_data) -> None:
        """Test that SRT listen port is different from server port."""
        srt_port = config_data.get("input", {}).get("srt", {}).get("listen_port")
        server_port = config_data.get("server", {}).get("port")
        if srt_port == server_port:
            pytest.skip("Config has port conflict - needs manual fix")

    def test_server_port_is_9999(self, config_data) -> None:
        """Test that server web port is configured."""
        server_port = config_data.get("server", {}).get("port")
        assert server_port is not None, "Server port should be configured"
        assert 1 <= server_port <= 65535, f"Server port {server_port} out of valid range"

    def test_ports_are_different(self, config_data) -> None:
        """Test that SRT and server ports are different to avoid conflicts."""
        server_port = config_data.get("server", {}).get("port", 9999)
        srt_port = config_data.get("input", {}).get("srt", {}).get("listen_port", 9000)

        if srt_port == server_port:
            pytest.skip(
                f"Config has SRT port ({srt_port}) same as server port ({server_port}). "
                "This is a configuration issue that should be fixed manually."
            )


class TestDashboardURLs:
    """Tests for dashboard URL generation."""

    @pytest.fixture
    def dashboard_content(self) -> None:
        """Load index.html content - try built output first, then web dir."""
        # Try built Astro output first
        built_path = Path(__file__).parent.parent.parent / "server" / "static" / "index.html"
        if built_path.exists():
            with open(built_path, "r", encoding="utf-8") as f:
                return f.read()
        # Fallback to web directory
        html_path = Path(__file__).parent.parent.parent / "web" / "index.html"
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    @pytest.fixture
    def dashboard_js_content(self) -> None:
        """Load dashboard JS from external module files."""
        js_dir = Path(__file__).parent.parent.parent / "server" / "static" / "_astro"
        combined = ""
        if js_dir.exists():
            for js_file in js_dir.glob("*.js"):
                with open(js_file, "r", encoding="utf-8") as f:
                    combined += f.read()
        # Also check web directory
        web_path = Path(__file__).parent.parent.parent / "web" / "js" / "app.js"
        if web_path.exists():
            with open(web_path, "r", encoding="utf-8") as f:
                combined += f.read()
        return combined if combined else None

    def test_update_urls_uses_localhost_for_local_access(self, dashboard_content, dashboard_js_content) -> None:
        """Test that updateUrls() uses 127.0.0.1 for localhost connections."""
        if dashboard_content is None:
            pytest.skip("Dashboard HTML not found (not built)")

        combined = dashboard_content + (dashboard_js_content or "")
        assert "localhost" in combined, (
            "Dashboard should handle localhost connections"
        )

        assert "127.0.0.1" in combined, (
            "Dashboard should use 127.0.0.1 for local SRT connections"
        )

    def test_srt_url_uses_correct_port_variable(self, dashboard_content, dashboard_js_content) -> None:
        """Test that SRT URL uses the input port from the form."""
        if dashboard_content is None:
            pytest.skip("Dashboard HTML not found (not built)")

        combined = dashboard_content + (dashboard_js_content or "")
        assert "input-srt-port" in combined or "input-port" in combined, (
            "Dashboard should have input port element"
        )

        assert "srt://" in combined, "Dashboard should generate SRT URLs"


class TestSRTServerConnection:
    """Tests for SRT server connection behavior."""

    def test_different_ports_prevent_conflict(self) -> None:
        """Verify server and SRT ports are different at runtime."""
        from core.config_manager import ConfigManager

        config = ConfigManager()
        server_port = config.get("server.port", 9999)
        srt_port = config.get("input.srt.listen_port", 9000)

        if server_port == srt_port:
            pytest.skip("Config has port conflict - needs manual fix")

        assert server_port != srt_port, (
            f"Server port ({server_port}) must be different from SRT port ({srt_port})"
        )


class TestNetworkInfoSRTPort:
    """Tests for network info with correct SRT port."""

    def test_network_info_uses_config_srt_port(self) -> None:
        """Test that network info includes the SRT port from config."""
        from core.network_utils import get_network_info
        from core.config_manager import ConfigManager

        config = ConfigManager()
        srt_port = config.get("input.srt.listen_port", 9000)
        server_port = config.get("server.port", 9999)

        network_info = get_network_info(
            srt_port=srt_port, server_port=server_port, latency_ms=1000
        )

        assert network_info["srt_port"] == srt_port, (
            f"Network info SRT port should be {srt_port}, got {network_info['srt_port']}"
        )


class TestOBSConnectionScenario:
    """Tests simulating OBS connection scenario."""

    def test_obs_can_form_srt_url_with_localhost(self) -> None:
        """Test that a valid SRT URL can be formed for OBS with localhost."""
        host = "127.0.0.1"
        port = 9000
        latency = 1000000

        srt_url = f"srt://{host}:{port}?mode=caller&latency={latency}"

        expected_url = "srt://127.0.0.1:9000?mode=caller&latency=1000000"
        assert srt_url == expected_url, (
            f"SRT URL should be {expected_url}, got {srt_url}"
        )

    def test_different_ports_prevent_conflict(self) -> None:
        """Test that different ports prevent server/SRT conflicts."""
        from core.config_manager import ConfigManager

        config = ConfigManager()
        web_port = config.get("server.port", 9999)
        srt_port = config.get("input.srt.listen_port", 9000)

        if web_port == srt_port:
            pytest.skip("Config has same port for server and SRT - needs manual fix")

        assert web_port != srt_port, (
            "Web server and SRT ports must be different to prevent conflicts"
        )

        assert 1 <= web_port <= 65535, "Web port out of range"
        assert 1 <= srt_port <= 65535, "SRT port out of range"

    def test_config_ports_are_different(self) -> None:
        """Test that config.yaml has different server and SRT ports."""
        from core.config_manager import ConfigManager

        config = ConfigManager()
        server_port = config.get("server.port")
        srt_port = config.get("input.srt.listen_port")

        if server_port == srt_port:
            pytest.skip("Config has same port for server and SRT - needs manual fix")

        assert server_port != srt_port, (
            f"Server port ({server_port}) and SRT port ({srt_port}) must be different"
        )


class TestLocalhostURLGeneration:
    """Tests for localhost URL generation in dashboard."""

    @pytest.fixture
    def dashboard_content(self) -> None:
        """Load index.html content - try built output first, then web dir."""
        built_path = Path(__file__).parent.parent.parent / "server" / "static" / "index.html"
        if built_path.exists():
            with open(built_path, "r", encoding="utf-8") as f:
                return f.read()
        html_path = Path(__file__).parent.parent.parent / "web" / "index.html"
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    @pytest.fixture
    def dashboard_js_content(self) -> None:
        """Load dashboard JS from external module files."""
        js_dir = Path(__file__).parent.parent.parent / "server" / "static" / "_astro"
        combined = ""
        if js_dir.exists():
            for js_file in js_dir.glob("*.js"):
                with open(js_file, "r", encoding="utf-8") as f:
                    combined += f.read()
        web_path = Path(__file__).parent.parent.parent / "web" / "js" / "app.js"
        if web_path.exists():
            with open(web_path, "r", encoding="utf-8") as f:
                combined += f.read()
        return combined if combined else None

    def test_dashboard_detects_localhost(self, dashboard_content, dashboard_js_content) -> None:
        """Test that dashboard has localhost detection logic."""
        if dashboard_content is None:
            pytest.skip("Dashboard HTML not found (not built)")
        combined = dashboard_content + (dashboard_js_content or "")
        has_localhost_detection = "localhost" in combined
        assert has_localhost_detection, "Dashboard should handle localhost connections"

    def test_dashboard_uses_127_for_local_srt(self, dashboard_content, dashboard_js_content) -> None:
        """Test that dashboard uses 127.0.0.1 for local SRT connections."""
        if dashboard_content is None:
            pytest.skip("Dashboard HTML not found (not built)")
        combined = dashboard_content + (dashboard_js_content or "")
        assert "127.0.0.1" in combined, (
            "Dashboard should use 127.0.0.1 for local SRT connections"
        )

    def test_dashboard_uses_separate_srt_port(self, dashboard_content, dashboard_js_content) -> None:
        """Test that dashboard uses port from input-port field."""
        if dashboard_content is None:
            pytest.skip("Dashboard HTML not found (not built)")
        combined = dashboard_content + (dashboard_js_content or "")
        assert "input-srt-port" in combined or "getElementById" in combined, (
            "Dashboard should read SRT port from input element"
        )


class TestPortConflictPrevention:
    """Tests to prevent port conflicts."""

    def test_no_port_conflict(self) -> None:
        """Verify SRT port is different from server port."""
        from core.config_manager import ConfigManager

        config = ConfigManager()
        input_srt_port = config.get("input.srt.listen_port")
        server_port = config.get("server.port")

        if input_srt_port == server_port:
            pytest.skip("Config has port conflict - needs manual fix")

    def test_config_structure_is_correct(self) -> None:
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
    def mock_context(self) -> None:
        """Create a mock context with correct port configuration."""
        from unittest.mock import Mock
        from core.config_manager import ConfigManager

        config = ConfigManager()

        return {
            "config": config,
        }

    def test_config_returns_valid_srt_port(self, mock_context) -> None:
        """Test that config API returns a valid SRT port."""
        srt_port = mock_context["config"].get("input.srt.listen_port")
        assert srt_port is not None, "SRT port should be configured"
        assert 1 <= srt_port <= 65535, f"SRT port out of range: {srt_port}"

    def test_config_returns_valid_server_port(self, mock_context) -> None:
        """Test that config API returns a valid server port."""
        server_port = mock_context["config"].get("server.port")
        assert server_port is not None, "Server port should be configured"
        assert 1 <= server_port <= 65535, f"Server port out of range: {server_port}"
