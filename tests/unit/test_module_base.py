"""
Unit tests for BaseModule.
"""

import pytest
import numpy as np
from core.module_base import BaseModule, PipelineData, ModuleState, ModuleStatus


class TestModule(BaseModule):
    """Concrete implementation of BaseModule for testing."""

    def __init__(self, name: str = "test", config: dict[str, object] | None = None) -> None:
        super().__init__(name, config)
        self.process_calls: list[object] = []

    def start(self) -> None:
        self._state = ModuleState.RUNNING

    def stop(self) -> None:
        self._state = ModuleState.IDLE

    def _do_process(self, data: PipelineData) -> PipelineData:
        self.process_calls.append(data.chunk_index)
        data.metadata["processed_by"] = self.name
        return data


class TestPipelineData:
    """Tests for PipelineData dataclass."""

    def test_default_init(self) -> None:
        """Test default initialization."""
        data = PipelineData()

        assert data.chunk_index == 0
        assert data.timestamp == 0.0
        assert data.duration == 0.0
        assert data.video_chunk_path is None
        assert data.audio_chunk_path is None

    def test_full_init(self) -> None:
        """Test full initialization."""
        data = PipelineData(
            chunk_index=5,
            timestamp=1234567890.0,
            duration=4.0,
            video_chunk_path="/path/to/video.ts",
            audio_chunk_path="/path/to/audio.wav",
            transcript="Hello world",
            translated_text="Hola mundo",
        )

        assert data.chunk_index == 5
        assert data.timestamp == 1234567890.0
        assert data.duration == 4.0
        assert data.video_chunk_path == "/path/to/video.ts"
        assert data.transcript == "Hello world"
        assert data.translated_text == "Hola mundo"

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        data = PipelineData(
            chunk_index=1,
            transcript="Test",
        )

        result = data.to_dict()

        assert isinstance(result, dict)
        assert result["chunk_index"] == 1
        assert result["transcript"] == "Test"

    def test_to_dict_handles_numpy(self) -> None:
        """Test serialization handles numpy arrays."""
        data = PipelineData()
        data.audio_samples = np.array([1, 2, 3])

        result = data.to_dict()

        assert "audio_samples" in result
        assert "ndarray" in result["audio_samples"]


class TestModuleStatus:
    """Tests for ModuleStatus dataclass."""

    def test_default_status(self) -> None:
        """Test default status values."""
        status = ModuleStatus(
            name="test",
            state=ModuleState.IDLE,
            enabled=True,
        )

        assert status.name == "test"
        assert status.state == ModuleState.IDLE
        assert status.enabled is True
        assert status.error_message is None
        assert status.processed_chunks == 0
        assert status.last_process_time_ms == 0.0

    def test_status_to_dict(self) -> None:
        """Test status serialization."""
        status = ModuleStatus(
            name="test",
            state=ModuleState.RUNNING,
            enabled=True,
            processed_chunks=10,
            last_process_time_ms=150.5,
        )

        result = status.to_dict()

        assert result["name"] == "test"
        assert result["state"] == "running"
        assert result["processed_chunks"] == 10
        assert result["last_process_time_ms"] == 150.5


class TestBaseModule:
    """Tests for BaseModule abstract class."""

    def test_init(self) -> None:
        """Test module initialization."""
        module = TestModule("test_module")

        assert module.name == "test_module"
        assert module.enabled is True
        assert module.state == ModuleState.IDLE

    def test_init_with_config(self) -> None:
        """Test initialization with config."""
        config = {"enabled": False, "custom_key": "custom_value"}
        module = TestModule("test", config)

        assert module.enabled is False

    def test_configure(self) -> None:
        """Test configure method."""
        module = TestModule("test")

        module.configure({"enabled": False})

        assert module.enabled is False

    def test_disabled_state(self) -> None:
        """Test disabled state after configuration."""
        module = TestModule("test")
        module.configure({"enabled": False})

        assert module.state == ModuleState.DISABLED

    def test_process(self) -> None:
        """Test process method."""
        module = TestModule("test")
        module.start()

        data = PipelineData(chunk_index=0)
        result = module.process(data)

        assert len(module.process_calls) == 1
        assert result.metadata["processed_by"] == "test"

    def test_process_disabled_module(self) -> None:
        """Test that disabled modules don't process."""
        module = TestModule("test")
        module.configure({"enabled": False})

        data = PipelineData(chunk_index=0)
        result = module.process(data)

        assert len(module.process_calls) == 0

    def test_process_error_handling(self) -> None:
        """Test error handling in process method."""
        module = TestModule("test")

        def raise_error(data: PipelineData) -> PipelineData:
            raise RuntimeError("Test error")

        module._do_process = raise_error  # type: ignore
        module.start()

        data = PipelineData(chunk_index=0)
        result = module.process(data)

        # After all retries, module enters DEGRADED state (graceful degradation)
        assert module._state == ModuleState.DEGRADED
        assert module._error_message == "Test error"
        # Data should be returned unchanged
        assert result.chunk_index == 0

    def test_get_status(self) -> None:
        """Test get_status method."""
        module = TestModule("test")
        module.start()
        module.process(PipelineData(chunk_index=0))

        status = module.get_status()

        assert status.name == "test"
        assert status.state == ModuleState.RUNNING
        assert status.processed_chunks == 1

    def test_reset_error(self) -> None:
        """Test reset_error method."""
        module = TestModule("test")

        # Force error state
        module._state = ModuleState.ERROR
        module._error_message = "Some error"

        module.reset_error()

        assert module._state == ModuleState.RUNNING
        assert module._error_message is None

    def test_timing_tracking(self) -> None:
        """Test that processing time is tracked."""
        import time

        module = TestModule("test")
        module.start()

        # Small delay to ensure timing is measurable
        original_do_process = module._do_process

        def slow_process(data: PipelineData) -> PipelineData:
            time.sleep(0.01)
            return original_do_process(data)

        module._do_process = slow_process  # type: ignore

        data = PipelineData(chunk_index=0)
        module.process(data)

        assert module._last_process_time_ms >= 10

    def test_metadata_preserved(self) -> None:
        """Test that metadata is preserved through processing."""
        module1 = TestModule("mod1")
        module2 = TestModule("mod2")

        module1.start()
        module2.start()

        data = PipelineData(chunk_index=0)
        data.metadata["initial"] = "value"

        data = module1.process(data)
        data = module2.process(data)

        assert data.metadata["initial"] == "value"
        assert data.metadata["processed_by"] == "mod2"


class TestModuleState:
    """Tests for ModuleState enum."""

    def test_all_states(self) -> None:
        """Test all module states exist."""
        assert ModuleState.IDLE.value == "idle"
        assert ModuleState.STARTING.value == "starting"
        assert ModuleState.RUNNING.value == "running"
        assert ModuleState.STOPPING.value == "stopping"
        assert ModuleState.ERROR.value == "error"
        assert ModuleState.DISABLED.value == "disabled"
