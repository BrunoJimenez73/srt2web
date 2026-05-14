from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cli.client.http_client import LogEntry
from cli.client.ws_client import WSClient


@pytest.fixture
def ws_client():
    return WSClient(
        url="http://localhost:9999",
        token=None,
        on_log=MagicMock(),
        on_status=MagicMock(),
        on_health=MagicMock(),
        on_connection_change=MagicMock(),
    )


class TestWSClientInit:
    def test_default_values(self):
        client = WSClient(url="http://localhost:9999")
        assert client.url == "ws://localhost:9999/ws/logs"
        assert client.token is None
        assert client._max_reconnect == 5
        assert client._backoff_base == 1.0

    def test_token_auth(self):
        client = WSClient(url="http://localhost:9999", token="abc123")
        assert client.token == "abc123"

    def test_ws_url_conversion(self):
        cases = [
            ("http://localhost:9999", "ws://localhost:9999/ws/logs"),
            ("https://example.com:4443", "wss://example.com:4443/ws/logs"),
            ("http://192.168.1.1:8080", "ws://192.168.1.1:8080/ws/logs"),
            ("ws://localhost:9999", "ws://localhost:9999/ws/logs"),
        ]
        for http_url, expected_ws_url in cases:
            client = WSClient(url=http_url)
            assert client.url == expected_ws_url

    def test_not_connected_by_default(self, ws_client):
        assert not ws_client.connected
        assert ws_client._ws is None


class TestWSClientBackoff:
    def test_backoff_delay_first(self, ws_client):
        delay = ws_client._get_backoff_delay()
        assert 1.0 <= delay <= 1.5

    def test_backoff_delay_increases(self, ws_client):
        d1 = ws_client._get_backoff_delay()
        ws_client._reconnect_count = 2
        d2 = ws_client._get_backoff_delay()
        assert d2 >= d1
        assert 4.0 <= d2 <= 4.5

    def test_backoff_capped_at_max(self, ws_client):
        ws_client._reconnect_count = 10
        delay = ws_client._get_backoff_delay()
        assert 30.0 <= delay <= 30.5

    def test_backoff_jitter_randomness(self, ws_client):
        delays = set()
        for _ in range(20):
            ws_client._reconnect_count = 0
            delays.add(ws_client._get_backoff_delay())
        assert len(delays) > 1


class TestWSClientHandleMessage:
    def test_log_message(self, ws_client):
        data = {"type": "log", "level": "INFO", "message": "test log", "timestamp": 1000.0}
        ws_client._handle_message(data)
        ws_client.on_log.assert_called_once()
        entry = ws_client.on_log.call_args[0][0]
        assert isinstance(entry, LogEntry)
        assert entry.level == "INFO"
        assert entry.message == "test log"

    def test_status_message(self, ws_client):
        data = {"type": "status", "state": "running", "chunks_processed": 5}
        ws_client._handle_message(data)
        ws_client.on_status.assert_called_once()
        arg = ws_client.on_status.call_args[0][0]
        assert arg["state"] == "running"

    def test_status_message_passes_data_directly(self, ws_client):
        data = {"type": "status", "state": "error"}
        ws_client._handle_message(data)
        ws_client.on_status.assert_called_once_with(data)

    def test_output_health_message(self, ws_client):
        data = {"type": "output_health", "output": "hls", "health": "healthy"}
        ws_client._handle_message(data)
        ws_client.on_health.assert_called_once_with(data)

    def test_unknown_message_type_ignored(self, ws_client):
        data = {"type": "unknown_type"}
        ws_client._handle_message(data)
        ws_client.on_log.assert_not_called()
        ws_client.on_status.assert_not_called()
        ws_client.on_health.assert_not_called()

    def test_status_no_callback(self):
        client = WSClient(url="http://localhost:9999")
        client._handle_message({"type": "status", "state": "running"})

    def test_health_no_callback(self):
        client = WSClient(url="http://localhost:9999")
        client._handle_message({"type": "output_health"})


class TestWSClientConnection:
    @pytest.mark.asyncio
    async def test_disconnect_clean(self, ws_client):
        ws_client._running = True
        ws_client._ws = AsyncMock()
        ws_client._task = asyncio.create_task(asyncio.sleep(0))
        await ws_client.disconnect()
        assert not ws_client._running
        assert ws_client._manual_disconnect

    @pytest.mark.asyncio
    async def test_disconnect_no_ws(self, ws_client):
        ws_client._running = True
        ws_client._ws = None
        await ws_client.disconnect()
        assert ws_client._manual_disconnect

    @pytest.mark.asyncio
    async def test_disconnect_calls_on_connection_change(self, ws_client):
        ws_client._running = True
        ws_client._ws = None
        ws_client.on_connection_change = MagicMock()
        await ws_client.disconnect()
        ws_client.on_connection_change.assert_called_with(False)

    def test_connected_property_with_open_ws(self, ws_client):
        ws_client._ws = MagicMock()
        ws_client._ws.closed = False
        assert ws_client.connected

    def test_connected_property_with_closed_ws(self, ws_client):
        ws_client._ws = MagicMock()
        ws_client._ws.closed = True
        assert not ws_client.connected

    def test_connected_property_no_ws(self, ws_client):
        ws_client._ws = None
        assert not ws_client.connected

    @pytest.mark.asyncio
    async def test_connect_creates_task(self, ws_client):
        patcher = patch("websockets.connect", side_effect=ConnectionRefusedError)
        patcher.start()
        await ws_client.connect()
        assert ws_client._task is not None
        assert ws_client._running
        await asyncio.sleep(0.1)
        await ws_client.disconnect()
        patcher.stop()

    @pytest.mark.asyncio
    async def test_connect_ignores_connection_refused(self, ws_client):
        patcher = patch("websockets.connect", side_effect=ConnectionRefusedError)
        patcher.start()
        await ws_client.connect()
        assert ws_client._running
        assert ws_client._task is not None
        await asyncio.sleep(0.1)
        await ws_client.disconnect()
        patcher.stop()
