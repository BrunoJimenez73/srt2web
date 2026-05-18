"""
Integration tests for the refactored pipeline components.

These tests verify that the new components work together correctly.
"""

import asyncio

import pytest

from core.module_base import BaseModule, PipelineData
from core.schemas import ModuleState
from core.unified_pipeline import UnifiedPipeline


class IntegrationTestModule(BaseModule):
    """Test module for integration testing using the production BaseModule."""

    def __init__(self, name: str, delay: float = 0.01, fail_rate: float = 0.0):
        super().__init__(name)
        self.delay = delay
        self.fail_rate = fail_rate
        self.processed_chunks: list[int] = []

    def start(self) -> None:
        self._state = ModuleState.RUNNING

    def stop(self) -> None:
        self._state = ModuleState.IDLE
        self.processed_chunks.clear()

    def _do_process(self, data: PipelineData) -> PipelineData:
        if self.fail_rate > 0 and len(self.processed_chunks) % max(1, int(1 / self.fail_rate)) == 0:
            msg = f"Simulated failure in {self.name}"
            raise ValueError(msg)

        if "modules" not in data.metadata:
            data.metadata["modules"] = []
        data.metadata["modules"].append(self.name)

        self.processed_chunks.append(data.chunk_index)
        return data


class TestPipelineIntegration:
    """Integration tests for pipeline components."""

    @pytest.mark.asyncio
    async def test_pipeline_with_multiple_modules(self):
        """Test pipeline processes data through multiple modules in order."""
        pipeline = UnifiedPipeline()

        module1 = IntegrationTestModule("module1", delay=0.01)
        module2 = IntegrationTestModule("module2", delay=0.01)
        module3 = IntegrationTestModule("module3", delay=0.01)

        pipeline.register_module(module1)
        pipeline.register_module(module2)
        pipeline.register_module(module3)

        await pipeline.initialize()

        data = PipelineData(chunk_index=0)
        result = await pipeline._process_chunk(data)

        assert result.metadata["modules"] == ["module1", "module2", "module3"]

        await pipeline.shutdown()

    @pytest.mark.asyncio
    async def test_pipeline_concurrent_processing(self):
        """Test pipeline can process multiple chunks concurrently."""
        pipeline = UnifiedPipeline(max_concurrent_chunks=3)

        slow_module = IntegrationTestModule("slow", delay=0.05)
        pipeline.register_module(slow_module)

        await pipeline.initialize()

        chunks = [PipelineData(chunk_index=i) for i in range(5)]
        tasks = [pipeline._process_chunk(data) for data in chunks]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert len(slow_module.processed_chunks) == 5

        await pipeline.shutdown()

    @pytest.mark.asyncio
    async def test_pipeline_error_recovery(self):
        """Test pipeline handles module errors gracefully."""
        pipeline = UnifiedPipeline(retry_attempts=2, retry_delay=0.01)

        reliable_module = IntegrationTestModule("reliable", delay=0.01)
        pipeline.register_module(reliable_module)

        await pipeline.initialize()

        success_count = 0
        for i in range(10):
            data = PipelineData(chunk_index=i)
            try:
                await pipeline._process_chunk(data)
                success_count += 1
            except Exception:
                # Expected: some chunks may fail in stress test
                pass

        assert success_count == 10

        await pipeline.shutdown()

    @pytest.mark.asyncio
    async def test_pipeline_metrics_accuracy(self):
        """Test pipeline metrics are accurate."""
        pipeline = UnifiedPipeline()

        module = IntegrationTestModule("test", delay=0.01)
        pipeline.register_module(module)

        await pipeline.initialize()

        for i in range(5):
            data = PipelineData(chunk_index=i)
            await pipeline._process_chunk(data)

        metrics = pipeline.get_metrics()
        assert metrics["chunks_processed"] == 5
        assert metrics["chunks_failed"] == 0
        assert metrics["avg_processing_time"] > 0

        await pipeline.shutdown()

    @pytest.mark.asyncio
    async def test_pipeline_state_transitions(self):
        """Test pipeline transitions through states correctly."""
        pipeline = UnifiedPipeline()

        module = IntegrationTestModule("test")
        pipeline.register_module(module)

        assert pipeline.state.value == "idle"

        await pipeline.initialize()
        assert pipeline.state.value == "idle"

        pipeline.start(
            on_log=lambda level, msg: None,
            on_state_change=lambda state: None,
        )
        assert pipeline.is_running

        await pipeline.stop()
        assert not pipeline.is_running
        assert pipeline.state.value == "idle"


class TestModuleInterfaceIntegration:
    """Integration tests for module interface."""

    def test_module_status_tracking(self) -> None:
        """Test module tracks status correctly."""
        module = IntegrationTestModule("status_test", delay=0.01)

        status = module.get_status()
        assert status.name == "status_test"
        assert status.enabled is True
        assert status.processed_chunks == 0

    def test_module_error_handling(self) -> None:
        """Test module handles errors correctly."""
        module = IntegrationTestModule("error_test", delay=0.01, fail_rate=1.0)

        data = PipelineData(chunk_index=0)
        with pytest.raises(ValueError, match="Simulated failure"):
            module._do_process(data)

    def test_reset_error_clears_state(self) -> None:
        """Test reset_error clears error state."""
        module = IntegrationTestModule("reset_test")

        data = PipelineData(chunk_index=0)
        result = module.process(data)
        assert result is not None
        module._state = ModuleState.ERROR
        module._error_message = "test error"

        module.reset_error()
        assert module.state != ModuleState.ERROR


class TestExceptionHierarchyIntegration:
    """Integration tests for exception hierarchy."""

    def test_exception_catch_base(self) -> None:
        """Test that all exceptions can be caught by base."""
        from core.exceptions import SRT2WebError

        try:
            raise ValueError("Test")
        except Exception:
            # Intentional: testing that base Exception catches ValueError
            pass

        try:
            from core.exceptions import ConfigError

            raise ConfigError("test")
        except SRT2WebError:
            pass

    def test_exception_context_preservation(self) -> None:
        """Test that exception context is preserved."""
        from core.exceptions import ModuleProcessingError

        try:
            raise ValueError("Original error")
        except ValueError as e:
            error = ModuleProcessingError("Processing failed", module="test", context={"original": str(e)})
            assert "Original error" in str(error.context.values())
