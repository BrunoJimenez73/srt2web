"""
Tests for core.output_sink — OutputSink base class.

F165: Covers health tracking, stats, error handling, and the abstract contract.
"""

import time

import pytest

from core.module_base import ModuleState
from core.output_sink import HealthState, OutputSink


class ConcreteOutputSink(OutputSink):
    """Minimal concrete implementation for testing the abstract base."""

    def start(self):
        pass

    def stop(self):
        pass

    def write(self, data):
        self._update_write_stats(len(str(data)))


@pytest.mark.unit
class TestOutputSink:
    """Unit tests for OutputSink base class."""

    def test_init(self):
        sink = ConcreteOutputSink("test", {"enabled": True})
        assert sink.name == "test"
        assert sink._enabled is True

    def test_init_disabled(self):
        sink = ConcreteOutputSink("test", {"enabled": False})
        assert sink._enabled is False

    def test_health_check_healthy_by_default(self):
        sink = ConcreteOutputSink("test", {})
        sink._last_write_time = time.time()
        assert sink.health_check() == HealthState.HEALTHY

    def test_health_check_degraded_when_no_recent_write(self):
        sink = ConcreteOutputSink("test", {})
        sink._last_write_time = time.time() - 60
        assert sink.health_check() == HealthState.DEGRADED

    def test_health_check_failed_on_error(self):
        sink = ConcreteOutputSink("test", {})
        sink._last_write_time = time.time()
        sink._set_error("something broke")
        assert sink.health_check() == HealthState.FAILED

    def test_set_and_clear_error(self):
        sink = ConcreteOutputSink("test", {})
        sink._set_error("error msg")
        assert sink._last_error == "error msg"
        assert sink._last_error_time is not None
        sink._clear_error()
        assert sink._last_error is None
        assert sink._last_error_time is None

    def test_update_write_stats(self):
        sink = ConcreteOutputSink("test", {})
        sink.write("hello")
        assert sink._bytes_written == 5
        assert sink._last_write_time > 0

    def test_update_write_stats_clears_error(self):
        sink = ConcreteOutputSink("test", {})
        sink._set_error("old error")
        sink.write("data")
        assert sink._last_error is None

    def test_get_status(self):
        sink = ConcreteOutputSink("test", {})
        status = sink.get_status()
        assert status.name == "test"
        assert status.state == ModuleState.IDLE
        assert status.enabled is True

    def test_set_output_dir(self):
        sink = ConcreteOutputSink("test", {})
        sink.set_output_dir("/tmp/output")
        assert sink._output_dir == "/tmp/output"

    def test_configure(self):
        sink = ConcreteOutputSink("test", {})
        sink.configure({"new_key": "value"})
        assert sink.config == {"new_key": "value"}

    def test_get_stream_info(self):
        sink = ConcreteOutputSink("test", {})
        info = sink.get_stream_info()
        assert info == {"type": "test"}

    def test_check_health_emits_event_on_change(self):
        sink = ConcreteOutputSink("test", {})
        sink._last_write_time = time.time()
        sink.check_health()
        assert sink._health_state == HealthState.HEALTHY
        sink._last_write_time = time.time() - 60
        sink.check_health()
        assert sink._health_state == HealthState.DEGRADED
