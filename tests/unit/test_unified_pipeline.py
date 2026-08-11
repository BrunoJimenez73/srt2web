"""
Unit tests for UnifiedPipeline — register, get_status, reconfigure.
"""

import inspect
import textwrap
from unittest.mock import MagicMock

from core.module_base import BaseModule, ModuleState, PipelineData
from core.unified_pipeline import UnifiedPipeline as Pipeline


class DummyModule(BaseModule):
    """A dummy module for testing."""

    def __init__(self, name: str = "dummy", config: dict | None = None):
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


class TestUnifiedPipelineRegister:
    """Tests for pipeline module registration."""

    def test_register_module(self):
        pipeline = Pipeline()
        module = DummyModule("test_module")
        pipeline.register_module(module)

        assert len(pipeline.get_modules()) == 1
        assert pipeline.get_module("test_module") is module

    def test_register_multiple_modules(self):
        pipeline = Pipeline()
        pipeline.register_module(DummyModule("mod1"))
        pipeline.register_module(DummyModule("mod2"))
        pipeline.register_module(DummyModule("mod3"))

        assert len(pipeline.get_modules()) == 3

    def test_register_module_with_config(self):
        pipeline = Pipeline()
        module = DummyModule("cfg_module")
        pipeline.register_module(module, config={"enabled": False})

        assert module.enabled is False

    def test_get_module_not_found(self):
        pipeline = Pipeline()
        assert pipeline.get_module("nonexistent") is None

    def test_get_modules_returns_copy_or_list(self):
        pipeline = Pipeline()
        pipeline.register_module(DummyModule("m1"))
        modules = pipeline.get_modules()
        assert len(modules) == 1
        assert modules[0].name == "m1"


class TestUnifiedPipelineGetStatus:
    """Tests for pipeline get_status."""

    def test_get_status_idle(self):
        pipeline = Pipeline()
        status = pipeline.get_status()

        assert status["state"] == "idle"
        assert "modules" in status
        assert "system" in status or "system_metrics" in status

    def test_get_status_contains_required_keys(self):
        pipeline = Pipeline()
        status = pipeline.get_status()

        assert "state" in status
        assert "mode" in status
        assert "chunks_processed" in status
        assert "chunks_failed" in status
        assert "avg_processing_time_ms" in status
        assert "uptime_seconds" in status
        assert "modules" in status

    def test_get_status_includes_registered_modules(self):
        pipeline = Pipeline()
        pipeline.register_module(DummyModule("test_mod"))

        status = pipeline.get_status()
        module_names = [m.get("name") for m in status["modules"]]
        assert "test_mod" in module_names

    def test_get_status_mode_default(self):
        pipeline = Pipeline()
        status = pipeline.get_status()
        assert status["mode"] == "thread_parallel"


class TestUnifiedPipelineReconfigure:
    """Tests for pipeline reconfigure."""

    def test_reconfigure_updates_chunk_duration(self):
        pipeline = Pipeline()

        config = MagicMock()
        config.get.return_value = 15
        config.get_module_config.return_value = {}

        pipeline._chunk_duration = 5
        pipeline.reconfigure(config)

        assert pipeline._chunk_duration == 15

    def test_reconfigure_calls_module_configure(self):
        pipeline = Pipeline()
        module = DummyModule("cfg_test")
        pipeline.register_module(module)

        config = MagicMock()
        config.get.return_value = 10
        config.get_module_config.return_value = {"enabled": False}

        pipeline.reconfigure(config)

        assert module.enabled is False


class TestPipelineData:
    """Tests for PipelineData attributes."""

    def test_pipeline_data_defaults(self):
        data = PipelineData(chunk_index=0)
        assert data.chunk_index == 0
        assert data.metadata == {}
        assert data.video_chunk_path is None

    def test_pipeline_data_with_fields(self):
        data = PipelineData(
            chunk_index=5,
            video_chunk_path="/tmp/test.ts",
            duration=10.0,
            metadata={"source": "test"},
        )
        assert data.chunk_index == 5
        assert data.video_chunk_path == "/tmp/test.ts"
        assert data.duration == 10.0
        assert data.metadata["source"] == "test"


class TestF127InitializedSingleAssignment:
    """F127 — _initialized debe asignarse exactamente una vez en __init__.

    La primera asignación (al inicio de __init__, antes de cualquier otro
    atributo) es la que protege contra race conditions. Una segunda
    asignación más tarde en __init__ anularía esa protección reabriendo
    una ventana donde el flag es False de nuevo.
    """

    def test_initialized_is_false_after_construction(self):
        """_initialized es False justo después de __init__, nunca True."""
        pipeline = Pipeline()
        assert pipeline._initialized is False

    def test_initialized_not_reassigned_in_init(self):
        """__init__ debe contener exactamente una asignación a _initialized."""
        src = inspect.getsource(Pipeline.__init__)
        lines = textwrap.dedent(src).splitlines()
        assignments = [ln for ln in lines if "self._initialized =" in ln and not ln.lstrip().startswith("#")]
        assert len(assignments) == 1, (
            f"Se esperaba exactamente 1 asignación a self._initialized en __init__, "
            f"se encontraron {len(assignments)}: {assignments}"
        )
