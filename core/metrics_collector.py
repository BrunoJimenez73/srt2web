"""
Metrics Collector - Expone métricas internas en formato Prometheus.

Provee métricas del pipeline para scraping por Prometheus y visualización en Grafana.
"""

from threading import Lock
from typing import Any

# Lazy import to avoid dependency if prometheus_client is not installed
_prometheus_available = False
try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest

    _prometheus_available = True
except ImportError:
    pass


class MetricsCollector:
    """
    Recolector de métricas para Prometheus.

    Las métricas se actualizan desde el pipeline via update_*() methods
    y se sirven via render() en formato text/plain.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._metrics: dict[str, Any] = {}
        self._last_update = 0.0

        if _prometheus_available:
            self._chunks_total = Counter("srt2web_chunks_processed_total", "Total chunks processed")
            self._chunks_failed = Counter("srt2web_chunks_failed_total", "Total chunks failed")
            self._processing_time = Histogram(
                "srt2web_processing_time_ms",
                "Processing time per chunk (ms)",
                buckets=[50, 100, 250, 500, 1000, 2000, 5000],
            )
            self._pipeline_state = Gauge(
                "srt2web_pipeline_state", "Pipeline state (0=idle,1=running,2=error)", ["state"]
            )
            self._cpu_gauge = Gauge("srt2web_cpu_percent", "CPU usage percentage")
            self._memory_gauge = Gauge("srt2web_memory_mb", "Memory usage in MB")
            self._gpu_gauge = Gauge("srt2web_gpu_utilization_percent", "GPU utilization percentage")
            self._uptime_gauge = Gauge("srt2web_uptime_seconds", "Pipeline uptime in seconds")
            self._ws_connections = Gauge("srt2web_websocket_connections", "Active WebSocket connections")

    @property
    def available(self) -> bool:
        return _prometheus_available

    def update_pipeline_state(self, state: str) -> None:
        with self._lock:
            self._metrics["pipeline_state"] = state
        if not _prometheus_available:
            return
        state_map = {"idle": 0, "starting": 1, "running": 1, "stopping": 0, "error": 2}
        val = state_map.get(state, 0)
        self._pipeline_state.labels(state=state).set(val)

    def update_chunks_processed(self, count: int = 1) -> None:
        with self._lock:
            self._metrics["chunks_processed"] = self._metrics.get("chunks_processed", 0) + count
        if not _prometheus_available:
            return
        self._chunks_total.inc(count)

    def update_chunks_failed(self, count: int = 1) -> None:
        with self._lock:
            self._metrics["chunks_failed"] = self._metrics.get("chunks_failed", 0) + count
        if not _prometheus_available:
            return
        self._chunks_failed.inc(count)

    def record_processing_time(self, ms: float) -> None:
        with self._lock:
            self._metrics["avg_processing_time_ms"] = ms
        if not _prometheus_available:
            return
        self._processing_time.observe(ms)

    def update_system_metrics(self, cpu: float, memory_mb: float, gpu: float = 0) -> None:
        with self._lock:
            self._metrics["cpu_percent"] = cpu
            self._metrics["memory_mb"] = memory_mb
        if not _prometheus_available:
            return
        self._cpu_gauge.set(cpu)
        self._memory_gauge.set(memory_mb)
        self._gpu_gauge.set(gpu)

    def update_uptime(self, seconds: float) -> None:
        with self._lock:
            self._metrics["uptime_seconds"] = seconds
        if not _prometheus_available:
            return
        self._uptime_gauge.set(seconds)

    def update_ws_connections(self, count: int) -> None:
        with self._lock:
            self._metrics["ws_connections"] = count
        if not _prometheus_available:
            return
        self._ws_connections.set(count)

    def render(self) -> str:
        """Render metrics in Prometheus format text/plain."""
        if _prometheus_available:
            result = generate_latest()
            return result.decode("utf-8") if isinstance(result, bytes) else str(result)

        # F135: fallback manual Prometheus format (no dependency required)
        lines: list[str] = []
        lines.append("# HELP srt2web_chunks_processed_total Total chunks processed")
        lines.append("# TYPE srt2web_chunks_processed_total counter")
        lines.append(f"srt2web_chunks_processed_total {self._metrics.get('chunks_processed', 0)}")
        lines.append("# HELP srt2web_chunks_failed_total Total chunks failed")
        lines.append("# TYPE srt2web_chunks_failed_total counter")
        lines.append(f"srt2web_chunks_failed_total {self._metrics.get('chunks_failed', 0)}")
        lines.append("# HELP srt2web_pipeline_state Pipeline state (0=idle,1=running,2=error)")
        lines.append("# TYPE srt2web_pipeline_state gauge")
        state = self._metrics.get("pipeline_state", "idle")
        state_map = {"idle": 0, "starting": 1, "running": 1, "stopping": 0, "error": 2}
        lines.append(f'srt2web_pipeline_state{{state="{state}"}} {state_map.get(state, 0)}')
        lines.append("# HELP srt2web_processing_time_ms Processing time per chunk (ms)")
        lines.append("# TYPE srt2web_processing_time_ms gauge")
        lines.append(f"srt2web_processing_time_ms {self._metrics.get('avg_processing_time_ms', 0)}")
        lines.append("# HELP srt2web_memory_mb Memory usage in MB")
        lines.append("# TYPE srt2web_memory_mb gauge")
        lines.append(f"srt2web_memory_mb {self._metrics.get('memory_mb', 0)}")
        lines.append("# HELP srt2web_cpu_percent CPU usage percentage")
        lines.append("# TYPE srt2web_cpu_percent gauge")
        lines.append(f"srt2web_cpu_percent {self._metrics.get('cpu_percent', 0)}")
        lines.append("# HELP srt2web_uptime_seconds Pipeline uptime in seconds")
        lines.append("# TYPE srt2web_uptime_seconds gauge")
        lines.append(f"srt2web_uptime_seconds {self._metrics.get('uptime_seconds', 0)}")
        lines.append("")
        return "\n".join(lines)


# Singleton global
metrics_collector = MetricsCollector()
