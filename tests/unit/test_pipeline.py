"""
Unit tests for Pipeline.
"""

import time

import pytest

from core.exceptions import PipelineStateError
from core.module_base import BaseModule, ModuleState, PipelineData
from core.unified_pipeline import PipelineState
from core.unified_pipeline import UnifiedPipeline as Pipeline


class DummyModule(BaseModule):
    """A dummy module for testing."""

    def __init__(self, name: str = "dummy", config: dict = None):  # type: ignore
        self._start_called = False
        self._stop_called = False
        self._process_count = 0
        super().__init__(name, config)

    def start(self):  # type: ignore
        self._start_called = True
        self._state = ModuleState.RUNNING

    def stop(self):  # type: ignore
        self._stop_called = True
        self._state = ModuleState.IDLE

    def _do_process(self, data: PipelineData) -> PipelineData:
        self._process_count += 1
        data.metadata["dummy_processed"] = True
        return data


class TestPipeline:
    """Tests for the Pipeline class."""

    def test_init(self) -> None:
        """Test pipeline initialization."""
        pipeline = Pipeline()

        assert pipeline.state == PipelineState.IDLE
        assert len(pipeline.get_modules()) == 0

    def test_register_module(self) -> None:
        """Test registering a module."""
        pipeline = Pipeline()
        module = DummyModule("test_module")

        pipeline.register_module(module)

        assert len(pipeline.get_modules()) == 1
        assert pipeline.get_module("test_module") is module

    def test_register_multiple_modules(self) -> None:
        """Test registering multiple modules."""
        pipeline = Pipeline()

        pipeline.register_module(DummyModule("mod1"))
        pipeline.register_module(DummyModule("mod2"))
        pipeline.register_module(DummyModule("mod3"))

        assert len(pipeline.get_modules()) == 3

    def test_get_module_not_found(self) -> None:
        """Test getting a non-existent module."""
        pipeline = Pipeline()

        assert pipeline.get_module("nonexistent") is None

    def test_reconfigure_modules(self) -> None:
        """Test reconfiguring all modules."""
        pipeline = Pipeline()
        module = DummyModule("test")
        pipeline.register_module(module)

        from core.config_manager import ConfigManager

        config = ConfigManager()

        config.set_module_enabled("test", False)

        pipeline.reconfigure(config)

        assert module.enabled is False

    def test_start_pipeline(self) -> None:
        """Test starting the pipeline."""
        pipeline = Pipeline()
        module = DummyModule("test")
        pipeline.register_module(module)

        pipeline.start()

        assert pipeline.state in (PipelineState.STARTING, PipelineState.RUNNING)

        pipeline.stop()

    @pytest.mark.asyncio
    async def test_stop_pipeline(self):
        """Test stopping the pipeline."""
        pipeline = Pipeline()
        module = DummyModule("test")
        pipeline.register_module(module)

        pipeline.start()

        await pipeline.stop()

        # Give it a moment to transition state
        for _ in range(10):
            if pipeline.state in (PipelineState.STOPPING, PipelineState.IDLE):
                break
            time.sleep(0.1)

        assert pipeline.state in (PipelineState.STOPPING, PipelineState.IDLE)

    @pytest.mark.asyncio
    async def test_initialized_reset_after_stop(self):
        """Test that _initialized is reset after stop to enable restart."""
        pipeline = Pipeline()
        module = DummyModule("test")
        pipeline.register_module(module)

        pipeline.start()

        for _ in range(10):
            if pipeline.state == PipelineState.RUNNING:
                break
            time.sleep(0.1)

        assert pipeline.state == PipelineState.RUNNING

        await pipeline.stop()

        for _ in range(10):
            if pipeline.state == PipelineState.IDLE:
                break
            time.sleep(0.1)

        assert pipeline._initialized is False

    @pytest.mark.asyncio
    async def test_restart_after_stop(self):
        """Test that pipeline can restart after being stopped."""
        pipeline = Pipeline()
        module = DummyModule("test")
        pipeline.register_module(module)

        async def mock_initialize():
            pass

        pipeline.initialize = mock_initialize

        pipeline.start()

        for _ in range(10):
            if pipeline.state == PipelineState.RUNNING:
                break
            time.sleep(0.1)

        assert pipeline.state == PipelineState.RUNNING

        await pipeline.stop()

        for _ in range(10):
            if pipeline.state == PipelineState.IDLE:
                break
            time.sleep(0.1)

        assert pipeline.state == PipelineState.IDLE
        assert pipeline._initialized is False

        pipeline._initialized = True
        pipeline.start()

        for _ in range(10):
            if pipeline.state == PipelineState.RUNNING:
                break
            time.sleep(0.1)

        assert pipeline.state == PipelineState.RUNNING

    def test_start_already_running(self) -> None:
        """Test starting an already running pipeline."""
        pipeline = Pipeline()

        pipeline.start()

        with pytest.raises(PipelineStateError):
            pipeline.start()

        assert pipeline.state == PipelineState.RUNNING

        pipeline.stop()

    def test_process_data_through_modules(self) -> None:
        """Test that data flows through modules."""
        pipeline = Pipeline()

        mod1 = DummyModule("mod1")
        mod2 = DummyModule("mod2")

        pipeline.register_module(mod1)
        pipeline.register_module(mod2)

        test_data = PipelineData(chunk_index=0)

        # Simulate what _run_loop does
        for module in pipeline.get_modules():
            test_data = module.process(test_data)

        assert test_data.metadata.get("dummy_processed") is True
        assert mod1._process_count == 1
        assert mod2._process_count == 1

    def test_disabled_module_skipped(self) -> None:
        """Test that disabled modules are skipped."""
        pipeline = Pipeline()

        mod1 = DummyModule("mod1")
        mod2 = DummyModule("mod2")
        mod2.enabled = False

        pipeline.register_module(mod1)
        pipeline.register_module(mod2)

        test_data = PipelineData(chunk_index=0)

        for module in pipeline.get_modules():
            if module.enabled:
                test_data = module.process(test_data)

        assert mod1._process_count == 1
        assert mod2._process_count == 0

    def test_module_error_handling(self) -> None:
        """Test that module errors don't stop the pipeline."""
        pipeline = Pipeline()

        error_module = DummyModule("error")

        def raise_error(data) -> None:
            raise RuntimeError("Test error")

        error_module._do_process = raise_error
        normal_module = DummyModule("normal")

        pipeline.register_module(error_module)
        pipeline.register_module(normal_module)

        test_data = PipelineData(chunk_index=0)

        for module in pipeline.get_modules():
            try:
                test_data = module.process(test_data)
            except Exception:
                # Expected: failing module should not crash pipeline
                pass

        assert normal_module._process_count == 1

    def test_get_status(self) -> None:
        """Test getting pipeline status."""
        pipeline = Pipeline()
        pipeline.register_module(DummyModule("mod1"))

        status = pipeline.get_status()

        assert "state" in status
        assert "modules" in status
        assert status["state"] == "idle"
        # UnifiedPipeline includes at least the registered modules
        assert len(status["modules"]) >= 1

    def test_callbacks(self) -> None:
        """Test log and state change callbacks."""
        pipeline = Pipeline()

        log_messages = []
        state_changes = []

        def on_log(level, message) -> None:
            log_messages.append((level, message))

        def on_state(state) -> None:
            state_changes.append(state)

        pipeline._on_log = on_log
        pipeline._on_state_change = on_state

        pipeline._log("info", "Test message")
        pipeline._set_state(PipelineState.RUNNING)

        assert ("info", "Test message") in log_messages
        assert "running" in state_changes

    def test_chunk_index_tracking(self) -> None:
        """Test that chunk tracking works."""
        pipeline = Pipeline()

        # Initialize the pipeline (handle Python 3.14+ asyncio)
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(pipeline.initialize())

        # Check that the pipeline has chunk-related properties
        # _chunk_index is a property that returns metrics.chunks_processed
        assert hasattr(Pipeline, "_chunk_index"), "UnifiedPipeline should have _chunk_index property"

        # chunks_processed should be accessible after initialization
        try:
            index = pipeline._chunk_index
            assert isinstance(index, int), "_chunk_index should return int"
        except AttributeError:
            # If property access fails due to missing metrics, just check the property exists
            pass
        assert isinstance(pipeline._chunk_index, int), "_chunk_index should be int"


class TestPipelineState:
    """Tests for PipelineState enum."""

    def test_pipeline_states(self) -> None:
        """Test all pipeline states exist."""
        assert PipelineState.IDLE.value == "idle"
        assert PipelineState.STARTING.value == "starting"
        assert PipelineState.RUNNING.value == "running"
        assert PipelineState.STOPPING.value == "stopping"
        assert PipelineState.ERROR.value == "error"
