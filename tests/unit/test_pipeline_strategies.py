"""
Tests for pipeline strategies (core/pipeline/strategies.py).
"""

import pytest
from unittest.mock import MagicMock, patch
import threading
import queue

from core.pipeline.strategies import (
    SequentialStrategy,
    ThreadParallelStrategy,
    AsyncIOStrategy,
    PipelineStrategy,
    StrategyConfig,
    PipelineContext,
    ChunkProcessor,
)
from core.module_base import PipelineData


@pytest.fixture
def sample_data():
    return PipelineData(video_chunk_path="/tmp/test.ts", duration=10.0)


class TestStrategyConfig:
    def test_default_values(self):
        config = StrategyConfig()
        assert config.max_concurrent_chunks == 2
        assert config.chunk_timeout_sec == 60.0
        assert config.enable_metrics is True

    def test_custom_values(self):
        config = StrategyConfig(max_concurrent_chunks=4, chunk_timeout_sec=30.0, enable_metrics=False)
        assert config.max_concurrent_chunks == 4
        assert config.chunk_timeout_sec == 30.0
        assert config.enable_metrics is False


class TestChunkProcessor:
    def test_default_fields(self):
        cp = ChunkProcessor(chunk_index=0, timestamp=100.0)
        assert cp.chunk_index == 0
        assert cp.timestamp == 100.0
        assert cp.data is None
        assert cp.stages_completed == {}
        assert cp.error is None
        assert cp.task is None

    def test_with_data(self):
        data = PipelineData(video_chunk_path="/tmp/t.ts")
        cp = ChunkProcessor(chunk_index=1, timestamp=200.0, data=data)
        assert cp.data is data
        assert cp.stages_completed == {}


class TestPipelineStrategy:
    def test_abstract_class(self):
        with pytest.raises(TypeError):
            PipelineStrategy()

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            PipelineStrategy(StrategyConfig())


class TestSequentialStrategy:
    def test_initialization(self):
        config = StrategyConfig(max_concurrent_chunks=1)
        strategy = SequentialStrategy(config)
        assert strategy._config.max_concurrent_chunks == 1
        assert not strategy.is_running

    def test_start_stop(self):
        strategy = SequentialStrategy()
        strategy.start()
        assert strategy.is_running
        strategy.stop()
        assert not strategy.is_running

    def test_process_chunk(self, sample_data):
        strategy = SequentialStrategy()
        mock_module = MagicMock()
        mock_module.enabled = True
        mock_module.process.return_value = sample_data
        strategy._modules = [mock_module]

        result = strategy.process_chunk(sample_data)
        assert result is sample_data
        assert strategy._chunks_processed == 1

    def test_get_metrics(self):
        strategy = SequentialStrategy(StrategyConfig(max_concurrent_chunks=2))
        strategy._chunks_processed = 5
        strategy._chunks_failed = 1
        strategy._total_time = 10.0
        metrics = strategy.get_metrics()
        assert metrics["strategy"] == "sequential"
        assert metrics["chunks_processed"] == 5
        assert metrics["chunks_failed"] == 1
        assert metrics["active_chunks"] == 0

    def test_default_config(self):
        strategy = SequentialStrategy()
        assert strategy._config.max_concurrent_chunks == 2


class TestThreadParallelStrategy:
    def test_initialization(self):
        config = StrategyConfig(max_concurrent_chunks=3)
        strategy = ThreadParallelStrategy(config)
        assert strategy._config.max_concurrent_chunks == 3
        assert not strategy.is_running

    def test_start_stop(self):
        strategy = ThreadParallelStrategy()
        strategy.start()
        assert strategy.is_running
        strategy.stop()
        assert not strategy.is_running

    def test_process_chunk(self, sample_data):
        strategy = ThreadParallelStrategy(StrategyConfig(max_concurrent_chunks=3))
        mock_module = MagicMock()
        mock_module.enabled = True
        mock_module.process.return_value = sample_data
        strategy._modules = [mock_module]

        result = strategy.process_chunk(sample_data)
        assert result is sample_data
        assert strategy._chunks_processed == 1

    def test_get_metrics(self):
        strategy = ThreadParallelStrategy(StrategyConfig(max_concurrent_chunks=3))
        strategy._chunks_processed = 10
        strategy._chunks_failed = 2
        metrics = strategy.get_metrics()
        assert metrics["chunks_processed"] == 10
        assert metrics["chunks_failed"] == 2

    def test_default_config(self):
        strategy = ThreadParallelStrategy()
        assert strategy._config.max_concurrent_chunks == 2


class TestAsyncIOStrategy:
    def test_initialization(self):
        config = StrategyConfig(max_concurrent_chunks=4)
        strategy = AsyncIOStrategy(config)
        assert strategy._config.max_concurrent_chunks == 4
        assert not strategy.is_running

    def test_start_stop(self):
        strategy = AsyncIOStrategy()
        strategy.start()
        assert strategy.is_running
        strategy.stop()
        assert not strategy.is_running

    def test_get_metrics(self):
        strategy = AsyncIOStrategy(StrategyConfig(max_concurrent_chunks=4))
        strategy._chunks_processed = 7
        strategy._active_chunks = 2
        metrics = strategy.get_metrics()
        assert metrics["chunks_processed"] == 7
        assert metrics["active_chunks"] == 2

    def test_default_config(self):
        strategy = AsyncIOStrategy()
        assert strategy._config.max_concurrent_chunks == 2


class TestProcessModules:
    def test_process_skips_disabled_modules(self, sample_data):
        strategy = SequentialStrategy()
        enabled = MagicMock()
        enabled.enabled = True
        enabled.process.return_value = sample_data
        disabled = MagicMock()
        disabled.enabled = False

        strategy._modules = [disabled, enabled]
        result = strategy._process_modules(sample_data)
        assert result is sample_data
        enabled.process.assert_called_once()
        disabled.process.assert_not_called()

    def test_process_in_order(self, sample_data):
        strategy = SequentialStrategy()
        calls = []

        m1 = MagicMock()
        m1.enabled = True
        m1.process.side_effect = lambda d: (calls.append("m1"), d)[1]
        m2 = MagicMock()
        m2.enabled = True
        m2.process.side_effect = lambda d: (calls.append("m2"), d)[1]

        strategy._modules = [m1, m2]
        strategy._process_modules(sample_data)
        assert calls == ["m1", "m2"]
