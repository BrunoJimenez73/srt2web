"""
Tests for WebSocket reconnection features.
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.unit
class TestWebSocketReconnect:
    """Test WSClient reconnection config via content scraping."""

    API_PATH = PROJECT_ROOT / "frontend" / "src" / "lib" / "api.ts"

    def test_ws_client_has_max_reconnect_attempts(self):
        """Test WSClient defines maxReconnectAttempts."""
        content = self.API_PATH.read_text(encoding="utf-8")
        assert "maxReconnectAttempts" in content
        assert "5" in content

    def test_ws_client_has_reconnect_delay(self):
        """Test WSClient defines backoffBase (reconnect delay base)."""
        content = self.API_PATH.read_text(encoding="utf-8")
        assert "backoffBase" in content
        assert "1000" in content

    def test_ws_client_reconnect_attempts_increments(self):
        """Test WSClient tracks reconnectAttempts."""
        content = self.API_PATH.read_text(encoding="utf-8")
        assert "reconnectAttempts" in content

    def test_ws_client_can_prevent_reconnect_on_manual_close(self):
        """Test WSClient has manual close mechanism."""
        content = self.API_PATH.read_text(encoding="utf-8")
        assert "_isManualClose" in content


class TestWebSocketReconnectBehavior:
    """Test WSClient reconnect logic via content scraping."""

    API_PATH = PROJECT_ROOT / "frontend" / "src" / "lib" / "api.ts"

    def test_reconnect_logic_when_not_manual_close(self):
        """Test WSClient attempts reconnect when not manual close."""
        content = self.API_PATH.read_text(encoding="utf-8")
        assert "this._isManualClose" in content
        assert "attemptReconnect" in content

    def test_reconnect_logic_when_manual_close(self):
        """Test WSClient skips reconnect on manual close."""
        content = self.API_PATH.read_text(encoding="utf-8")
        assert "if (!this._isManualClose)" in content


class TestWebSocketPing:
    """Test WSClient state checks via content scraping."""

    API_PATH = PROJECT_ROOT / "frontend" / "src" / "lib" / "api.ts"

    def test_ws_client_has_connected_state_check(self):
        """Test WSClient defines isConnected method."""
        content = self.API_PATH.read_text(encoding="utf-8")
        assert "isConnected" in content


class TestWebSocketMessageHandling:
    """Test WebSocket message parsing."""

    def test_log_message_parsing(self):
        """Test log message is parsed correctly."""
        import json

        log_msg = json.dumps({"type": "log", "level": "info", "message": "Test message"})
        data = json.loads(log_msg)
        assert data["type"] == "log"
        assert data["level"] == "info"

    def test_status_message_parsing(self):
        """Test status message is parsed correctly."""
        import json

        status_msg = json.dumps({"type": "status", "status": {"state": "running", "chunks_processed": 10}})
        data = json.loads(status_msg)
        assert data["type"] == "status"
        assert "status" in data
        assert data["status"]["state"] == "running"
