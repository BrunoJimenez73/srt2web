"""
Metrics endpoint for Prometheus scraping.
"""

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response

from core.metrics_collector import metrics_collector

logger = logging.getLogger("srt2web.api.metrics")

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def get_metrics(request: Request) -> Response:
    """Prometheus metrics endpoint."""
    # Update pipeline-related metrics from current state
    ctx: dict[str, Any] = request.app.state.ctx
    pipeline = ctx.get("pipeline")
    if pipeline and hasattr(pipeline, "get_status"):
        try:
            status = pipeline.get_status()
            state = status.get("state", "idle")
            metrics_collector.update_pipeline_state(state)

            chunks = status.get("chunks_processed", 0)
            metrics_collector.update_chunks_processed(0)  # reset not needed, counter tracks total

            failed = status.get("chunks_failed", 0)
            if failed:
                metrics_collector.update_chunks_failed(0)

            avg_time = status.get("avg_processing_time_ms", 0)
            if avg_time:
                metrics_collector.record_processing_time(avg_time)

            uptime = status.get("uptime_seconds", 0)
            metrics_collector.update_uptime(uptime)

            sys_metrics = status.get("system_metrics", {}) or status.get("system", {})
            cpu = sys_metrics.get("cpu_percent", 0) or sys_metrics.get("cpu_usage", 0)
            mem = sys_metrics.get("memory_mb", 0)
            gpu = sys_metrics.get("gpu_percent", 0) or sys_metrics.get("gpu_usage", 0)
            metrics_collector.update_system_metrics(float(cpu), float(mem), float(gpu))
        except Exception as e:
            logger.debug(f"Failed to update metrics: {e}")

    body = metrics_collector.render()
    return PlainTextResponse(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")
