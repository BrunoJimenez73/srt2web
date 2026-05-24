"""
Metrics Collector - Expone métricas internas en formato Prometheus.

Provee métricas del pipeline para scraping por Prometheus y visualización en Grafana.
"""

from threading import Lock

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
        self._metrics: dict[str, float] = {}
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
        if not _prometheus_available:
            return
        state_map = {"idle": 0, "starting": 1, "running": 1, "stopping": 0, "error": 2}
        val = state_map.get(state, 0)
        self._pipeline_state.labels(state=state).set(val)

    def update_chunks_processed(self, count: int = 1) -> None:
        if not _prometheus_available:
            return
        self._chunks_total.inc(count)

    def update_chunks_failed(self, count: int = 1) -> None:
        if not _prometheus_available:
            return
        self._chunks_failed.inc(count)

    def record_processing_time(self, ms: float) -> None:
        if not _prometheus_available:
            return
        self._processing_time.observe(ms)

    def update_system_metrics(self, cpu: float, memory_mb: float, gpu: float = 0) -> None:
        if not _prometheus_available:
            return
        self._cpu_gauge.set(cpu)
        self._memory_gauge.set(memory_mb)
        self._gpu_gauge.set(gpu)

    def update_uptime(self, seconds: float) -> None:
        if not _prometheus_available:
            return
        self._uptime_gauge.set(seconds)

    def update_ws_connections(self, count: int) -> None:
        if not _prometheus_available:
            return
        self._ws_connections.set(count)

    def render(self) -> str:
        """Render metrics in Prometheus format."""
        if not _prometheus_available:
            return "# prometheus_client not installed\n"
        result = generate_latest()
        return result.decode("utf-8") if isinstance(result, bytes) else str(result)


# Singleton global
metrics_collector = MetricsCollector()
