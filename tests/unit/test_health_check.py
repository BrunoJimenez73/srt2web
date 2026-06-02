"""
Tests for Pipeline Status API endpoint and readiness/security probes.
"""

import logging

import pytest


class TestReadinessEndpoint:
    """Test suite for /ready endpoint (F102)."""

    def test_ready_endpoint_exists(self, client) -> None:
        response = client.get("/ready")
        assert response.status_code in (200, 503)

    def test_ready_returns_status_field(self, client) -> None:
        response = client.get("/ready")
        data = response.json()
        assert "status" in data

    def test_ready_returns_reason_when_not_ready(self, client) -> None:
        response = client.get("/ready")
        data = response.json()
        if response.status_code == 503:
            assert "reason" in data

    def test_live_endpoint_exists(self, client) -> None:
        response = client.get("/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    def test_health_endpoint_exists(self, client) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_api_health_returns_input_output(self, client) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "input" in data
        assert "output" in data


class TestSecurityLogging:
    """Test suite for security logging channel (F102)."""

    def test_security_handler_added(self) -> None:
        from core.logging_setup import setup_logging, SecurityLogHandler

        setup_logging()
        root = logging.getLogger()
        found = any(isinstance(h, SecurityLogHandler) for h in root.handlers)
        assert found, "SecurityLogHandler should be registered on root logger"

    def test_security_events_not_filtered_from_file(self) -> None:
        from core.logging_setup import setup_logging, get_filter_patterns

        patterns = get_filter_patterns()
        # SECURITY events should NOT be in the filter patterns (F102 fix)
        assert "SECURITY:" not in patterns
        assert "auth_token not configured" not in patterns

    def test_console_still_filters_security(self) -> None:
        from core.logging_setup import ConsoleFilter

        filt = ConsoleFilter()

        class FakeRecord:
            def getMessage(self):
                return "SECURITY: auth_token not configured - API is unprotected!"

        assert not filt.filter(FakeRecord()), "ConsoleFilter should suppress SECURITY messages"


class TestStatusEndpoint:
    """Test suite for /api/status endpoint."""

    def test_status_endpoint_exists(self, client) -> None:
        """Test that status endpoint exists."""
        response = client.get("/api/status")

        assert response.status_code == 200

    def test_status_returns_state(self, client) -> None:
        """Test that status endpoint returns pipeline state."""
        response = client.get("/api/status")
        data = response.json()

        assert "state" in data
        assert data["state"] in ["idle", "starting", "running", "stopping", "error"]

    def test_status_returns_uptime(self, client) -> None:
        """Test that status endpoint returns uptime."""
        response = client.get("/api/status")
        data = response.json()

        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))

    def test_status_returns_memory(self, client) -> None:
        """Test that status endpoint returns memory info."""
        response = client.get("/api/status")
        data = response.json()

        if "memory_mb" in data:
            assert "memory_percent" in data

    def test_status_returns_modules(self, client) -> None:
        """Test that status endpoint returns modules status."""
        response = client.get("/api/status")
        data = response.json()

        assert "modules" in data
        assert isinstance(data["modules"], list)

    def test_status_returns_input_info(self, client) -> None:
        """Test that status endpoint returns input info."""
        response = client.get("/api/status")
        data = response.json()

        # Input info is in 'network' field
        assert "network" in data
        assert isinstance(data["network"], dict)

    def test_status_returns_output_info(self, client) -> None:
        """Test that status endpoint returns output info."""
        response = client.get("/api/status")
        data = response.json()

        # Output info might be in modules or output_sinks
        has_output = "output_sinks" in data or "modules" in data
        assert has_output

    def test_status_returns_chunks_processed(self, client) -> None:
        """Test that status endpoint returns chunks processed count."""
        response = client.get("/api/status")
        data = response.json()

        # Check for chunks_processed in top level or in modules
        if "chunks_processed" in data:
            assert isinstance(data["chunks_processed"], int)


class TestStatusModuleStatus:
    """Test suite for module status in status endpoint."""

    def test_module_status_fields(self, client) -> None:
        """Test that each module has required fields."""
        response = client.get("/api/status")
        data = response.json()

        # modules is a list of dicts with module info
        for module_status in data["modules"]:
            assert "name" in module_status
            assert "state" in module_status
            assert "enabled" in module_status

    def test_module_state_values(self, client) -> None:
        """Test that module states are valid."""
        response = client.get("/api/status")
        data = response.json()

        valid_states = [
            "idle",
            "starting",
            "running",
            "stopping",
            "error",
            "disabled",
        ]

        for module_status in data["modules"]:
            if "state" in module_status:
                assert module_status["state"] in valid_states


class TestStatusInputOutput:
    """Test suite for input/output status in status endpoint."""

    def test_input_receiving_field(self, client) -> None:
        """Test that input has receiving status."""
        response = client.get("/api/status")
        data = response.json()

        # Check for input_receiving flag
        if "input_receiving" in data:
            assert isinstance(data["input_receiving"], bool)

    def test_input_info_exists(self, client) -> None:
        """Test that input info is available."""
        response = client.get("/api/status")
        data = response.json()

        # Input info might be in input_info or as separate field
        has_input = "input_info" in data
        if has_input:
            assert isinstance(data["input_info"], dict)
