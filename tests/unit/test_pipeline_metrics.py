"""Tests for core.pipeline_metrics."""

from core.pipeline_metrics import PipelineMetrics


class TestPipelineMetrics:
    def test_defaults(self) -> None:
        m = PipelineMetrics()
        assert m.chunks_processed == 0
        assert m.chunks_failed == 0
        assert m.total_processing_time == 0.0
        assert m.start_time is None

    def test_avg_processing_time_empty(self) -> None:
        m = PipelineMetrics()
        assert m.avg_processing_time == 0.0

    def test_avg_processing_time(self) -> None:
        m = PipelineMetrics(chunks_processed=10, total_processing_time=5.0)
        assert m.avg_processing_time == 0.5

    def test_uptime_no_start(self) -> None:
        m = PipelineMetrics()
        assert m.uptime == 0.0

    def test_to_dict(self) -> None:
        m = PipelineMetrics(chunks_processed=5, chunks_failed=1, total_processing_time=2.5)
        d = m.to_dict()
        assert d["chunks_processed"] == 5
        assert d["chunks_failed"] == 1
        assert d["total_processing_time"] == 2.5
        assert "avg_processing_time" in d
        assert "uptime" in d
