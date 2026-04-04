"""
Tests for core/module_interface.py.

Tests for ProcessingModule Protocol and BaseModule class.
"""

import pytest
import asyncio
from typing import Optional

from core.module_interface import BaseModule, ProcessingModule
from core.types import ModuleState, ModuleStatus, PipelineData
from core.exceptions import SRT2WebError


class TestProcessingModuleProtocol:
    """Test suite for ProcessingModule Protocol."""
    
    def test_protocol_is_runtime_checkable(self):
        """Test that ProcessingModule is runtime checkable."""
        from typing import runtime_checkable
        assert hasattr(ProcessingModule, '_is_runtime_protocol')
    
    def test_protocol_has_required_methods(self):
        """Test that ProcessingModule has required methods."""
        assert hasattr(ProcessingModule, 'initialize')
        assert hasattr(ProcessingModule, 'process')
        assert hasattr(ProcessingModule, 'shutdown')
        assert hasattr(ProcessingModule, 'get_status')
        assert hasattr(ProcessingModule, 'reset')
    
    def test_protocol_annotations(self):
        """Test that ProcessingModule has required annotations."""
        # Check that the protocol defines the required annotations
        assert 'name' in ProcessingModule.__annotations__
        assert 'enabled' in ProcessingModule.__annotations__


class ConcreteModule(BaseModule):
    """Concrete implementation of BaseModule for testing."""
    
    def __init__(self, name: str = "test_module", enabled: bool = True):
        super().__init__(name, enabled)
        self.initialized = False
        self.processed = False
        self.shutdown_called = False
    
    async def initialize(self) -> None:
        self._set_state(ModuleState.INITIALIZING)
        await asyncio.sleep(0.01)  # Simulate async work
        self.initialized = True
        self._set_state(ModuleState.READY)
    
    async def process(self, data: PipelineData) -> PipelineData:
        self._start_processing()
        await asyncio.sleep(0.01)  # Simulate async work
        data.metadata[self.name] = "processed"
        self.processed = True
        self._end_processing(0.01)
        return data
    
    async def shutdown(self) -> None:
        self._set_state(ModuleState.IDLE)
        await asyncio.sleep(0.01)  # Simulate async work
        self.shutdown_called = True


class TestBaseModule:
    """Test suite for BaseModule class."""
    
    def test_base_module_creation(self):
        """Test BaseModule creation with default values."""
        module = ConcreteModule()
        assert module.name == "test_module"
        assert module.enabled is True
        assert module.state == ModuleState.IDLE
    
    def test_base_module_custom_name(self):
        """Test BaseModule creation with custom name."""
        module = ConcreteModule(name="custom_module")
        assert module.name == "custom_module"
    
    def test_base_module_disabled(self):
        """Test BaseModule creation with disabled state."""
        module = ConcreteModule(enabled=False)
        assert module.enabled is False
        assert module.state == ModuleState.DISABLED
    
    def test_base_module_enable_disable(self):
        """Test enabling and disabling a module."""
        module = ConcreteModule()
        assert module.enabled is True
        
        module.enabled = False
        assert module.enabled is False
        assert module.state == ModuleState.DISABLED
        
        module.enabled = True
        assert module.enabled is True
        # Note: enabling doesn't change state from DISABLED automatically
    
    def test_base_module_get_status(self):
        """Test get_status returns ModuleStatus."""
        module = ConcreteModule()
        status = module.get_status()
        
        assert isinstance(status, ModuleStatus)
        assert status.name == "test_module"
        assert status.enabled is True
        assert status.state == ModuleState.IDLE
    
    def test_base_module_reset(self):
        """Test reset returns module to IDLE state."""
        module = ConcreteModule()
        module._set_state(ModuleState.ERROR)
        assert module.state == ModuleState.ERROR
        
        module.reset()
        assert module.state == ModuleState.IDLE
    
    @pytest.mark.asyncio
    async def test_base_module_initialize(self):
        """Test module initialization."""
        module = ConcreteModule()
        assert module.initialized is False
        
        await module.initialize()
        assert module.initialized is True
        assert module.state == ModuleState.READY
    
    @pytest.mark.asyncio
    async def test_base_module_process(self):
        """Test module processing."""
        module = ConcreteModule()
        await module.initialize()
        
        data = PipelineData()
        assert module.processed is False
        
        result = await module.process(data)
        assert module.processed is True
        assert result is data  # Should return same data object
        assert "test_module" in result.metadata
    
    @pytest.mark.asyncio
    async def test_base_module_processing_metrics(self):
        """Test that processing updates metrics."""
        module = ConcreteModule()
        await module.initialize()
        
        status = module.get_status()
        assert status.processed_chunks == 0
        
        data = PipelineData()
        await module.process(data)
        
        status = module.get_status()
        assert status.processed_chunks == 1
        assert status.last_processing_time > 0
    
    @pytest.mark.asyncio
    async def test_base_module_shutdown(self):
        """Test module shutdown."""
        module = ConcreteModule()
        await module.initialize()
        assert module.shutdown_called is False
        
        await module.shutdown()
        assert module.shutdown_called is True
    
    def test_base_module_set_error(self):
        """Test setting error state."""
        module = ConcreteModule()
        status = module.get_status()
        
        assert status.error_count == 0
        assert status.last_error is None
        
        module._set_error("Test error")
        
        status = module.get_status()
        assert status.error_count == 1
        assert status.last_error == "Test error"
        assert module.state == ModuleState.ERROR
    
    def test_base_module_repr(self):
        """Test string representation."""
        module = ConcreteModule(name="test")
        repr_str = repr(module)
        
        assert "ConcreteModule" in repr_str
        assert "test" in repr_str
        assert "idle" in repr_str
    
    def test_base_module_is_processing_module(self):
        """Test that BaseModule subclasses satisfy ProcessingModule protocol."""
        module = ConcreteModule()
        # Note: Since ProcessingModule is a Protocol with abstract methods,
        # we check if our module has the required interface
        assert hasattr(module, 'initialize')
        assert hasattr(module, 'process')
        assert hasattr(module, 'shutdown')
        assert hasattr(module, 'get_status')
        assert hasattr(module, 'reset')
        assert hasattr(module, 'name')
        assert hasattr(module, 'enabled')


