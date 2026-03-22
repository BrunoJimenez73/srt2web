"""
WebSocket routes for SRT2Web.

Provides real-time log streaming and status updates to the frontend.
"""

import json
import asyncio
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from dataclasses import dataclass
from typing import Optional, Dict, Any

from server.security import validate_ws_auth


@dataclass
class WebSocketRequest:
    """Wrapper to make WebSocket compatible with validate_ws_auth."""
    headers: Dict[str, str]
    query_params: Dict[str, str]
    client: Optional[Any] = None
    
    @classmethod
    def from_websocket(cls, websocket: WebSocket) -> 'WebSocketRequest':
        """Create a WebSocketRequest from a WebSocket."""
        # Extract headers
        headers = dict(websocket.scope.get('headers', []))
        # Decode header values from bytes
        headers = {k.decode() if isinstance(k, bytes) else k: 
                   v.decode() if isinstance(v, bytes) else v 
                   for k, v in headers.items()}
        
        # Extract query params from query_string
        query_string = websocket.scope.get('query_string', b'').decode()
        query_params = {}
        if query_string:
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key] = value
        
        # Extract client info
        client = websocket.scope.get('client')
        client_obj = None
        if client:
            class ClientInfo:
                def __init__(self, host, port):
                    self.host = host
                    self.port = port
            client_obj = ClientInfo(client[0], client[1])
        
        return cls(
            headers=headers,
            query_params=query_params,
            client=client_obj
        )

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
    async def ws_logs(websocket: WebSocket):
        """WebSocket endpoint for real-time log streaming."""
        # Create wrapper for auth validation
        request = WebSocketRequest.from_websocket(websocket)
        
        # Validate authentication via query parameter ?token=xxx
        ctx = websocket.app.state.ctx
        config = ctx.get("config")
        get_token = lambda: config.get("server.auth_token", "") if config else ""

        if not validate_ws_auth(request, get_token):
            host = request.client.host if request.client else "unknown"
            logger.warning(f"SECURITY: WebSocket auth failed from {host}")
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
                        srt_ingest = ctx.get("srt_ingest")
                        status["input_receiving"] = srt_ingest.is_receiving() if srt_ingest else False
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
