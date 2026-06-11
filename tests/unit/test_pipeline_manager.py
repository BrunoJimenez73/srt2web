"""Tests for PipelineManager."""

import asyncio
import threading
import uuid

import pytest

from core.pipeline_manager import PipelineManager
from core.schemas import PipelineMode


class TestPipelineManager:
    """Tests for PipelineManager."""

    def test_create_pipeline(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({}, "/tmp/output")
        assert pid is not None
        assert isinstance(pid, str)
        assert uuid.UUID(pid) is not None

    def test_create_pipeline_increments_count(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        pid1 = mgr.create_pipeline({}, "/tmp/output1")
        pid2 = mgr.create_pipeline({}, "/tmp/output2")
        assert mgr.get_pipeline_count() == 2
        assert mgr.list_pipelines() == [pid1, pid2]

    def test_get_pipeline_returns_pipeline(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({}, "/tmp/output")
        pipeline = mgr.get_pipeline(pid)
        assert pipeline is not None

    def test_get_pipeline_nonexistent(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        assert mgr.get_pipeline("nonexistent") is None

    def test_get_pipeline_count(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        assert mgr.get_pipeline_count() == 0
        mgr.create_pipeline({}, "/tmp/output")
        assert mgr.get_pipeline_count() == 1

    def test_list_pipelines_empty(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        assert mgr.list_pipelines() == []

    def test_list_pipelines_after_create(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({}, "/tmp/output")
        assert mgr.list_pipelines() == [pid]

    def test_stop_pipeline_returns_true_for_existing(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({}, "/tmp/output")
        result = asyncio.run(mgr.stop_pipeline(pid))
        assert result is True

    def test_stop_pipeline_removes_from_list(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({}, "/tmp/output")
        asyncio.run(mgr.stop_pipeline(pid))
        assert mgr.get_pipeline_count() == 0
        assert mgr.get_pipeline(pid) is None

    def test_stop_pipeline_returns_false_for_nonexistent(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        result = asyncio.run(mgr.stop_pipeline("nonexistent"))
        assert result is False

    def test_start_pipeline_returns_true(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({}, "/tmp/output")
        result = mgr.start_pipeline(pid, None, None)
        assert result is True

    def test_start_pipeline_returns_false_for_nonexistent(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        result = mgr.start_pipeline("nonexistent", None, None)
        assert result is False

    def test_max_pipelines_limit(self) -> None:
        mgr = PipelineManager(max_pipelines=2)
        mgr.create_pipeline({}, "/tmp/output1")
        mgr.create_pipeline({}, "/tmp/output2")
        with pytest.raises(RuntimeError, match="Pipeline limit reached"):
            mgr.create_pipeline({}, "/tmp/output3")

    def test_create_pipeline_with_custom_mode(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({}, "/tmp/output", mode=PipelineMode.SEQUENTIAL)
        pipeline = mgr.get_pipeline(pid)
        assert pipeline is not None
        assert pipeline.mode == PipelineMode.SEQUENTIAL

    def test_create_pipeline_with_custom_concurrent(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({}, "/tmp/output", max_concurrent_chunks=5)
        pipeline = mgr.get_pipeline(pid)
        assert pipeline is not None
        assert pipeline._semaphore is not None

    def test_stop_pipeline_cleans_resources(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({}, "/tmp/output")
        asyncio.run(mgr.stop_pipeline(pid))
        assert mgr.list_pipelines() == []

    def test_multiple_stop_same_pipeline(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({}, "/tmp/output")
        assert asyncio.run(mgr.stop_pipeline(pid)) is True
        assert asyncio.run(mgr.stop_pipeline(pid)) is False

    def test_thread_safety_concurrent_creates(self) -> None:
        mgr = PipelineManager(max_pipelines=50)
        errors: list[Exception] = []

        def create() -> None:
            try:
                mgr.create_pipeline({}, "/tmp/output")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert mgr.get_pipeline_count() == 20

    def test_thread_safety_concurrent_stop(self) -> None:
        mgr = PipelineManager(max_pipelines=50)
        pids = [mgr.create_pipeline({}, "/tmp/output") for _ in range(10)]

        def stop_all() -> None:
            for pid in pids:
                asyncio.run(mgr.stop_pipeline(pid))

        threads = [threading.Thread(target=stop_all) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert mgr.get_pipeline_count() == 0

    def test_merge_config_empty(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        merged = mgr._merge_config({})
        assert "pipeline" in merged
        assert merged["pipeline"]["chunk_duration_sec"] == 10
        assert "input" in merged
        assert "output" in merged
        assert "modules" in merged

    def test_merge_config_custom_overrides_default(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        merged = mgr._merge_config({"pipeline": {"chunk_duration_sec": 30}})
        assert merged["pipeline"]["chunk_duration_sec"] == 30

    def test_merge_config_new_keys(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        merged = mgr._merge_config({"custom_key": "custom_value"})
        assert merged["custom_key"] == "custom_value"

    def test_start_pipeline_nonexistent_returns_false(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        assert mgr.start_pipeline("invalid", None, None) is False

    def test_create_pipeline_with_config_merge(self) -> None:
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({"pipeline": {"buffer_size": 10}}, "/tmp/output")
        pipeline = mgr.get_pipeline(pid)
        assert pipeline is not None

    # ── F128: deep merge preserves sub-keys not specified in custom ──

    def test_merge_preserves_other_pipeline_keys(self) -> None:
        """Custom overrides one pipeline field, others survive."""
        mgr = PipelineManager(max_pipelines=10)
        merged = mgr._merge_config({"pipeline": {"retry_delay": 2.0}})
        assert merged["pipeline"]["retry_delay"] == 2.0
        assert merged["pipeline"]["chunk_duration_sec"] == 10
        assert merged["pipeline"]["buffer_size"] == 5
        assert merged["pipeline"]["retry_attempts"] == 2

    def test_merge_preserves_output_subkeys(self) -> None:
        """Custom overrides output.web.segment_duration, list_size survives."""
        mgr = PipelineManager(max_pipelines=10)
        merged = mgr._merge_config({"output": {"web": {"segment_duration": 5}}})
        assert merged["output"]["web"]["segment_duration"] == 5
        assert merged["output"]["web"]["list_size"] == 2
        assert merged["output"]["type"] == "web"

    def test_merge_preserves_module_subkeys(self) -> None:
        """Custom overrides one module key, other modules survive."""
        mgr = PipelineManager(max_pipelines=10)
        merged = mgr._merge_config({"modules": {"transcriber": {"beam_size": 4}}})
        assert merged["modules"]["transcriber"]["beam_size"] == 4
        assert merged["modules"]["audio_mixer"]["original_volume"] == 0.15
        assert merged["modules"]["tts_engine"]["device"] == "cpu"

    def test_merge_adds_new_section(self) -> None:
        """Custom adds a section not in defaults."""
        mgr = PipelineManager(max_pipelines=10)
        merged = mgr._merge_config({"custom_section": {"key": "val"}})
        assert merged["custom_section"]["key"] == "val"
        # Existing sections unchanged
        assert merged["pipeline"]["chunk_duration_sec"] == 10

    def test_deep_merge_static(self) -> None:
        """_deep_merge static method works independently."""
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        override = {"b": {"c": 99}}
        result = PipelineManager._deep_merge(base, override)
        assert result == {"a": 1, "b": {"c": 99, "d": 3}}
        # Original unchanged
        assert base["b"]["c"] == 2

    # ── F129: lost_chunk_timeout_sec en defaults y creación ──

    def test_merge_default_has_lost_chunk_timeout(self) -> None:
        """Default merge includes lost_chunk_timeout_sec."""
        mgr = PipelineManager(max_pipelines=10)
        merged = mgr._merge_config({})
        assert merged["pipeline"]["lost_chunk_timeout_sec"] == 30.0

    def test_merge_custom_lost_chunk_timeout(self) -> None:
        """Custom lost_chunk_timeout_sec overrides default."""
        mgr = PipelineManager(max_pipelines=10)
        merged = mgr._merge_config({"pipeline": {"lost_chunk_timeout_sec": 60.0}})
        assert merged["pipeline"]["lost_chunk_timeout_sec"] == 60.0
        assert merged["pipeline"]["chunk_duration_sec"] == 10

    def test_create_pipeline_passes_lost_chunk_timeout(self) -> None:
        """Pipeline is created with lost_chunk_timeout from config."""
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({"pipeline": {"lost_chunk_timeout_sec": 45.0}}, "/tmp/output")
        pipeline = mgr.get_pipeline(pid)
        assert pipeline is not None
        assert pipeline.lost_chunk_timeout == 45.0

    def test_create_pipeline_default_timeout(self) -> None:
        """Pipeline created without config uses default 30s."""
        mgr = PipelineManager(max_pipelines=10)
        pid = mgr.create_pipeline({}, "/tmp/output")
        pipeline = mgr.get_pipeline(pid)
        assert pipeline is not None
        assert pipeline.lost_chunk_timeout == 30.0
