"""
Tests for Prometheus metrics endpoint and collector.
"""

from fastapi.testclient import TestClient

from core.metrics_collector import MetricsCollector


class TestMetricsCollector:
    def test_render_without_prometheus(self) -> None:
        """Render should output Prometheus format text even without prometheus_client."""
        collector = MetricsCollector()
        output = collector.render()
        assert "# HELP srt2web_chunks_processed_total" in output
        assert "# TYPE srt2web_chunks_processed_total counter" in output
        assert "srt2web_chunks_processed_total 0" in output
        assert "srt2web_memory_mb 0" in output

    def test_render_includes_state_after_update(self) -> None:
        """After updating state, render includes it."""
        collector = MetricsCollector()
        collector.update_pipeline_state("running")
        output = collector.render()
        assert 'srt2web_pipeline_state{state="running"} 1' in output

    def test_render_includes_chunks_after_update(self) -> None:
        """After updating chunks, render includes counts."""
        collector = MetricsCollector()
        collector.update_chunks_processed(10)
        collector.update_chunks_failed(2)
        output = collector.render()
        assert "srt2web_chunks_processed_total 10" in output
        assert "srt2web_chunks_failed_total 2" in output

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
