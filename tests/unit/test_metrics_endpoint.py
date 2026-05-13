"""
Tests for Prometheus metrics endpoint and collector.
"""

from fastapi.testclient import TestClient

from core.metrics_collector import MetricsCollector


class TestMetricsCollector:
    def test_render_without_prometheus(self) -> None:
        """Render should return fallback message when prometheus_client not installed."""
        collector = MetricsCollector()
        output = collector.render()
        assert "prometheus_client" in output or "# HELP" in output or "# TYPE" in output

    def test_update_pipeline_state(self) -> None:
        """Pipeline state update should not crash."""
        collector = MetricsCollector()
        collector.update_pipeline_state("running")
        collector.update_pipeline_state("error")
        collector.update_pipeline_state("idle")

    def test_chunk_counters(self) -> None:
        """Chunk counter updates should not crash."""
        collector = MetricsCollector()
        collector.update_chunks_processed(5)
        collector.update_chunks_failed(1)

    def test_system_metrics(self) -> None:
        """System metrics update should not crash."""
        collector = MetricsCollector()
        collector.update_system_metrics(45.0, 1024.0, 30.0)
        collector.update_uptime(3600.0)
        collector.update_ws_connections(3)


class TestMetricsEndpoint:
    def test_metrics_returns_text(self, mock_app_context) -> None:
        """GET /metrics returns plaintext."""
        from server.app import create_app

        app = create_app(mock_app_context)
        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
