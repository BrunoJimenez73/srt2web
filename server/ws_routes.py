"""
WebSocket routes for SRT2Web.

Provides real-time log streaming and status updates to the frontend.
"""

import json
import asyncio
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request

from server.security import validate_ws_auth

logger = logging.getLogger("srt2web.ws")


class LogBroadcaster:
    """
    Manages WebSocket connections and broadcasts log messages.
    Thread-safe: can be called from the pipeline thread.
    """

    def __init__(self):
        self._subscribers: Set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop = None
        self._buffer: list = []  # Buffer for messages before loop is set
        self._max_buffer = 200

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the asyncio event loop (call from main thread)."""
        self._loop = loop

    async def subscribe(self, ws: WebSocket):
        """Add a WebSocket subscriber."""
        await ws.accept()
        self._subscribers.add(ws)
        logger.info(f"WebSocket client connected. Total: {len(self._subscribers)}")

        # Send buffered messages
        for msg in self._buffer[-50:]:
            try:
                await ws.send_text(msg)
            except Exception:
                break

    def unsubscribe(self, ws: WebSocket):
        """Remove a WebSocket subscriber."""
        self._subscribers.discard(ws)
        logger.info(f"WebSocket client disconnected. Total: {len(self._subscribers)}")

    def broadcast(self, level: str, message: str):
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

        # Send to all subscribers
        if self._loop and self._subscribers:
            asyncio.run_coroutine_threadsafe(
                self._async_broadcast(data),
                self._loop,
            )

    async def _async_broadcast(self, data: str):
        """Send data to all subscribers, removing dead connections."""
        dead = set()
        for ws in self._subscribers:
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        self._subscribers -= dead

    def broadcast_status(self, status: dict):
        """Broadcast a status update to all subscribers."""
        data = json.dumps(
            {
                "type": "status",
                **status,
            }
        )

        if self._loop and self._subscribers:
            asyncio.run_coroutine_threadsafe(
                self._async_broadcast(data),
                self._loop,
            )


# Global broadcaster instance
log_broadcaster = LogBroadcaster()


def create_ws_router() -> APIRouter:
    router = APIRouter(tags=["websocket"])

    @router.websocket("/ws/logs")
    async def ws_logs(websocket: WebSocket, request: Request):
        """WebSocket endpoint for real-time log streaming."""
        # Validate authentication via query parameter ?token=xxx
        ctx = websocket.app.state.ctx
        config = ctx.get("config")
        get_token = lambda: config.get("server.auth_token", "") if config else ""

        if not validate_ws_auth(request, get_token):
            logger.warning(f"SECURITY: WebSocket auth failed from {request.client.host}")
            await websocket.close(code=4001, reason="Authentication required. Use ?token=<auth_token>")
            return

        # Set the event loop if not set
        try:
            if log_broadcaster._loop is None:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                log_broadcaster.set_loop(loop)
        except Exception:
            pass

        await log_broadcaster.subscribe(websocket)

        try:
            while True:
                # Keep connection alive, also accept commands from client
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    # Handle client commands (e.g., request status)
                    if msg.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                    elif msg.get("type") == "get_status":
                        ctx = websocket.app.state.ctx
                        pipeline = ctx["pipeline"]
                        status = pipeline.get_status()
                        status["input_receiving"] = ctx["srt_ingest"].is_receiving()
                        await websocket.send_text(
                            json.dumps({"type": "status", **status})
                        )
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            log_broadcaster.unsubscribe(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            log_broadcaster.unsubscribe(websocket)

    return router
