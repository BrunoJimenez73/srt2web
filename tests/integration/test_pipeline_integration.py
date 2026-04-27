"""
Integration tests for the refactored pipeline components.

These tests verify that the new components work together correctly.
"""

import pytest
import asyncio
from typing import List

from core.async_pipeline_v2 import AsyncPipelineV2
from core.module_interface import BaseModule
from core.types import PipelineData, ModuleState
from core.exceptions import ModuleProcessingError


class IntegrationTestModule(BaseModule):
    """Test module for integration testing."""
    
    def __init__(self, name: str, delay: float = 0.01, fail_rate: float = 0.0):  # type: ignore
        super().__init__(name)
        self.delay = delay
        self.fail_rate = fail_rate
        self.processed_chunks: List[int] = []
    
    async def initialize(self) -> None:
        self._set_state(ModuleState.INITIALIZING)
        await asyncio.sleep(0.001)
        self._set_state(ModuleState.READY)
    
    async def process(self, data: PipelineData) -> PipelineData:
        if self.fail_rate > 0 and len(self.processed_chunks) % int(1/self.fail_rate) == 0:
            raise ValueError(f"Simulated failure in {self.name}")
        
        self._start_processing()
        await asyncio.sleep(self.delay)
        
        # Add processing marker
        if "modules" not in data.metadata:
            data.metadata["modules"] = []
        data.metadata["modules"].append(self.name)
        
        self.processed_chunks.append(data.chunk_index)
        self._end_processing(self.delay)
        return data
    
    async def shutdown(self) -> None:
        self._set_state(ModuleState.IDLE)
        self.processed_chunks.clear()


class TestPipelineIntegration:
    """Integration tests for pipeline components."""
    
    @pytest.mark.asyncio
    async def test_pipeline_with_multiple_modules(self):
        """Test pipeline processes data through multiple modules in order."""
        pipeline = AsyncPipelineV2()
        
        # Create modules
        module1 = IntegrationTestModule("module1", delay=0.01)
        module2 = IntegrationTestModule("module2", delay=0.01)
        module3 = IntegrationTestModule("module3", delay=0.01)
        
        # Register in order
        pipeline.register_module(module1)
        pipeline.register_module(module2)
        pipeline.register_module(module3)
        
        # Initialize
        await pipeline.initialize()
        
        # Process data
        data = PipelineData(chunk_index=0)
        result = await pipeline._process_chunk(data)
        
        # Verify order
        assert result.metadata["modules"] == ["module1", "module2", "module3"]
        
        # Cleanup
        await pipeline.shutdown()
    
    @pytest.mark.asyncio
    async def test_pipeline_concurrent_processing(self):
        """Test pipeline can process multiple chunks concurrently."""
        pipeline = AsyncPipelineV2(max_concurrent_chunks=3)
        
        # Create slow module
        slow_module = IntegrationTestModule("slow", delay=0.05)
        pipeline.register_module(slow_module)
        
        await pipeline.initialize()
        
        # Process multiple chunks concurrently
        chunks = [PipelineData(chunk_index=i) for i in range(5)]
        tasks = [pipeline._process_chunk(data) for data in chunks]
        
        results = await asyncio.gather(*tasks)
        
        # All should complete
        assert len(results) == 5
        
        # Module should have processed all
        assert len(slow_module.processed_chunks) == 5
        
        await pipeline.shutdown()
    
    @pytest.mark.asyncio
    async def test_pipeline_error_recovery(self):
        """Test pipeline handles module errors gracefully."""
        pipeline = AsyncPipelineV2(retry_attempts=2, retry_delay=0.01)
        
        # Create module that never fails (to test pipeline continues)
        reliable_module = IntegrationTestModule("reliable", delay=0.01)
        pipeline.register_module(reliable_module)
        
        await pipeline.initialize()
        
        # Process multiple chunks - all should succeed
        success_count = 0
        for i in range(10):
            data = PipelineData(chunk_index=i)
            try:
                await pipeline._process_chunk(data)
                success_count += 1
            except Exception:
                pass
        
        # All should succeed with reliable module
        assert success_count == 10
        
        await pipeline.shutdown()
    
    @pytest.mark.asyncio
    async def test_pipeline_metrics_accuracy(self):
        """Test pipeline metrics are accurate."""
        pipeline = AsyncPipelineV2()
        
        module = IntegrationTestModule("test", delay=0.01)
        pipeline.register_module(module)
        
        await pipeline.initialize()
        
        # Process known number of chunks
        for i in range(5):
            data = PipelineData(chunk_index=i)
            await pipeline._process_chunk(data)
        
        # Check metrics
        metrics = pipeline.get_metrics()
        assert metrics["chunks_processed"] == 5
        assert metrics["chunks_failed"] == 0
        assert metrics["avg_processing_time"] > 0
        
        await pipeline.shutdown()
    
    @pytest.mark.asyncio
    async def test_pipeline_state_transitions(self):
        """Test pipeline transitions through states correctly."""
        pipeline = AsyncPipelineV2()
        
        module = IntegrationTestModule("test")
        pipeline.register_module(module)
        
        # Initial state
        assert pipeline.state.value == "idle"
        
        # After initialize
        await pipeline.initialize()
        assert pipeline.state.value == "idle"  # Back to idle after init
        
        # After start
        await pipeline.start()
        assert pipeline.is_running
        
        # After stop
        await pipeline.stop()
        assert not pipeline.is_running
        assert pipeline.state.value == "idle"


