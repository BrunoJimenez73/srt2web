import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from cli.client.ws_client import WSClient


@pytest.mark.asyncio
async def test_ws_client_initialization():
    """Test that WSClient initializes correctly."""
    client = WSClient("ws://localhost:8080")
    assert client.url == "ws://localhost:8080/ws/logs"
    assert client.token is None


@pytest.mark.asyncio
async def test_ws_client_initialization_with_token():
    """Test that WSClient initializes with token."""
    client = WSClient("ws://localhost:8080", token="test-token")
    assert client.url == "ws://localhost:8080/ws/logs"
    assert client.token == "test-token"


@pytest.mark.asyncio
async def test_http_url_normalized_to_ws():
    """HTTP URLs must be normalized to ws:// + /ws/logs suffix."""
    client = WSClient("http://localhost:9999")
    assert client.url == "ws://localhost:9999/ws/logs"


@pytest.mark.asyncio
async def test_ws_client_connect_success():
    """Test successful connection handling."""
    client = WSClient("ws://localhost:8080")
    with patch("cli.client.ws_client.websockets.connect") as mock_connect:
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.__aenter__.return_value = mock_ws
        mock_ws.__aiter__.return_value = iter([])
        mock_connect.return_value = mock_ws
        await client.connect()
        await asyncio.sleep(0.05)  # let the run task enter the connection
        mock_connect.assert_called_once()
        assert client.connected is True
        await client.disconnect()


@pytest.mark.asyncio
async def test_reconnect_backoff_delay_increases():
    """Exponential backoff delay must grow with reconnect count."""
    client = WSClient("ws://localhost:8080")
    client._reconnect_count = 0
    base = client._get_backoff_delay()
    client._reconnect_count = 1
    first = client._get_backoff_delay()
    client._reconnect_count = 3
    third = client._get_backoff_delay()
    client._reconnect_count = 10
    capped = client._get_backoff_delay()
    # base=1.0, max=30.0; jitter (0..0.5) keeps base*2^n growth monotonic
    assert base < first < third
    assert capped <= client._max_backoff + client._jitter
    assert client._max_backoff == 30.0


@pytest.mark.asyncio
async def test_ws_client_disconnect_cleans_up():
    """disconnect() must cancel the run task and mark manual disconnect."""
    client = WSClient("ws://localhost:8080")
    with patch("cli.client.ws_client.websockets.connect") as mock_connect:
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.__aenter__.return_value = mock_ws
        mock_ws.__aiter__.return_value = iter([])
        mock_connect.return_value = mock_ws
        await client.connect()
        assert client._task is not None
        await client.disconnect()
        assert client._task is None
        assert client._manual_disconnect is True


@pytest.mark.asyncio
async def test_ws_client_message_handling():
    """Incoming 'log' messages must be delivered to the on_log callback."""
    from cli.client.http_client import LogEntry

    received: list[LogEntry] = []
    client = WSClient("ws://localhost:8080", on_log=received.append)
    msg = {
        "type": "log",
        "level": "INFO",
        "message": "hello",
        "module": "core",
        "timestamp": "2026-08-11T10:00:00",
    }
    client._handle_message(msg)
    assert len(received) == 1
    assert received[0].message == "hello"


@pytest.mark.asyncio
async def test_ws_client_status_handling():
    """Incoming 'status' messages must be delivered to the on_status callback."""
    received: list[dict] = []
    client = WSClient("ws://localhost:8080", on_status=received.append)
    client._handle_message({"type": "status", "status": {"state": "running"}})
    assert received == [{"state": "running"}]
