"""
Tests for Async Pipeline implementation.
"""

import pytest
import time
import queue
from unittest.mock import MagicMock, patch


class TestAsyncPipeline:
    """Test suite for AsyncPipeline class."""

    def test_initialization(self):
        """Test AsyncPipeline initialization."""
        from core.async_pipeline import AsyncPipeline

        ap = AsyncPipeline(buffer_size=5, num_workers=2)

        assert ap.buffer_size == 5
        assert ap.num_workers == 2
        assert ap._running is False
        assert ap._chunk_queue.maxsize == 5

    def test_set_input_source(self):
        """Test setting input source."""
        from core.async_pipeline import AsyncPipeline

        ap = AsyncPipeline()
        mock_input = MagicMock()

        ap.set_input_source(mock_input)

        assert ap._input_source is mock_input

    def test_set_output_sink(self):
        """Test setting output sink."""
        from core.async_pipeline import AsyncPipeline

        ap = AsyncPipeline()
        mock_output = MagicMock()

        ap.set_output_sink(mock_output)

        assert ap._output_sink is mock_output

    def test_register_module(self):
        """Test registering modules."""
        from core.async_pipeline import AsyncPipeline
        from core.module_base import BaseModule, ModuleState, PipelineData

        class MockModule(BaseModule):
            def start(self):
                pass

            def stop(self):
                pass

            def _do_process(self, data):
                return data

        ap = AsyncPipeline()
        module = MockModule("test")

        ap.register_module(module)

        assert len(ap._modules) == 1
        assert ap._modules[0].name == "test"

    def test_start_pipeline(self):
        """Test starting the pipeline."""
        from core.async_pipeline import AsyncPipeline
        from core.module_base import BaseModule, ModuleState, PipelineData

        class MockModule(BaseModule):
            def start(self):
                self._state = ModuleState.RUNNING

            def stop(self):
                self._state = ModuleState.IDLE

            def _do_process(self, data):
                return data

        ap = AsyncPipeline()
        ap.register_module(MockModule("test"))

        mock_input = MagicMock()
        mock_output = MagicMock()
        ap.set_input_source(mock_input)
        ap.set_output_sink(mock_output)

        ap.start()

        assert ap._running is True
        mock_input.start.assert_called_once()

        ap.stop()

    def test_stop_pipeline(self):
        """Test stopping the pipeline."""
        from core.async_pipeline import AsyncPipeline
        from core.module_base import BaseModule, ModuleState, PipelineData

        class MockModule(BaseModule):
            def start(self):
                self._state = ModuleState.RUNNING

            def stop(self):
                self._state = ModuleState.IDLE

            def _do_process(self, data):
                return data

        ap = AsyncPipeline()
        module = MockModule("test")
        ap.register_module(module)

        mock_input = MagicMock()
        mock_output = MagicMock()
        ap.set_input_source(mock_input)
        ap.set_output_sink(mock_output)

        ap.start()
        time.sleep(0.1)
        ap.stop()

        assert ap._running is False

    def test_get_status(self):
        """Test getting pipeline status."""
        from core.async_pipeline import AsyncPipeline

        ap = AsyncPipeline(buffer_size=3, num_workers=2)

        status = ap.get_status()

        assert "running" in status
        assert "buffer_size" in status
        assert "chunks_queued" in status
        assert "chunks_processed" in status


class TestChunkProcessor:
    """Test suite for ChunkProcessor dataclass."""

    def test_chunk_processor_creation(self):
        """Test ChunkProcessor creation."""
        from core.async_pipeline import ChunkProcessor, ProcessingStage

        cp = ChunkProcessor(
            chunk_index=1,
            timestamp=time.time(),
        )

        assert cp.chunk_index == 1
        assert cp.stage == ProcessingStage.INPUT
        assert cp.data is None
        assert cp.is_complete is False

    def test_chunk_processor_is_complete(self):
        """Test ChunkProcessor is_complete property."""
        from core.async_pipeline import ChunkProcessor, ProcessingStage
        from core.module_base import PipelineData

        cp = ChunkProcessor(
            chunk_index=1,
            timestamp=time.time(),
            stage=ProcessingStage.OUTPUT,
            data=PipelineData(),
        )

        assert cp.is_complete is True


class TestProcessingStage:
    """Test suite for ProcessingStage enum."""

    def test_processing_stages_exist(self):
        """Test that all processing stages are defined."""
        from core.async_pipeline import ProcessingStage

        expected_stages = [
            "INPUT",
            "AUDIO_EXTRACT",
            "TRANSCRIBE",
            "TRANSLATE",
            "SUBS",
            "TTS",
            "MIX",
            "OUTPUT",
        ]

        for stage in expected_stages:
            assert hasattr(ProcessingStage, stage)


class TestOptimizedPipeline:
    """Test suite for OptimizedPipeline class."""

    def test_optimized_pipeline_inheritance(self):
        """Test that OptimizedPipeline inherits from AsyncPipeline."""
        from core.async_pipeline import OptimizedPipeline, AsyncPipeline

        assert issubclass(OptimizedPipeline, AsyncPipeline)

    def test_optimized_pipeline_initialization(self):
        """Test OptimizedPipeline initialization."""
        from core.async_pipeline import OptimizedPipeline

        op = OptimizedPipeline(buffer_size=3, num_workers=4)

        assert op.buffer_size == 3
        assert op.num_workers == 4


class TestAsyncPipelineEdgeCases:
    """Edge case tests for AsyncPipeline."""

    def test_start_without_input_source(self):
        """Test starting pipeline without input source."""
        from core.async_pipeline import AsyncPipeline
        from core.module_base import BaseModule, ModuleState, PipelineData

        class MockModule(BaseModule):
            def start(self):
                self._state = ModuleState.RUNNING

            def stop(self):
                self._state = ModuleState.IDLE

            def _do_process(self, data):
                return data

        ap = AsyncPipeline()
        ap.register_module(MockModule("test"))

        ap.start()
        time.sleep(0.1)

        assert ap._running is True

        ap.stop()

    def test_multiple_modules(self):
        """Test registering multiple modules."""
        from core.async_pipeline import AsyncPipeline
        from core.module_base import BaseModule, ModuleState, PipelineData

        class MockModule(BaseModule):
            def __init__(self, name):
                super().__init__(name)

            def start(self):
                self._state = ModuleState.RUNNING

            def stop(self):
                self._state = ModuleState.IDLE

            def _do_process(self, data):
                return data

        ap = AsyncPipeline()
        ap.register_module(MockModule("module1"))
        ap.register_module(MockModule("module2"))
        ap.register_module(MockModule("module3"))

        assert len(ap._modules) == 3

    def test_output_queue_full_handling(self):
        """Test handling when output queue is full."""
        from core.async_pipeline import AsyncPipeline, ChunkProcessor, ProcessingStage

        ap = AsyncPipeline(buffer_size=1, num_workers=1)
        ap._output_queue = queue.Queue(maxsize=1)

        cp = ChunkProcessor(
            chunk_index=1,
            timestamp=time.time(),
            stage=ProcessingStage.OUTPUT,
        )

        ap._output_queue.put(cp, timeout=0.1)

        with pytest.raises(queue.Full):
            ap._output_queue.put(cp, timeout=0.1)
