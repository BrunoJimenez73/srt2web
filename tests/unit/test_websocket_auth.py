"""
WebSocket authentication tests for SRT2Web.
Tests WebSocket connection with and without auth token.
"""

from pathlib import Path

import pytest


@pytest.mark.websocket
@pytest.mark.security
class TestWebSocketAuth:
    """Tests for WebSocket authentication."""

    def _get_auth_validator(self):
        from server.security import validate_ws_auth

        return validate_ws_auth

    def test_websocket_auth_module_imports(self):
        """Test that WebSocket auth module can be imported."""
        fn = self._get_auth_validator()
        assert fn is not None

    def test_websocket_auth_accepts_no_token_when_not_required(self):
        """Test auth validation allows request when no token is configured."""
        from unittest.mock import Mock, patch

        validate_ws_auth = self._get_auth_validator()

        mock_request = Mock()
        mock_request.query_params = {}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"

        def get_auth_token() -> None:
            return None

        with patch.dict("os.environ", {}, clear=True):
            result = validate_ws_auth(mock_request, get_auth_token)
        assert result is True

    def test_websocket_auth_rejects_missing_token_param(self):
        """Test auth validation rejects request when token is required but not provided."""
        from unittest.mock import Mock

        validate_ws_auth = self._get_auth_validator()

        mock_request = Mock()
        mock_request.query_params = {}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"

        def get_auth_token() -> str:
            return "test-token-123"

        result = validate_ws_auth(mock_request, get_auth_token)
        assert result is False

    def test_websocket_auth_accepts_valid_token(self):
        """Test auth validation accepts request with valid token."""
        from unittest.mock import Mock

        validate_ws_auth = self._get_auth_validator()

        mock_request = Mock()
        mock_request.query_params.get = lambda k, d=None: "test-token-123" if k == "token" else d
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"

        def get_auth_token() -> str:
            return "test-token-123"

        result = validate_ws_auth(mock_request, get_auth_token)
        assert result is True


@pytest.mark.websocket
class TestWebSocketReconnect:
    """Tests for WebSocket reconnection logic in WSClient."""

    def test_ws_client_class_exists(self):
        """Test WSClient class is defined in api.ts."""
        api_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "lib" / "api.ts"
        assert api_path.exists()
        content = api_path.read_text(encoding="utf-8")
        assert "class WSClient" in content

    def test_ws_client_has_reconnect_properties(self):
        """Test WSClient has reconnect configuration properties."""
        api_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "lib" / "api.ts"
        content = api_path.read_text(encoding="utf-8")
        assert "maxReconnectAttempts" in content
        assert "backoffBase" in content
        assert "maxBackoff" in content
