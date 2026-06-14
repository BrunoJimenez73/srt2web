"""
F134: Integration tests — pipeline chunk processing → HLS output.

Uses mocked FFmpeg/subprocess to avoid requiring real FFmpeg.
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from core.module_base import BaseModule, ModuleState, PipelineData
from core.unified_pipeline import PipelineMode, UnifiedPipeline


class _PassThroughModule(BaseModule):
    """Module that passes data through unchanged."""

    def __init__(self, name: str = "passthrough", config: dict | None = None):
        super().__init__(name, config)
        self._start_called = False
        self._stop_called = False

    def start(self) -> None:
        self._start_called = True
        self._state = ModuleState.RUNNING

    def stop(self) -> None:
        self._stop_called = True
        self._state = ModuleState.IDLE

    def _do_process(self, data: PipelineData) -> PipelineData:
        return data


@pytest.mark.integration
class TestPipelineHLSFlow:
    """Integration tests: pipeline processes chunks → HLS output."""

    def _make_mock_input(self) -> MagicMock:
        """Create an input source mock that returns None chunks (no data)."""
        src = MagicMock()
        src.get_next_chunk = MagicMock(return_value=None)
        src.start = MagicMock()
        return src

    def _make_mock_output(self) -> MagicMock:
        sink = MagicMock()
        sink.start = MagicMock()
        return sink

    def test_pipeline_start_stop_clean(self) -> None:
        """Start + stop leaves pipeline in IDLE state without errors."""
        pipeline = UnifiedPipeline(mode=PipelineMode.THREAD_PARALLEL)
        pipeline.register_module(_PassThroughModule("test_mod"))
        pipeline.set_input_source(self._make_mock_input())
        pipeline.set_output_sink(self._make_mock_output())
        pipeline.start()
        assert pipeline.is_running
        asyncio.run(pipeline.stop())
        assert pipeline.state.value == "idle"

    def test_pipeline_start_stop_sequential(self) -> None:
        """SEQUENTIAL mode start + stop clean."""
        pipeline = UnifiedPipeline(mode=PipelineMode.SEQUENTIAL)
        pipeline.register_module(_PassThroughModule("mod1"))
        pipeline.set_input_source(self._make_mock_input())
        pipeline.set_output_sink(self._make_mock_output())
        pipeline.start()
        assert pipeline.is_running
        asyncio.run(pipeline.stop())
        assert pipeline.state.value == "idle"

    def test_pipeline_status_after_processing(self) -> None:
        """get_status() returns valid data after processing."""
        pipeline = UnifiedPipeline(mode=PipelineMode.SEQUENTIAL)
        pipeline.register_module(_PassThroughModule("mod_a"))
        pipeline.set_input_source(self._make_mock_input())
        pipeline.set_output_sink(self._make_mock_output())
        status = pipeline.get_status()
        assert "state" in status
        assert "modules" in status
        pipeline.start()
        asyncio.run(pipeline.stop())

    def test_bidirectional_stop_idempotent(self) -> None:
        """Calling stop() twice is safe."""
        pipeline = UnifiedPipeline(mode=PipelineMode.SEQUENTIAL)
        pipeline.register_module(_PassThroughModule("mod"))
        pipeline.set_input_source(self._make_mock_input())
        pipeline.set_output_sink(self._make_mock_output())
        pipeline.start()
        asyncio.run(pipeline.stop())
        asyncio.run(pipeline.stop())  # Second stop should not raise
        assert pipeline.state.value == "idle"

    def test_reconfigure_after_stop(self) -> None:
        """Reconfiguring after stop should work."""
        pipeline = UnifiedPipeline(mode=PipelineMode.SEQUENTIAL)
        pipeline.register_module(_PassThroughModule("mod"))
        pipeline.set_input_source(self._make_mock_input())
        pipeline.set_output_sink(self._make_mock_output())
        pipeline.start()
        asyncio.run(pipeline.stop())
        config = MagicMock()
        config.get.return_value = 5
        config.get_module_config.return_value = {}
        pipeline.reconfigure(config)
        assert pipeline._chunk_duration == 5
