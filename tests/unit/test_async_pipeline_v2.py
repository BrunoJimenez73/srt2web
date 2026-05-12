"""
Tests for core/async_pipeline_v2.py.

Tests for the new asyncio-based pipeline implementation.
"""

import asyncio

import pytest

from core.exceptions import PipelineStateError
from core.module_base import PipelineData

# Import the updated AsyncPipeline implementation and the correct schema definitions.
# The original test expected a module `core.async_pipeline_v2` and types from `core.types`,
# but the current architecture places the async pipeline in `core.pipeline.async_pipeline`
# and the data models in `core.schemas`. We alias the imported class to keep the test
# name `AsyncPipelineV2` unchanged while using the new implementation.
from core.pipeline.async_pipeline import AsyncPipelineV2
from core.schemas import ModuleState, PipelineState


class MockAsyncModule:
    """Mock module with async methods for testing."""

    def __init__(self, name: str = "mock_module", delay: float = 0.01, fail: bool = False):  # type: ignore
        self.name = name
        self.delay = delay
        self.fail = fail
        self.initialized = False
        self.shutdown_called = False
        self.processed_count = 0

    async def initialize(self) -> None:
        await asyncio.sleep(0.001)
        self.initialized = True

    async def process(self, data: PipelineData) -> PipelineData:
        if self.fail:
            raise ValueError(f"Module {self.name} failed")
        await asyncio.sleep(self.delay)
        data.metadata[self.name] = "processed"
        self.processed_count += 1
        return data

    async def shutdown(self) -> None:
        await asyncio.sleep(0.001)
        self.shutdown_called = True

    def get_status(self):  # type: ignore
        return type(
            "Status",
            (),
            {
                "name": self.name,
                "state": ModuleState.READY if self.initialized else ModuleState.IDLE,
                "enabled": True,
                "processed_chunks": self.processed_count,
            },
        )()


class MockSyncModule:
    """Mock module with sync methods for testing."""

    def __init__(self, name: str = "sync_module"):  # type: ignore
        self.name = name
        self.initialized = False
        self.shutdown_called = False
        self.processed_count = 0

    def initialize(self) -> None:
        self.initialized = True

    def process(self, data: PipelineData) -> PipelineData:
        data.metadata[self.name] = "sync_processed"
        self.processed_count += 1
        return data

    def shutdown(self) -> None:
        self.shutdown_called = True

    def get_status(self):  # type: ignore
        return type(
            "Status",
            (),
            {
                "name": self.name,
                "state": ModuleState.READY if self.initialized else ModuleState.IDLE,
                "enabled": True,
                "processed_chunks": self.processed_count,
            },
        )()


class MockInputSource:
    """Mock input source for testing."""

    def __init__(self, data_items: list = None):  # type: ignore
        self.data_items = data_items or []
        self.index = 0
        self.initialized = False

    async def initialize(self) -> None:
        self.initialized = True

    async def get_data(self) -> PipelineData:
        if self.index < len(self.data_items):
            item = self.data_items[self.index]
            self.index += 1
            return item
        return None

    def shutdown(self) -> None:
        pass


class TestAsyncPipelineV2Creation:
    """Test suite for AsyncPipelineV2 creation and basic properties."""

    def test_pipeline_creation(self) -> None:
        """Test basic pipeline creation."""
        pipeline = AsyncPipelineV2()
        assert pipeline.state == PipelineState.IDLE
        assert not pipeline.is_running
        assert pipeline.max_concurrent_chunks == 3
        assert pipeline.retry_attempts == 2

    def test_pipeline_custom_config(self) -> None:
        """Test pipeline creation with custom config."""
        pipeline = AsyncPipelineV2(max_concurrent_chunks=5, retry_attempts=3, retry_delay=0.5)
        assert pipeline.max_concurrent_chunks == 5
        assert pipeline.retry_attempts == 3
        assert pipeline.retry_delay == 0.5

    def test_pipeline_set_state(self) -> None:
        """Test setting pipeline state."""
        pipeline = AsyncPipelineV2()
        pipeline._set_state(PipelineState.RUNNING)
        assert pipeline.state == PipelineState.RUNNING
        assert pipeline.is_running


