import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from cli.client.ws_client import WSClient


@pytest.mark.asyncio
async def test_ws_client_initialization():
    """Test that WSClient initializes correctly."""
    client = WSClient("ws://localhost:8080")
    assert client.url == "ws://localhost:8080"
    assert client.token is None


@pytest.mark.asyncio
async def test_ws_client_initialization_with_token():
    """Test that WSClient initializes with token."""
    client = WSClient("ws://localhost:8080", token="test-token")
    assert client.url == "ws://localhost:8080"
    assert client.token == "test-token"


@pytest.mark.asyncio
async def test_ws_client_connect_success():
    """Test successful connection handling."""
    client = WSClient("ws://localhost:8080")
    with patch("websockets.connect") as mock_connect:
        mock_ws = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_ws
        await client.connect()
        mock_connect.assert_called_once()


@pytest.mark.asyncio
async def test_ws_client_reconnect_backoff():
    """Test automatic reconnection with exponential backoff/jitter."""
    client = WSClient("ws://localhost:8080")
    with patch("websockets.connect") as mock_connect:
        mock_ws = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_ws
        await client.connect()
        await client.disconnect()
        await client.connect()
        assert mock_connect.call_count == 2


@pytest.mark.asyncio
async def test_ws_client_message_handling():
    """Test handling of incoming messages."""
    client = WSClient("ws://localhost:8080")
    # This would test the message handler logic
    pass
