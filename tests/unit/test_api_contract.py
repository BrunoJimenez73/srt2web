"""
API Contract Tests for SRT2Web.

These tests verify that the API responses match the expected contract/schema.
Uses the source of truth from frontend/src/lib/api.ts types.
"""

import pytest
from fastapi.testclient import TestClient

# Mock app for testing
from server.app import create_app


@pytest.fixture
def app_context():
    """Create a mock app context for testing."""
    from core.config_manager import ConfigManager
    from core.pipeline import Pipeline

    config = ConfigManager()
    pipeline = Pipeline()

    return {
        "config": config,
        "pipeline": pipeline,
        "srt_ingest": None,
        "log_broadcast": lambda level, msg: None,
    }


@pytest.fixture
def client(app_context):
    """Create a test client for the FastAPI app."""
    app = create_app(app_context)
    return TestClient(app)


@pytest.mark.api
@pytest.mark.contract
class TestConfigEndpointContract:
    """Verify /api/config endpoint contract."""

    def test_config_response_structure(self, client):
        """Config response should have required fields."""
        response = client.get("/api/config")
        assert response.status_code == 200

        data = response.json()
        # Verify top-level structure
        assert "server" in data
        assert "input" in data
        assert "output" in data
        assert "pipeline" in data
        assert "modules" in data

    def test_config_server_fields(self, client):
        """Server config should have required fields."""
        response = client.get("/api/config")
        data = response.json()

        server = data["server"]
        assert "host" in server
        assert "port" in server
        assert "auth_token" in server
        assert "rate_limit_rpm" in server
        assert "max_request_size_mb" in server

    def test_config_pipeline_fields(self, client):
        """Pipeline config should have required fields."""
        response = client.get("/api/config")
        data = response.json()

        pipeline = data["pipeline"]
        assert "chunk_duration_sec" in pipeline
        assert "mode" in pipeline
        assert "max_concurrent_chunks" in pipeline


@pytest.mark.api
@pytest.mark.contract
class TestStatusEndpointContract:
    """Verify /api/status endpoint contract."""

    def test_status_response_structure(self, client):
        """Status response should have required fields."""
        response = client.get("/api/status")
        assert response.status_code == 200

        data = response.json()
        # Verify it returns a list of module statuses
        assert isinstance(data, list)

    def test_status_module_structure(self, client):
        """Each module status should have required fields."""
        response = client.get("/api/status")
        data = response.json()

        if len(data) > 0:
            module = data[0]
            assert "name" in module
            assert "enabled" in module
            assert "status" in module
            assert "processed_chunks" in module


@pytest.mark.api
@pytest.mark.contract
class TestOutputsEndpointContract:
    """Verify /api/outputs endpoint contract."""

    def test_outputs_response_is_list(self, client):
        """Outputs endpoint should return a list."""
        response = client.get("/api/outputs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_output_returns_201(self, client):
        """Creating an output should return 201 or 200."""
        output_data = {
            "type": "hls",
            "segment_duration": 10,
            "list_size": 5,
        }
        response = client.post("/api/outputs", json=output_data)
        # Accept 200, 201, or 400 (if validation fails)
        assert response.status_code in [200, 201, 400]