@pytest.mark.asyncio
class TestAsyncPipelineV2Initialization:
    """Test suite for AsyncPipelineV2 initialization."""

    async def test_initialize_empty_pipeline(self):
        """Test initializing pipeline with no modules."""
        pipeline = AsyncPipelineV2()
        await pipeline.initialize()
        # Should succeed without errors

    async def test_initialize_with_modules(self):
        """Test initializing pipeline with modules."""
        pipeline = AsyncPipelineV2()
        module = MockAsyncModule()
        pipeline.register_module(module)

        await pipeline.initialize()
        assert module.initialized is True

    async def test_initialize_with_mixed_modules(self):
        """Test initializing pipeline with sync and async modules."""
        pipeline = AsyncPipelineV2()
        pipeline.register_module(MockAsyncModule("async1"))
        pipeline.register_module(MockSyncModule("sync1"))
        pipeline.register_module(MockAsyncModule("async2"))

        await pipeline.initialize()
        assert pipeline._modules[0].initialized is True
        assert pipeline._modules[1].initialized is True
        assert pipeline._modules[2].initialized is True

    async def test_initialize_with_input_output(self):
        """Test initializing pipeline with input/output."""
        pipeline = AsyncPipelineV2()
        input_source = MockInputSource()
        pipeline.set_input_source(input_source)

        await pipeline.initialize()
        assert input_source.initialized is True


@pytest.mark.asyncio
class TestAsyncPipelineV2Processing:
    """Test suite for AsyncPipelineV2 processing."""

    async def test_process_single_chunk(self):
        """Test processing a single chunk."""
        pipeline = AsyncPipelineV2()
        module = MockAsyncModule()
        pipeline.register_module(module)

        await pipeline.initialize()

        data = PipelineData(chunk_index=0)
        result = await pipeline._process_chunk(data)

        assert result is data
        assert "mock_module" in result.metadata
        assert module.processed_count == 1

    async def test_process_multiple_modules(self):
        """Test processing through multiple modules."""
        pipeline = AsyncPipelineV2()
        module1 = MockAsyncModule("mod1")
        module2 = MockAsyncModule("mod2")
        module3 = MockAsyncModule("mod3")

        pipeline.register_module(module1)
        pipeline.register_module(module2)
        pipeline.register_module(module3)

        await pipeline.initialize()

        data = PipelineData(chunk_index=0)
        result = await pipeline._process_chunk(data)

        assert "mod1" in result.metadata
        assert "mod2" in result.metadata
        assert "mod3" in result.metadata
        assert module1.processed_count == 1
        assert module2.processed_count == 1
        assert module3.processed_count == 1

    async def test_process_with_sync_module(self):
        """Test processing with sync module."""
        pipeline = AsyncPipelineV2()
        sync_module = MockSyncModule()
        pipeline.register_module(sync_module)

        await pipeline.initialize()

        data = PipelineData(chunk_index=0)
        result = await pipeline._process_chunk(data)

        assert "sync_module" in result.metadata
        assert sync_module.processed_count == 1


@pytest.mark.asyncio
class TestAsyncPipelineV2Concurrency:
    """Test suite for AsyncPipelineV2 concurrency."""

    async def test_concurrent_processing_limit(self):
        """Test that concurrent processing is limited."""
        pipeline = AsyncPipelineV2(max_concurrent_chunks=2)

        # Create slow module
        slow_module = MockAsyncModule(delay=0.1)
        pipeline.register_module(slow_module)

        await pipeline.initialize()

        # Start multiple chunks concurrently
        chunks = [PipelineData(chunk_index=i) for i in range(5)]
        tasks = [pipeline._process_chunk(data) for data in chunks]

        # Wait for all to complete
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert slow_module.processed_count == 5

    async def test_semaphore_limits_concurrency(self):
        """Test that semaphore properly limits concurrency."""
        max_concurrent = 2
        pipeline = AsyncPipelineV2(max_concurrent_chunks=max_concurrent)

        # Track concurrent executions
        current_concurrent = 0
        max_observed_concurrent = 0

        class TrackingModule:
            def __init__(self):  # type: ignore
                self.name = "tracking"

            async def initialize(self):
                pass

            async def process(self, data):
                nonlocal current_concurrent, max_observed_concurrent
                current_concurrent += 1
                max_observed_concurrent = max(max_observed_concurrent, current_concurrent)
                await asyncio.sleep(0.05)
                current_concurrent -= 1
                return data

            async def shutdown(self):
                pass

            def get_status(self):  # type: ignore
                return type("Status", (), {"name": "tracking"})()

        pipeline.register_module(TrackingModule())
        await pipeline.initialize()

        # Process many chunks concurrently
        chunks = [PipelineData(chunk_index=i) for i in range(10)]
        tasks = [pipeline._process_chunk(data) for data in chunks]
        await asyncio.gather(*tasks)

        # Max observed should not exceed limit
        assert max_observed_concurrent <= max_concurrent


