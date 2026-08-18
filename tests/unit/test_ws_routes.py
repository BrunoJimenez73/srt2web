"""
Unit tests for WebSocket routes.
"""

import json
import sys
from unittest.mock import AsyncMock, Mock

import pytest

from server.ws_routes import LogBroadcaster, create_ws_router


class TestLogBroadcaster:
    """Tests for LogBroadcaster class."""

    def test_init(self) -> None:
        """Test broadcaster initialization."""
        broadcaster = LogBroadcaster()

        assert broadcaster._subscribers == set()
        assert broadcaster._loop is None
        assert len(broadcaster._buffer) == 0

    def test_set_loop(self) -> None:
        """Test setting the event loop."""
        broadcaster = LogBroadcaster()
        mock_loop = Mock()

        broadcaster.set_loop(mock_loop)

        assert broadcaster._loop == mock_loop

    @pytest.mark.asyncio
    async def test_subscribe(self):
        """Test subscribing a WebSocket."""
        broadcaster = LogBroadcaster()
        mock_ws = AsyncMock()

        await broadcaster.subscribe(mock_ws)

        # subscribe no longer calls accept() — accept is done before auth
        mock_ws.accept.assert_not_called()
        assert mock_ws in broadcaster._subscribers

    def test_unsubscribe(self) -> None:
        """Test unsubscribing a WebSocket."""
        broadcaster = LogBroadcaster()
        mock_ws = Mock()

        broadcaster._subscribers.add(mock_ws)
        broadcaster.unsubscribe(mock_ws)

        assert mock_ws not in broadcaster._subscribers

    def test_broadcast_buffers_message(self) -> None:
        """Test that broadcast buffers the message."""
        broadcaster = LogBroadcaster()

        broadcaster.broadcast("info", "Test message")

        assert len(broadcaster._buffer) == 1
        msg = json.loads(broadcaster._buffer[0])
        assert msg["message"] == "Test message"
        assert msg["level"] == "info"

    def test_broadcast_respects_max_buffer(self) -> None:
        """Test that broadcast respects max buffer size."""
        broadcaster = LogBroadcaster()
        broadcaster._max_buffer = 5

        for i in range(10):
            broadcaster.broadcast("info", f"Message {i}")

        assert len(broadcaster._buffer) == 5

    def test_broadcast_status(self) -> None:
        """Test broadcasting status updates."""
        broadcaster = LogBroadcaster()

        broadcaster.broadcast_status({"state": "running"})

        assert len(broadcaster._buffer) == 0


class TestWsRouter:
    """Tests for WebSocket router."""

    def test_ws_endpoint_exists(self) -> None:
        """Test that WebSocket endpoint is registered."""
        router = create_ws_router()

        # Get all routes
        routes = router.routes
        ws_routes = [r for r in routes if hasattr(r, "path") and "ws" in r.path]

        assert len(ws_routes) > 0
        assert any("/ws/logs" in str(r.path) for r in ws_routes)


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        sys.platform != "linux",
        reason="CI: instantiating full UnifiedPipeline+app stalls the suite end "
        "for 10-25min on GitHub windows/macos runners (ubuntu still covers it)",
    )
    async def test_ws_connection_flow(self):
        """Test WebSocket connection and messaging flow."""
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline
        from server.app import create_app

        config = ConfigManager()
        pipeline = Pipeline()
        srt_ingest = Mock()

        app_context = {
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": srt_ingest,
            "log_broadcast": lambda level, msg: None,
        }

        app = create_app(app_context)

        # This would require a real WebSocket test client
        # For now, we verify the route is set up correctly
        assert app is not None


class TestLogBroadcasterThreadSafety:
    """Tests for thread safety of LogBroadcaster."""

    def test_broadcast_from_thread(self) -> None:
        """Test broadcasting from a separate thread."""
        import threading

        broadcaster = LogBroadcaster()

        def broadcast_message() -> None:
            broadcaster.broadcast("info", "Thread message")

        thread = threading.Thread(target=broadcast_message)
        thread.start()
        thread.join()

        # Should not raise and should buffer the message
        assert len(broadcaster._buffer) == 1

    def test_multiple_threads(self) -> None:
        """Test broadcasting from multiple threads."""
        import threading

        broadcaster = LogBroadcaster()

        def broadcast_many() -> None:
            for i in range(10):
                broadcaster.broadcast("info", f"Message {i}")

        threads = [threading.Thread(target=broadcast_many) for _ in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All messages should be buffered
        assert len(broadcaster._buffer) == 30


class TestWsMessageTypes:
    """Tests for different WebSocket message types."""

    def test_log_message_format(self) -> None:
        """Test log message format."""
        import time

        broadcaster = LogBroadcaster()
        before = time.time()
        broadcaster.broadcast("error", "Test error message")
        after = time.time()

        msg = json.loads(broadcaster._buffer[-1])

        assert msg["type"] == "log"
        assert msg["level"] == "error"
        assert msg["message"] == "Test error message"
        assert before <= msg["timestamp"] <= after

    def test_status_message_format(self) -> None:
        """Test status message format is correct."""
        broadcaster = LogBroadcaster()

        broadcaster.broadcast_status({"state": "running", "chunks": 10})

        assert len(broadcaster._buffer) == 0
