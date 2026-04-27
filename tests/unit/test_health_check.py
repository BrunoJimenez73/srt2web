"""
Tests for Health Check API endpoint.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestHealthEndpoint:
    """Test suite for /api/health endpoint."""

    def test_health_endpoint_exists(self, client) -> None:
        """Test that health endpoint exists."""
        response = client.get("/api/health")

        assert response.status_code == 200

    def test_health_returns_status(self, client) -> None:
        """Test that health endpoint returns status."""
        response = client.get("/api/health")
        data = response.json()

        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_returns_uptime(self, client) -> None:
        """Test that health endpoint returns uptime."""
        response = client.get("/api/health")
        data = response.json()

        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))

    def test_health_returns_memory(self, client) -> None:
        """Test that health endpoint returns memory info."""
        response = client.get("/api/health")
        data = response.json()

        assert "memory_mb" in data
        assert "memory_percent" in data

    def test_health_returns_pipeline_state(self, client) -> None:
        """Test that health endpoint returns pipeline state."""
        response = client.get("/api/health")
        data = response.json()

        assert "pipeline_state" in data

    def test_health_returns_modules(self, client) -> None:
        """Test that health endpoint returns modules status."""
        response = client.get("/api/health")
        data = response.json()

        assert "modules" in data
        assert isinstance(data["modules"], dict)

    def test_health_returns_input_info(self, client) -> None:
        """Test that health endpoint returns input info."""
        response = client.get("/api/health")
        data = response.json()

        assert "input" in data

    def test_health_returns_output_info(self, client) -> None:
        """Test that health endpoint returns output info."""
        response = client.get("/api/health")
        data = response.json()

        assert "output" in data

    def test_health_returns_chunks_processed(self, client) -> None:
        """Test that health endpoint returns chunks processed count."""
        response = client.get("/api/health")
        data = response.json()

        assert "chunks_processed" in data
        assert isinstance(data["chunks_processed"], int)


class TestHealthModuleStatus:
    """Test suite for module status in health check."""

    def test_module_status_fields(self, client) -> None:
        """Test that each module has required fields."""
        response = client.get("/api/health")
        data = response.json()

        for module_name, status in data["modules"].items():
            assert "state" in status
            assert "circuit_state" in status
            assert "enabled" in status
            assert "processed_chunks" in status
            assert "last_process_time_ms" in status

    def test_module_circuit_state(self, client) -> None:
        """Test that module circuit states are reported."""
        response = client.get("/api/health")
        data = response.json()

        for module_name, status in data["modules"].items():
            assert status["circuit_state"] in ["closed", "open", "half_open"]

    def test_module_state_values(self, client) -> None:
        """Test that module states are valid."""
        response = client.get("/api/health")
        data = response.json()

        valid_states = [
            "idle",
            "starting",
            "running",
            "stopping",
            "error",
            "disabled",
            "degraded",
        ]

        for module_name, status in data["modules"].items():
            assert status["state"] in valid_states


class TestHealthDegradedStatus:
    """Test suite for degraded health status."""

    def test_healthy_when_all_modules_running(self, client) -> None:
        """Test that status is healthy when all modules are running."""
        response = client.get("/api/health")
        data = response.json()

        if data["status"] == "healthy":
            for module_name, status in data["modules"].items():
                if status["enabled"]:
                    assert status["state"] != "error"
                    assert status["circuit_state"] in ["closed", "half_open"]

    def test_degraded_when_circuit_open(self, client) -> None:
        """Test that status is degraded when circuit is open."""
        response = client.get("/api/health")
        data = response.json()

        has_open_circuit = any(
            m["circuit_state"] == "open" for m in data["modules"].values()
        )

        if has_open_circuit:
            assert data["status"] in ["degraded", "unhealthy"]

    def test_unhealthy_when_module_has_error(self, client) -> None:
        """Test that status is unhealthy when module has error."""
        response = client.get("/api/health")
        data = response.json()

        has_error = any(m["state"] == "error" for m in data["modules"].values())

        if has_error:
            assert data["status"] == "unhealthy"


class TestHealthInputOutput:
    """Test suite for input/output status in health check."""

    def test_input_receiving_field(self, client) -> None:
        """Test that input has receiving status."""
        response = client.get("/api/health")
        data = response.json()

        assert "receiving" in data["input"]

    def test_output_streaming_field(self, client) -> None:
        """Test that output has streaming status."""
        response = client.get("/api/health")
        data = response.json()

        assert "streaming" in data["output"]

    def test_input_type_field(self, client) -> None:
        """Test that input has type."""
        response = client.get("/api/health")
        data = response.json()

        if data["input"].get("type"):
            assert isinstance(data["input"]["type"], str)

    def test_output_type_field(self, client) -> None:
        """Test that output has type."""
        response = client.get("/api/health")
        data = response.json()

        if data["output"].get("type"):
            assert isinstance(data["output"]["type"], str)
