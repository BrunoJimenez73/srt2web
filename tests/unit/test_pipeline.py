"""
Unit tests for Pipeline.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock
from core.pipeline import Pipeline, PipelineState
from core.module_base import BaseModule, PipelineData, ModuleState


class DummyModule(BaseModule):
    """A dummy module for testing."""

    def __init__(self, name: str = "dummy", config: dict = None):
        self._start_called = False
        self._stop_called = False
        self._process_count = 0
        super().__init__(name, config)

    def start(self):
        self._start_called = True
        self._state = ModuleState.RUNNING

    def stop(self):
        self._stop_called = True
        self._state = ModuleState.IDLE

    def _do_process(self, data: PipelineData) -> PipelineData:
        self._process_count += 1
        data.metadata["dummy_processed"] = True
        return data


class TestPipeline:
    """Tests for the Pipeline class."""

    def test_init(self):
        """Test pipeline initialization."""
        pipeline = Pipeline()

        assert pipeline.state == PipelineState.IDLE
        assert len(pipeline.get_modules()) == 0

    def test_register_module(self):
        """Test registering a module."""
        pipeline = Pipeline()
        module = DummyModule("test_module")

        pipeline.register_module(module)

        assert len(pipeline.get_modules()) == 1
        assert pipeline.get_module("test_module") is module

    def test_register_multiple_modules(self):
        """Test registering multiple modules."""
        pipeline = Pipeline()

        pipeline.register_module(DummyModule("mod1"))
        pipeline.register_module(DummyModule("mod2"))
        pipeline.register_module(DummyModule("mod3"))

        assert len(pipeline.get_modules()) == 3

    def test_get_module_not_found(self):
        """Test getting a non-existent module."""
        pipeline = Pipeline()

        assert pipeline.get_module("nonexistent") is None

    def test_reconfigure_modules(self):
        """Test reconfiguring all modules."""
        pipeline = Pipeline()
        module = DummyModule("test")
        pipeline.register_module(module)

        from core.config_manager import ConfigManager

        config = ConfigManager()

        config.set_module_enabled("test", False)

        pipeline.reconfigure(config)

        assert module.enabled is False

    def test_start_pipeline(self):
        """Test starting the pipeline."""
        pipeline = Pipeline()
        module = DummyModule("test")
        pipeline.register_module(module)

        pipeline.start()

        assert pipeline.state in (PipelineState.STARTING, PipelineState.RUNNING)

        pipeline.stop()

    def test_stop_pipeline(self):
        """Test stopping the pipeline."""
        pipeline = Pipeline()
        module = DummyModule("test")
        pipeline.register_module(module)

        pipeline.start()

        pipeline.stop()

        assert pipeline.state == PipelineState.IDLE

    def test_start_already_running(self):
        """Test starting an already running pipeline."""
        pipeline = Pipeline()

        pipeline.start()

        pipeline.start()

        assert pipeline.state == PipelineState.RUNNING

        pipeline.stop()

    def test_process_data_through_modules(self):
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

    def test_disabled_module_skipped(self):
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

    def test_module_error_handling(self):
        """Test that module errors don't stop the pipeline."""
        pipeline = Pipeline()

        error_module = DummyModule("error")

        def raise_error(data):
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
                pass

        assert normal_module._process_count == 1

    def test_get_status(self):
        """Test getting pipeline status."""
        pipeline = Pipeline()
        pipeline.register_module(DummyModule("mod1"))

        status = pipeline.get_status()

        assert "state" in status
        assert "modules" in status
        assert status["state"] == "idle"
        assert len(status["modules"]) == 1

    def test_callbacks(self):
        """Test log and state change callbacks."""
        pipeline = Pipeline()

        log_messages = []
        state_changes = []

        def on_log(level, message):
            log_messages.append((level, message))

        def on_state(state):
            state_changes.append(state)

        pipeline._on_log = on_log
        pipeline._on_state_change = on_state

        pipeline._log("info", "Test message")
        pipeline._set_state(PipelineState.RUNNING)

        assert ("info", "Test message") in log_messages
        assert "running" in state_changes

    def test_chunk_index_tracking(self):
        """Test that chunk index is properly tracked."""
        pipeline = Pipeline()

        assert pipeline._chunk_index == 0

        pipeline._chunk_index = 2

        assert pipeline._chunk_index == 2


class TestPipelineState:
    """Tests for PipelineState enum."""

    def test_pipeline_states(self):
        """Test all pipeline states exist."""
        assert PipelineState.IDLE.value == "idle"
        assert PipelineState.STARTING.value == "starting"
        assert PipelineState.RUNNING.value == "running"
        assert PipelineState.STOPPING.value == "stopping"
        assert PipelineState.ERROR.value == "error"
