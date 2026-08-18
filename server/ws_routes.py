"""
WebSocket routes for SRT2Web.

Provides real-time log streaming, status updates, and player feedback loop.
"""

import asyncio
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.ctx import get_auth_token


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
        """Add a WebSocket subscriber and send buffered messages.
        The WebSocket must already be accepted via ws.accept()."""
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
        for ws in list(self._subscribers):
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

# F171 — Player feedback monitor (lazy-initialized by app)
feedback_monitor: Any | None = None

# Event loop is set lazily on the first WebSocket connection via the
# ``ws_logs`` handler.  Avoid ``asyncio.get_event_loop()`` at module level
# (deprecated since Python 3.12, emits ``DeprecationWarning``).


def create_ws_router() -> APIRouter:
    router = APIRouter(tags=["websocket"])

    @router.websocket("/ws/logs")
    async def ws_logs(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time log streaming."""
        ctx = websocket.app.state.ctx
        config = ctx.get("config")
        configured_token = get_auth_token(config)
        auth_required = bool(configured_token)
        if os.environ.get("SRT2WEB_TESTING"):
            auth_required = False

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

        # Accept the WebSocket only after validating auth via query param
        # F161: Reject unauthenticated connections before accepting
        if auth_required:
            token_param = websocket.query_params.get("token", "")
            if not token_param or not hmac.compare_digest(token_param, configured_token):
                await websocket.close(code=4001, reason="Authentication required")
                return

        await websocket.accept()
        await log_broadcaster.subscribe(websocket)

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)

                    # Handle client commands
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

    @router.websocket("/ws/player-feedback")
    async def ws_player_feedback(websocket: WebSocket) -> None:
        """F171 — WebSocket endpoint for player buffer health & rebuffering feedback."""
        ctx = websocket.app.state.ctx
        config = ctx.get("config")
        configured_token = get_auth_token(config)
        auth_required = bool(configured_token)
        if os.environ.get("SRT2WEB_TESTING"):
            auth_required = False

        if auth_required:
            token_param = websocket.query_params.get("token", "")
            if not token_param or not hmac.compare_digest(token_param, configured_token):
                await websocket.close(code=4001, reason="Authentication required")
                return

        await websocket.accept()
        logger.info("Player feedback WS connected")

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    msg_type = msg.get("type", "")

                    if msg_type == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                        continue

                    if msg_type == "feedback":
                        fb_data = msg.get("data", {})
                        _handle_player_feedback(fb_data, ctx)

                    elif msg_type == "stalled":
                        dur = msg.get("data", {}).get("duration_ms", 0)
                        _handle_player_stall(dur, ctx)

                    elif msg_type == "bandwidth":
                        bps = msg.get("data", {}).get("bps", 0)
                        _handle_player_bandwidth(bps, ctx)

                    elif msg_type == "buffered":
                        level = msg.get("data", {}).get("level_ms", 0)
                        _handle_player_buffered(level, ctx)

                except json.JSONDecodeError:
                    pass

        except WebSocketDisconnect:
            logger.info("Player feedback WS disconnected")
        except Exception as e:
            logger.error(f"Player feedback WS error: {e}")

    def _handle_player_feedback(fb_data: dict[str, Any], ctx: dict[str, Any]) -> None:
        """Route player feedback to the monitor."""
        global feedback_monitor
        if feedback_monitor is None:
            _init_feedback_monitor(ctx)
        if feedback_monitor is None:
            return
        buff = fb_data.get("buffer_ms", 0)
        target = fb_data.get("target_buffer_ms", 12000)
        if buff > 0:
            feedback_monitor.record_buffer(buff, target)

    def _handle_player_stall(duration_ms: float, ctx: dict[str, Any]) -> None:
        global feedback_monitor
        if feedback_monitor is None:
            _init_feedback_monitor(ctx)
        if feedback_monitor is None:
            return
        feedback_monitor.record_stall(duration_ms)

    def _handle_player_bandwidth(bps: float, ctx: dict[str, Any]) -> None:
        global feedback_monitor
        if feedback_monitor is None:
            _init_feedback_monitor(ctx)
        if feedback_monitor is None:
            return
        feedback_monitor.record_bandwidth(bps)

    def _handle_player_buffered(level_ms: float, ctx: dict[str, Any]) -> None:
        global feedback_monitor
        if feedback_monitor is None:
            _init_feedback_monitor(ctx)
        if feedback_monitor is None:
            return
        feedback_monitor.record_buffered(level_ms)

    def _init_feedback_monitor(ctx: dict[str, Any]) -> None:
        """Lazy-init the PlayerFeedbackMonitor with pipeline adaptation callbacks."""
        global feedback_monitor
        if feedback_monitor is not None:
            return
        try:
            from core.player_feedback import PlayerFeedbackMonitor

            pipeline = ctx.get("pipeline")

            def on_adapt(reason: str, params: dict[str, Any]) -> None:
                if pipeline is None:
                    return
                chunk_factor = params.get("chunk_duration_factor", 0.5)
                current_dur = pipeline._chunk_duration if hasattr(pipeline, "_chunk_duration") else 10
                new_dur = max(2, int(current_dur * chunk_factor))
                if hasattr(pipeline, "_on_chunk_duration_change"):
                    pipeline._on_chunk_duration_change(float(new_dur))
                if "max_concurrent" in params and hasattr(pipeline, "_adaptive_config"):
                    if pipeline._adaptive_config is None:
                        pipeline._adaptive_config = {}
                    pipeline._adaptive_config["max_concurrent"] = params["max_concurrent"]
                logger.info(
                    f"Player feedback on_adapt: {reason} "
                    f"chunk={current_dur}->{new_dur}s "
                    f"concurrency={params.get('max_concurrent', 'unchanged')}"
                )

            def on_restore() -> None:
                if pipeline is None:
                    return
                restore_duration = getattr(pipeline, "_default_chunk_duration", 10.0)
                if hasattr(pipeline, "_on_chunk_duration_change"):
                    pipeline._on_chunk_duration_change(float(restore_duration))
                if hasattr(pipeline, "_adaptive_config") and pipeline._adaptive_config:
                    pipeline._adaptive_config["max_concurrent"] = 4
                logger.info("Player feedback on_restore: restored defaults")

            feedback_monitor = PlayerFeedbackMonitor(on_adapt=on_adapt, on_restore=on_restore)
            logger.info("PlayerFeedbackMonitor initialized")
        except Exception as e:
            logger.error(f"Failed to init PlayerFeedbackMonitor: {e}")
            feedback_monitor = None

    return router