@pytest.mark.asyncio
class TestAsyncPipelineV2ErrorHandling:
    """Test suite for AsyncPipelineV2 error handling."""

    async def test_module_failure_raises_error(self):
        """Test that module failure raises error."""
        pipeline = AsyncPipelineV2(retry_attempts=0)  # No retries
        fail_module = MockAsyncModule(fail=True)
        pipeline.register_module(fail_module)

        await pipeline.initialize()

        data = PipelineData(chunk_index=0)
        with pytest.raises(Exception):
            await pipeline._process_chunk(data)

    async def test_retry_on_failure(self):
        """Test that failed processing is retried."""
        call_count = 0

        class FlakyModule:
            def __init__(self):  # type: ignore
                self.name = "flaky"

            async def initialize(self):
                pass

            async def process(self, data):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise ValueError("Temporary failure")
                return data

            async def shutdown(self):
                pass

            def get_status(self):  # type: ignore
                return type("Status", (), {"name": "flaky"})()

        pipeline = AsyncPipelineV2(retry_attempts=3, retry_delay=0.01)
        pipeline.register_module(FlakyModule())

        await pipeline.initialize()

        data = PipelineData(chunk_index=0)
        result = await pipeline._process_chunk(data)

        assert result is data
        assert call_count == 3  # Failed twice, succeeded on third

    def test_metrics_track_failures_manual(self):  # type: ignore
        """Test that metrics track failed chunks (manual counting)."""
        pipeline = AsyncPipelineV2()

        # Manually set metrics to test get_metrics
        pipeline._chunks_processed = 5
        pipeline._chunks_failed = 2

        metrics = pipeline.get_metrics()
        assert metrics["chunks_processed"] == 5
        assert metrics["chunks_failed"] == 2


@pytest.mark.asyncio
class TestAsyncPipelineV2StartStop:
    """Test suite for AsyncPipelineV2 start/stop."""

    async def test_start_running_pipeline(self):
        """Test starting a running pipeline raises error."""
        pipeline = AsyncPipelineV2()
        # Manually set state to RUNNING
        pipeline.state = PipelineState.RUNNING

        with pytest.raises(PipelineStateError):
            await pipeline.start()

    async def test_start_idle_pipeline(self):
        """Test starting an idle pipeline works."""
        pipeline = AsyncPipelineV2()
        await pipeline.initialize()

        # Should be able to start without error
        await pipeline.start()

        # Should be running
        assert pipeline.is_running

        # Clean up
        await pipeline.stop()

    async def test_stop_not_running_pipeline(self):
        """Test stopping a non-running pipeline does nothing."""
        pipeline = AsyncPipelineV2()
        # Should not raise
        await pipeline.stop()

    async def test_shutdown_calls_module_shutdown(self):
        """Test that shutdown calls module shutdown methods."""
        pipeline = AsyncPipelineV2()
        module1 = MockAsyncModule("mod1")
        module2 = MockAsyncModule("mod2")
        pipeline.register_module(module1)
        pipeline.register_module(module2)

        await pipeline.initialize()
        await pipeline.shutdown()

        assert module1.shutdown_called is True
        assert module2.shutdown_called is True


@pytest.mark.asyncio
class TestAsyncPipelineV2Callbacks:
    """Test suite for AsyncPipelineV2 callbacks."""

    async def test_state_change_callback(self):
        """Test state change callback is called."""
        pipeline = AsyncPipelineV2()
        states = []

        def on_state_change(state) -> None:
            states.append(state)

        pipeline.set_state_callback(on_state_change)
        pipeline._set_state(PipelineState.RUNNING)

        assert "running" in states

    async def test_chunk_complete_callback(self):
        """Test chunk complete callback is called."""
        pipeline = AsyncPipelineV2()
        module = MockAsyncModule()
        pipeline.register_module(module)

        completed_chunks = []

        def on_chunk_complete(index, data) -> None:
            completed_chunks.append(index)

        pipeline.set_chunk_complete_callback(on_chunk_complete)

        await pipeline.initialize()

        data = PipelineData(chunk_index=42)
        await pipeline._process_chunk(data)

        assert 42 in completed_chunks


class TestAsyncPipelineV2Metrics:
    """Test suite for AsyncPipelineV2 metrics."""

    def test_get_metrics_empty(self) -> None:
        """Test metrics for empty pipeline."""
        pipeline = AsyncPipelineV2()
        metrics = pipeline.get_metrics()

        assert metrics["state"] == "idle"
        assert metrics["chunks_processed"] == 0
        assert metrics["chunks_failed"] == 0
        assert metrics["modules_count"] == 0

    def test_get_metrics_after_processing(self) -> None:
        """Test metrics after processing chunks."""
        pipeline = AsyncPipelineV2()
        pipeline._chunks_processed = 10
        pipeline._chunks_failed = 2
        pipeline._total_processing_time = 5.0

        metrics = pipeline.get_metrics()

        assert metrics["chunks_processed"] == 10
        assert metrics["chunks_failed"] == 2
        assert metrics["avg_processing_time"] == 0.5
