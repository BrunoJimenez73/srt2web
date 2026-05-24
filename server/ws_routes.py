"""
WebSocket routes for SRT2Web.

Provides real-time log streaming and status updates to the frontend.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


@dataclass
class WebSocketRequest:
    """Wrapper to make WebSocket compatible with validate_ws_auth."""

    headers: dict[str, str]
    query_params: dict[str, str]
    client: Any | None = None

    @classmethod
    def from_websocket(cls, websocket: WebSocket) -> "WebSocketRequest":
        """Create a WebSocketRequest from a WebSocket."""
        # Extract headers
        headers = dict(websocket.scope.get("headers", []))
        # Decode header values from bytes
        headers = {
            k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v
            for k, v in headers.items()
        }

        # Extract query params from query_string
        query_string = websocket.scope.get("query_string", b"").decode()
        query_params = {}
        if query_string:
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    query_params[key] = value

        # Extract client info
        client = websocket.scope.get("client")
        client_obj = None
        if client:

            class ClientInfo:
                def __init__(self, host: str, port: int) -> None:
                    self.host = host
                    self.port = port

            client_obj = ClientInfo(client[0], client[1])

        return cls(headers=headers, query_params=query_params, client=client_obj)


logger = logging.getLogger("srt2web.ws")


class LogBroadcaster:
    """
    Manages WebSocket connections and broadcasts log messages.
    Thread-safe: can be called from the pipeline thread.
    """

    def __init__(self) -> None:
        self._subscribers: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._buffer: list[str] = []  # Buffer for messages before loop is set
        self._max_buffer = 200

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the asyncio event loop (call from main thread)."""
        self._loop = loop

    async def subscribe(self, ws: WebSocket) -> None:
        """Add a WebSocket subscriber."""
        await ws.accept()
        self._subscribers.add(ws)
        logger.info(f"WebSocket client connected. Total: {len(self._subscribers)}")

        # Send buffered messages
        for msg in self._buffer[-50:]:
            try:
                await ws.send_text(msg)
            except Exception as e:
                logger.debug("Failed to send buffered message to subscriber: %s", e)
                break

    def unsubscribe(self, ws: WebSocket) -> None:
        """Remove a WebSocket subscriber."""
        self._subscribers.discard(ws)
        logger.info(f"WebSocket client disconnected. Total: {len(self._subscribers)}")

    def broadcast(self, level: str, message: str) -> None:
        """
        Broadcast a log message to all subscribers.
        Can be called from any thread.
        """
        import time

        data = json.dumps(
            {
                "type": "log",
                "level": level,
                "message": message,
                "timestamp": time.time(),
            }
        )

        # Buffer the message
        self._buffer.append(data)
        if len(self._buffer) > self._max_buffer:
            self._buffer = self._buffer[-self._max_buffer :]

        # Debug: log to stderr in development only
        if os.environ.get("SRT2WEB_DEBUG") == "1":
            logger.debug(f"[WS-BROADCAST] {level}: {message[:80]}...")

        # Send to all subscribers
        if self._loop and self._subscribers:
            asyncio.run_coroutine_threadsafe(
                self._async_broadcast(data),
                self._loop,
            )

    async def _async_broadcast(self, data: str) -> None:
        """Send data to all subscribers, removing dead connections."""
        dead = set()
        for ws in self._subscribers:
            try:
                await ws.send_text(data)
            except Exception as e:
                logger.debug("Removing dead WebSocket subscriber: %s", e)
                dead.add(ws)
        self._subscribers -= dead

    def broadcast_status(self, status: dict[str, Any]) -> None:
        """Broadcast a status update to all subscribers."""
        data = json.dumps(
            {
                "type": "status",
                "status": status,
            }
        )

        if self._loop and self._subscribers:
            asyncio.run_coroutine_threadsafe(
                self._async_broadcast(data),
                self._loop,
            )

    def broadcast_output_health(self, output_name: str, health: str, extra: dict[str, Any] | None = None) -> None:
        """Broadcast an output health event to all subscribers."""
        data = json.dumps(
            {
                "type": "output_health",
                "output": output_name,
                "health": health,
                "extra": extra or {},
                "timestamp": time.time(),
            }
        )

        if self._loop and self._subscribers:
            asyncio.run_coroutine_threadsafe(
                self._async_broadcast(data),
                self._loop,
            )


# Global broadcaster instance
log_broadcaster = LogBroadcaster()

# Try to set the event loop immediately for the main thread
try:
    _main_loop = asyncio.get_event_loop()
    if _main_loop and not _main_loop.is_closed():
        log_broadcaster.set_loop(_main_loop)
except RuntimeError:
    # No event loop in current thread - will be set when first WebSocket connects
    pass


def create_ws_router() -> APIRouter:
    router = APIRouter(tags=["websocket"])

    @router.websocket("/ws/logs")
    async def ws_logs(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time log streaming."""
        ctx = websocket.app.state.ctx
        config = ctx.get("config")
        configured_token = config.get("server.auth_token", "") if config else ""

        # If auth token is configured, require token in first message
        auth_verified = False
        if not configured_token:
            # No auth configured - allow connection
            auth_verified = True

        # Set the event loop if not set
        try:
            if log_broadcaster._loop is None:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                log_broadcaster.set_loop(loop)
        except Exception as e:
            logger.debug("Suppressed error: %s", e, exc_info=True)

        await log_broadcaster.subscribe(websocket)

        try:
            while True:
                # Keep connection alive, also accept commands from client
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)

                    # Handle auth in first message if token is configured
                    if not auth_verified and configured_token:
                        if msg.get("type") == "auth":
                            client_token = msg.get("token", "")
                            if client_token == configured_token:
                                auth_verified = True
                                await websocket.send_text(json.dumps({"type": "auth_ok"}))
                            else:
                                await websocket.close(code=4001, reason="Invalid token")
                                return
                        else:
                            # Auth required but not provided
                            await websocket.close(
                                code=4001, reason="Authentication required. Send {type: 'auth', token: '...'}"
                            )
                            return
                        continue

                    # Handle client commands (e.g., request status)
                    if msg.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                    elif msg.get("type") == "get_status":
                        ctx = websocket.app.state.ctx
                        pipeline = ctx["pipeline"]
                        pipeline_status = pipeline.get_status()
                        srt_ingest = ctx.get("srt_ingest")
                        pipeline_status["input_receiving"] = srt_ingest.is_receiving() if srt_ingest else False
                        await websocket.send_text(json.dumps({"type": "status", "status": pipeline_status}))
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            log_broadcaster.unsubscribe(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            log_broadcaster.unsubscribe(websocket)

    return router