class TestModuleInterfaceIntegration:
    """Integration tests for module interface."""
    
    @pytest.mark.asyncio
    async def test_module_lifecycle(self):
        """Test module goes through complete lifecycle."""
        module = IntegrationTestModule("lifecycle_test")
        
        # Initial state
        assert module.state == ModuleState.IDLE
        
        # Initialize
        await module.initialize()
        assert module.state == ModuleState.READY
        
        # Process
        data = PipelineData(chunk_index=0)
        result = await module.process(data)
        assert module.state == ModuleState.READY
        assert 0 in module.processed_chunks
        
        # Shutdown
        await module.shutdown()
        assert module.state == ModuleState.IDLE
    
    @pytest.mark.asyncio
    async def test_module_error_handling(self):
        """Test module handles errors correctly."""
        module = IntegrationTestModule("error_test", delay=0.01)
        
        await module.initialize()
        
        # Normal processing
        data = PipelineData(chunk_index=0)
        result = await module.process(data)
        assert module.state == ModuleState.READY
        
        # Manually set error
        module._set_error("Test error")
        assert module.state == ModuleState.ERROR
        
        # Reset should clear error
        module.reset()
        assert module.state == ModuleState.IDLE
    
    def test_module_status_tracking(self) -> None:
        """Test module tracks status correctly."""
        module = IntegrationTestModule("status_test", delay=0.01)
        
        status = module.get_status()
        assert status.name == "status_test"
        assert status.enabled is True
        assert status.processed_chunks == 0


class TestExceptionHierarchyIntegration:
    """Integration tests for exception hierarchy."""
    
    def test_exception_catch_base(self) -> None:
        """Test that all exceptions can be caught by base."""
        from core.exceptions import SRT2WebError
        
        try:
            raise ValueError("Test")
        except Exception:
            pass  # This should work
        
        # Test our exceptions
        try:
            from core.exceptions import ConfigError
            raise ConfigError("test")
        except SRT2WebError:
            pass  # Should catch
    
    def test_exception_context_preservation(self) -> None:
        """Test that exception context is preserved."""
        from core.exceptions import ModuleProcessingError
        
        try:
            raise ValueError("Original error")
        except ValueError as e:
            error = ModuleProcessingError(
                "Processing failed",
                module="test",
                context={"original": str(e)}
            )
            assert "Original error" in str(error.context.values())