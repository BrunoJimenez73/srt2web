"""
WebRTC Signaling Routes - Handles SDP offer/answer exchange.

Provides HTTP endpoints for WebRTC signaling between clients and the server.
"""

import json
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("srt2web.webrtc_signaling")


def create_webrtc_router() -> APIRouter:
    """Create WebRTC signaling router."""
    router = APIRouter()

    # F151: Store active signaling sessions with TTL-based cleanup
    _sessions: dict[str, Any] = {}
    _SESSION_MAX_AGE_SEC = 3600  # 1 hour TTL
    _SESSION_MAX_COUNT = 50

    def _cleanup_stale_sessions() -> None:
        """Remove sessions older than _SESSION_MAX_AGE_SEC."""
        now = time.time()
        stale = [sid for sid, s in _sessions.items() if now - s.get("created_at", now) > _SESSION_MAX_AGE_SEC]
        for sid in stale:
            del _sessions[sid]
            logger.info("Cleaned up stale WebRTC session: %s", sid)

    @router.post("/webrtc/offer")
    async def handle_webrtc_offer(request: Request) -> JSONResponse:
        """
        Handle WebRTC SDP offer from client.

        Expects JSON body with:
        - sdp: SDP offer string
        - type: SDP type (usually "offer")

        Returns JSON with:
        - sdp: SDP answer string
        - type: "answer"
        - client_id: Unique client identifier
        """
        try:
            body = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON") from exc

        sdp = body.get("sdp")
        sdp_type = body.get("type", "offer")

        if not sdp:
            raise HTTPException(status_code=400, detail="Missing SDP offer")

        # Get app context
        app_context = request.app.state.ctx
        pipeline = app_context.get("pipeline")

        if not pipeline:
            raise HTTPException(status_code=500, detail="Pipeline not available")

        # Get output sink
        output_sink = pipeline.output_sink

        if not output_sink:
            raise HTTPException(status_code=500, detail="Output sink not available")

        # Check if output sink supports WebRTC
        if not hasattr(output_sink, "_engines") or "webrtc" not in output_sink._engines:
            raise HTTPException(status_code=501, detail="WebRTC engine not available")

        webrtc_engine = output_sink._engines.get("webrtc")

        if not webrtc_engine or not webrtc_engine._running:
            raise HTTPException(status_code=503, detail="WebRTC engine not running")

        # Generate client ID
        client_id = str(uuid.uuid4())

        try:
            # Handle the offer through the WebRTC engine
            # This needs to be done in the engine's event loop
            import asyncio

            if webrtc_engine._loop and webrtc_engine._thread and webrtc_engine._thread.is_alive():
                future = asyncio.run_coroutine_threadsafe(
                    webrtc_engine.handle_offer(client_id, sdp, sdp_type), webrtc_engine._loop
                )
                answer_sdp = future.result(timeout=10.0)

                # Store session info with wall-clock timestamp
                _sessions[client_id] = {"created_at": time.time(), "output_sink": output_sink}
                # F151: Enforce max session count and clean up stale sessions
                if len(_sessions) > _SESSION_MAX_COUNT:
                    _cleanup_stale_sessions()
                if len(_sessions) > _SESSION_MAX_COUNT:
                    oldest = min(_sessions, key=lambda k: _sessions[k].get("created_at", 0))
                    del _sessions[oldest]
                    logger.info("Evicted oldest WebRTC session: %s", oldest)

                return JSONResponse(content={"sdp": answer_sdp, "type": "answer", "client_id": client_id})
            else:
                raise HTTPException(status_code=503, detail="WebRTC engine event loop not running")

        except TimeoutError as exc:
            logger.error(f"WebRTC offer handling timed out for client {client_id}")
            raise HTTPException(status_code=504, detail="WebRTC offer handling timed out") from exc
        except Exception as e:
            logger.error(f"Error handling WebRTC offer: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="Internal WebRTC error") from e

    @router.post("/webrtc/close")
    async def handle_webrtc_close(request: Request) -> JSONResponse:
        """
        Handle WebRTC connection close notification.

        Expects JSON body with:
        - client_id: Client identifier to close
        """
        try:
            body = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON") from exc

        client_id = body.get("client_id")

        if not client_id:
            raise HTTPException(status_code=400, detail="Missing client_id")

        # Clean up session
        if client_id in _sessions:
            del _sessions[client_id]
            logger.info(f"WebRTC session closed for client {client_id}")

        return JSONResponse(content={"status": "ok"})

    @router.get("/webrtc/sessions")
    async def get_webrtc_sessions() -> JSONResponse:
        """Get active WebRTC sessions (for debugging)."""
        return JSONResponse(content={"active_sessions": len(_sessions), "session_ids": list(_sessions.keys())})

    return router
