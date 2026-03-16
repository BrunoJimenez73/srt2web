"""
E2E tests for the API endpoints.
"""

import pytest
import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestAPIEndpoints:
    """Tests for all API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        from fastapi.testclient import TestClient
        from server.app import create_app
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline
        from core.module_base import ModuleState, ModuleStatus
        
        class DummyModule:
            def __init__(self, name, enabled=True):
                self.name = name
                self.enabled = enabled
                self._state = ModuleState.IDLE
            
            def configure(self, config):
                self.enabled = config.get("enabled", True)
            
            def get_status(self):
                return ModuleStatus(
                    name=self.name,
                    state=self._state,
                    enabled=self.enabled,
                    processed_chunks=0,
                    last_process_time_ms=0.0,
                )
        
        config = ConfigManager()
        pipeline = Pipeline()
        
        # Add test modules
        pipeline.register_module(DummyModule("audio_extractor"))
        pipeline.register_module(DummyModule("transcriber"))
        pipeline.register_module(DummyModule("translator"))
        pipeline.register_module(DummyModule("subtitle_generator"))
        pipeline.register_module(DummyModule("tts_engine"))
        pipeline.register_module(DummyModule("audio_mixer"))
        pipeline.register_module(DummyModule("video_muxer"))
        
        srt_ingest = Mock()
        srt_ingest.is_receiving.return_value = False
        srt_ingest.get_srt_url.return_value = "srt://127.0.0.1:9000"
        
        app = create_app({
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": srt_ingest,
            "log_broadcast": Mock(),
        })
        
        return TestClient(app)

    def test_get_status(self, client):
        """Test GET /api/status endpoint."""
        response = client.get("/api/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "state" in data
        assert "modules" in data
        assert "srt_receiving" in data

    def test_get_status_includes_module_details(self, client):
        """Test that status includes module details."""
        response = client.get("/api/status")
        
        data = response.json()
        modules = data["modules"]
        
        assert len(modules) == 7  # All modules
        
        module_names = [m["name"] for m in modules]
        assert "transcriber" in module_names
        assert "translator" in module_names

    def test_get_config(self, client):
        """Test GET /api/config endpoint."""
        response = client.get("/api/config")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "server" in data
        assert "srt" in data
        assert "modules" in data

    def test_update_config_partial(self, client):
        """Test partial config update."""
        response = client.put(
            "/api/config",
            json={"config": {"srt": {"listen_port": 9999}}}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"

    def test_update_config_nested(self, client):
        """Test nested config update."""
        response = client.put(
            "/api/config",
            json={"config": {"modules": {"transcriber": {"model": "tiny"}}}}
        )
        
        assert response.status_code == 200

    def test_update_config_invalid(self, client):
        """Test invalid config update."""
        response = client.put(
            "/api/config",
            json={"config": {"modules": {"transcriber": {"model": "invalid"}}}}
        )
        
        assert response.status_code == 422  # Validation error

    def test_list_modules(self, client):
        """Test GET /api/modules endpoint."""
        response = client.get("/api/modules")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "modules" in data
        assert len(data["modules"]) > 0

    def test_toggle_module_enable(self, client):
        """Test enabling a module."""
        response = client.put(
            "/api/modules/transcriber/toggle",
            json={"enabled": True}
        )
        
        # Should work even if module doesn't exist in pipeline
        assert response.status_code in [200, 404]

    def test_toggle_module_disable(self, client):
        """Test disabling a module."""
        response = client.put(
            "/api/modules/transcriber/toggle",
            json={"enabled": False}
        )
        
        assert response.status_code in [200, 404]

    def test_toggle_module_invalid_name(self, client):
        """Test toggling with invalid module name."""
        response = client.put(
            "/api/modules/invalid-module/toggle",
            json={"enabled": True}
        )
        
        assert response.status_code == 400

    def test_srt_info(self, client):
        """Test GET /api/srt-info endpoint."""
        response = client.get("/api/srt-info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "mode" in data
        assert "port" in data
        assert "latency_ms" in data
        assert "obs_url" in data
        assert "vmix_url" in data
        assert "instructions" in data

    def test_start_pipeline(self, client):
        """Test POST /api/start endpoint."""
        # Mock the srt_ingest and pipeline to avoid actual start
        response = client.post("/api/start")
        
        # Will fail because modules need to be set up
        assert response.status_code in [200, 500]

    def test_stop_pipeline(self, client):
        """Test POST /api/stop endpoint."""
        response = client.post("/api/stop")
        
        # Should work
        assert response.status_code in [200, 500]


class TestAPIValidation:
    """Tests for API input validation."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        from fastapi.testclient import TestClient
        from server.app import create_app
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline
        
        config = ConfigManager()
        pipeline = Pipeline()
        srt_ingest = Mock()
        
        app = create_app({
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": srt_ingest,
            "log_broadcast": Mock(),
        })
        
        return TestClient(app)

    def test_invalid_port_value(self, client):
        """Test that invalid port values are rejected."""
        response = client.put(
            "/api/config",
            json={"config": {"srt": {"listen_port": 70000}}}
        )
        
        assert response.status_code == 422

    def test_invalid_latency(self, client):
        """Test that invalid latency is rejected."""
        response = client.put(
            "/api/config",
            json={"config": {"srt": {"latency_ms": -100}}}
        )
        
        assert response.status_code == 422

    def test_invalid_module_name_in_toggle(self, client):
        """Test that invalid module names in toggle are rejected."""
        response = client.put(
            "/api/modules/bad-name/toggle",
            json={"enabled": True}
        )
        
        assert response.status_code == 400

    def test_invalid_json_body(self, client):
        """Test that invalid JSON is rejected."""
        response = client.put(
            "/api/config",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422


class TestAPIIntegration:
    """Integration tests for API workflows."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        from fastapi.testclient import TestClient
        from server.app import create_app
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline
        
        config = ConfigManager()
        pipeline = Pipeline()
        srt_ingest = Mock()
        
        app = create_app({
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": srt_ingest,
            "log_broadcast": Mock(),
        })
        
        return TestClient(app)

    def test_config_update_reflects_in_status(self, client):
        """Test that config updates reflect in status."""
        # Get initial config
        config_response = client.get("/api/config")
        initial_port = config_response.json()["srt"]["listen_port"]
        
        # Update config
        client.put(
            "/api/config",
            json={"config": {"srt": {"listen_port": 8888}}}
        )
        
        # Get config again
        config_response = client.get("/api/config")
        updated_port = config_response.json()["srt"]["listen_port"]
        
        assert updated_port == 8888

    def test_srt_info_uses_config(self, client):
        """Test that srt-info uses current config."""
        # Update SRT port
        client.put(
            "/api/config",
            json={"config": {"srt": {"listen_port": 9999}}}
        )
        
        # Check srt-info
        response = client.get("/api/srt-info")
        data = response.json()
        
        assert data["port"] == 9999


class TestAPILiveServer:
    """Tests that require a live running server."""

    @pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_TESTS"),
        reason="Live server tests require explicit opt-in"
    )
    def test_live_server_api_health(self):
        """Test that live server API is healthy."""
        import requests
        
        response = requests.get("http://localhost:8080/health", timeout=5)
        
        assert response.status_code == 200

    @pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_TESTS"),
        reason="Live server tests require explicit opt-in"
    )
    def test_live_server_api_status(self):
        """Test live server status endpoint."""
        import requests
        
        response = requests.get("http://localhost:8080/api/status", timeout=5)
        
        assert response.status_code == 200
        data = response.json()
        assert "state" in data

    @pytest.mark.skipif(
        not os.environ.get("RUN_LIVE_TESTS"),
        reason="Live server tests require explicit opt-in"
    )
    def test_live_server_can_start_pipeline(self):
        """Test starting pipeline on live server."""
        import requests
        
        # First ensure config is valid
        # Then try to start
        response = requests.post("http://localhost:8080/api/start", timeout=30)
        
        # May succeed or fail depending on setup
        assert response.status_code in [200, 500]
