"""
Tests for pipeline factory (core/pipeline/factory.py).
"""


import pytest

from core.pipeline.factory import create_pipeline, get_available_modes
from core.schemas import PipelineMode


class TestCreatePipeline:
    def test_create_sequential(self):
        pipeline = create_pipeline("sequential")
        assert pipeline.__class__.__name__ == "SequentialPipeline"
        assert pipeline.max_concurrent_chunks == 3

    def test_create_thread_parallel(self):
        pipeline = create_pipeline("thread_parallel")
        assert pipeline.__class__.__name__ == "ParallelPipeline"
        assert pipeline.max_concurrent_chunks == 3

    def test_create_asyncio(self):
        pipeline = create_pipeline("asyncio")
        assert pipeline.__class__.__name__ == "AsyncPipeline"
        assert pipeline.max_concurrent_chunks == 3

    def test_custom_max_concurrent_chunks(self):
        pipeline = create_pipeline("thread_parallel", max_concurrent_chunks=5)
        assert pipeline.max_concurrent_chunks == 5

    def test_custom_buffer_size(self):
        pipeline = create_pipeline("sequential", buffer_size=10)
        assert pipeline.buffer_size == 10

    def test_custom_retry(self):
        pipeline = create_pipeline("asyncio", retry_attempts=3, retry_delay=2.0)
        assert pipeline.retry_attempts == 3
        assert pipeline.retry_delay == 2.0

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            create_pipeline("invalid_mode")

    def test_case_insensitive(self):
        pipeline = create_pipeline("SEQUENTIAL")
        assert pipeline.__class__.__name__ == "SequentialPipeline"


class TestPipelineMode:
    def test_enum_values(self):
        assert PipelineMode.SEQUENTIAL.value == "sequential"
        assert PipelineMode.THREAD_PARALLEL.value == "thread_parallel"
        assert PipelineMode.ASYNCIO.value == "asyncio"


class TestGetAvailableModes:
    def test_returns_dict(self):
        modes = get_available_modes()
        assert isinstance(modes, dict)
        assert "sequential" in modes
        assert "thread_parallel" in modes
        assert "asyncio" in modes

    def test_descriptions(self):
        modes = get_available_modes()
        assert "secuencial" in modes["sequential"].lower()
        assert "thread" in modes["thread_parallel"].lower()
        assert "asyncio" in modes["asyncio"].lower()
