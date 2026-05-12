"""
REST API routes for SRT2Web.

Provides endpoints for pipeline control, configuration,
and module management.

This file has been refactored from a monolithic 1047-line file
into separate modules under server/routes/ and server/validators.py
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from server.routes import config, modules, outputs, pipeline

logger = logging.getLogger("srt2web.api")


def create_api_router() -> APIRouter:
    """Create and return the main API router with all sub-routers."""
    router = APIRouter(tags=["api"])

    # Include sub-routers from separated modules
    router.include_router(pipeline.router)
    router.include_router(config.router)
    router.include_router(modules.router)
    router.include_router(outputs.router)

    def _ctx(request: Request) -> dict:
        return request.app.state.ctx

    @router.get("/output-info")
    async def output_info(request: Request):
        """Get output sink information (legacy — use /outputs for multi-output)."""
        ctx = _ctx(request)
        pipeline = ctx["pipeline"]
        from server.routes.outputs import _get_composite

        composite = _get_composite(pipeline)
        if hasattr(composite, "get_all_output_statuses"):
            statuses = composite.get_all_output_statuses()
            if not statuses:
                raise HTTPException(404, "No outputs configured")
            return statuses[0]
        sink = pipeline.get_output_sink()
        if not sink:
            raise HTTPException(404, "No output sink configured")
        return sink.get_stream_info()

    # ── Network Information ──────────────────────────

    @router.get("/network/info")
    async def network_info(request: Request):
        """Get network information for external connections."""
        from core.network_utils import get_network_info

        ctx = _ctx(request)
        config = ctx["config"]

        srt_port = config.get("input.srt.listen_port", 9000)
        server_port = config.get("server.port", 9999)
        latency_ms = config.get("input.srt.latency_ms", 1000)
        srt_mode = config.get("input.srt.mode", "listener")
        caller_address = config.get("input.srt.caller_address", "")

        network = get_network_info(srt_port=srt_port, server_port=server_port, latency_ms=latency_ms)

        network["srt_mode"] = srt_mode
        network["caller_address"] = caller_address

        return network

    # ── Health Check ───────────────────────────────────

    @router.get("/health")
    async def health_check(request: Request):
        """
        Health check endpoint for monitoring and load balancers.

        Returns:
            - status: overall health status (healthy/degraded/unhealthy)
            - uptime_seconds: time since startup
            - memory_mb: current memory usage
            - modules: status of each module with circuit breaker state
            - pipeline: pipeline state and stats
        """
        from time import time as get_time

        import psutil

        ctx = _ctx(request)
        pipeline = ctx["pipeline"]

        start_time = ctx.get("_start_time", get_time())
        uptime = get_time() - start_time

        memory_info = {"memory_mb": 0, "memory_percent": 0}
        try:
            process = psutil.Process()
            memory_info = {
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
                "memory_percent": round(process.memory_percent(), 1),
            }
        except ImportError:
            pass

        modules_status = {}
        overall_healthy = True
        has_degraded = False

        for module in pipeline.get_modules():
            status = module.get_status()
            status_dict = status.to_dict()
            circuit_state = status_dict.pop("circuit_state", "closed")

            modules_status[module.name] = {
                "state": status_dict["state"],
                "circuit_state": circuit_state,
                "enabled": status_dict["enabled"],
                "processed_chunks": status_dict["processed_chunks"],
                "last_process_time_ms": status_dict["last_process_time_ms"],
                "error": status_dict["error_message"],
            }

            if status.state == "error":
                overall_healthy = False
            elif circuit_state in ("open", "half_open"):
                has_degraded = True

        if overall_healthy and has_degraded:
            health_status = "degraded"
        elif overall_healthy:
            health_status = "healthy"
        else:
            health_status = "unhealthy"

        input_health = {"receiving": False}
        input_src = pipeline.get_input_source()
        if input_src:
            input_health = {
                "receiving": input_src.is_receiving() if hasattr(input_src, "is_receiving") else False,
                "type": getattr(input_src, "name", "unknown"),
            }

        output_health = {"streaming": False}
        output_snk = pipeline.get_output_sink()
        if output_snk:
            output_health = {
                "streaming": output_snk.is_streaming() if hasattr(output_snk, "is_streaming") else False,
                "type": getattr(output_snk, "name", "unknown"),
            }

        return {
            "status": health_status,
            "uptime_seconds": round(uptime, 1),
            "memory_mb": memory_info["memory_mb"],
            "memory_percent": memory_info["memory_percent"],
            "chunks_processed": pipeline.chunks_processed,
            "pipeline_state": pipeline.state.value,
            "modules": modules_status,
            "input": input_health,
            "output": output_health,
        }

    # ── Available Types ────────────────────────────────

    @router.get("/available")
    async def get_available(request: Request):
        """Get available input and output types."""
        from core.io_factory import InputFactory, OutputFactory

        return {
            "inputs": InputFactory.available(),
            "outputs": OutputFactory.available(),
        }

    # Legacy endpoint - redirects to input-info
    @router.get("/srt-info")
    async def srt_info(request: Request):
        """Get SRT connection information (legacy - use /input-info)."""
        ctx = _ctx(request)
        input_source = ctx.get("input_source")
        if input_source:
            return input_source.get_connection_info()

        config = ctx["config"]
        host = config.get("server.host", "127.0.0.1")
        port = config.get("input.srt.listen_port", 9000)
        latency_ms = config.get("input.srt.latency_ms", 1000)
        return {
            "url": f"srt://{host}:{port}?mode=listener&latency={latency_ms}",
            "host": host,
            "port": port,
            "srt_port": port,
            "mode": config.get("input.srt.mode", "listener"),
            "latency_ms": latency_ms,
            "receiving": False,
        }

    return router