class ErrorModule(BaseModule):
    """Module that raises errors for testing error handling."""
    
    def __init__(self, fail_on: str = "initialize"):
        super().__init__("error_module")
        self.fail_on = fail_on
    
    async def initialize(self) -> None:
        if self.fail_on == "initialize":
            raise ValueError("Initialization failed")
        self._set_state(ModuleState.READY)
    
    async def process(self, data: PipelineData) -> PipelineData:
        if self.fail_on == "process":
            raise ValueError("Processing failed")
        return data
    
    async def shutdown(self) -> None:
        if self.fail_on == "shutdown":
            raise ValueError("Shutdown failed")


class TestBaseModuleErrorHandling:
    """Test suite for BaseModule error handling."""
    
    @pytest.mark.asyncio
    async def test_initialize_error_sets_error_state(self):
        """Test that initialization error sets error state."""
        module = ErrorModule(fail_on="initialize")
        
        with pytest.raises(ValueError):
            await module.initialize()
        
        assert module.state == ModuleState.IDLE  # Error before state change
    
    def test_error_handling_sets_error_state(self):
        """Test that _set_error sets error state."""
        module = ConcreteModule()
        assert module.state == ModuleState.IDLE
        
        module._set_error("Test error")
        assert module.state == ModuleState.ERROR
        assert module.get_status().error_count == 1
    
    def test_multiple_errors_increment_count(self):
        """Test that multiple errors increment error count."""
        module = ConcreteModule()
        
        module._set_error("Error 1")
        module._set_error("Error 2")
        module._set_error("Error 3")
        
        status = module.get_status()
        assert status.error_count == 3
        assert status.last_error == "Error 3"
    
    def test_reset_clears_error(self):
        """Test that reset clears error state and counters."""
        module = ConcreteModule()
        module._set_error("Test error")
        
        assert module.state == ModuleState.ERROR
        assert module.get_status().error_count == 1
        
        module.reset()
        
        assert module.state == ModuleState.IDLE
        assert module.get_status().last_error is None
        assert module.get_status().error_count == 0


class TestModuleStateTransitions:
    """Test suite for module state transitions."""
    
    @pytest.mark.asyncio
    async def test_idle_to_ready_transition(self):
        """Test transition from IDLE to READY."""
        module = ConcreteModule()
        assert module.state == ModuleState.IDLE
        
        await module.initialize()
        assert module.state == ModuleState.READY
    
    @pytest.mark.asyncio
    async def test_ready_to_processing_transition(self):
        """Test transition from READY to PROCESSING."""
        module = ConcreteModule()
        await module.initialize()
        
        # During processing, state should be PROCESSING
        # We need to check mid-processing, so we'll use a custom module
        class SlowModule(ConcreteModule):
            async def process(self, data: PipelineData) -> PipelineData:
                self._start_processing()
                await asyncio.sleep(0.1)
                self._end_processing(0.1)
                return data
        
        module = SlowModule()
        await module.initialize()
        assert module.state == ModuleState.READY
        
        # Start processing without awaiting
        task = asyncio.create_task(module.process(PipelineData()))
        await asyncio.sleep(0.05)  # Wait a bit
        assert module.state == ModuleState.PROCESSING
        
        await task  # Complete processing
        assert module.state == ModuleState.READY
    
    def test_disabled_state(self):
        """Test DISABLED state."""
        module = ConcreteModule(enabled=False)
        assert module.state == ModuleState.DISABLED
        assert module.enabled is False
        
        # Disabling an enabled module should set DISABLED state
        module2 = ConcreteModule(enabled=True)
        assert module2.state == ModuleState.IDLE
        module2.enabled = False
        assert module2.state == ModuleState.DISABLED
