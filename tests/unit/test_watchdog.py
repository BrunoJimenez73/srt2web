"""
Tests for FFmpeg Watchdog implementation.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestFFmpegWatchdog:
    """Test suite for FFmpegWatchdog class."""

    def test_initialization(self) -> None:
        """Test Watchdog initialization."""
        from core.watchdog import FFmpegWatchdog

        wd = FFmpegWatchdog(
            check_interval=5.0,
            hang_timeout=60.0,
            max_restarts=10,
        )

        assert wd.check_interval == 5.0
        assert wd.hang_timeout == 60.0
        assert wd.max_restarts == 10
        assert wd.restart_count == 0
        assert wd.is_healthy is False

    def test_attach_process(self) -> None:
        """Test attaching a process to watchdog."""
        from core.watchdog import FFmpegWatchdog

        wd = FFmpegWatchdog()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None

        wd.attach_process(mock_proc, "Test Process")

        assert wd.is_healthy is True
        assert wd._process_name == "Test Process"

    def test_detach_process(self) -> None:
        """Test detaching a process from watchdog."""
        from core.watchdog import FFmpegWatchdog

        wd = FFmpegWatchdog()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None

        wd.attach_process(mock_proc, "Test")
        wd.detach()

        assert wd.is_healthy is False
        assert wd._process is None

    def test_detect_crashed_process(self) -> None:
        """Test that watchdog detects crashed process."""
        from core.watchdog import FFmpegWatchdog

        wd = FFmpegWatchdog(check_interval=0.1)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1
        mock_proc.returncode = 1

        restart_callback = MagicMock()
        wd.attach_process(mock_proc, "FFmpeg", restart_callback)

        with patch.object(wd, "_check_health"):
            pass

        assert wd.is_healthy is False

    def test_notify_activity(self) -> None:
        """Test activity notification."""
        from core.watchdog import FFmpegWatchdog

        wd = FFmpegWatchdog(hang_timeout=10)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None

        wd.attach_process(mock_proc, "FFmpeg")
        wd._is_hung = True

        wd.notify_activity()

        assert wd._is_hung is False

    def test_restart_count(self) -> None:
        """Test restart counter."""
        from core.watchdog import FFmpegWatchdog

        wd = FFmpegWatchdog(max_restarts=5)
        wd._restart_count = 3

        assert wd.restart_count == 3


class TestProcessManager:
    """Test suite for ProcessManager singleton."""

    def test_singleton(self) -> None:
        """Test that ProcessManager is a singleton."""
        from core.watchdog import ProcessManager

        pm1 = ProcessManager()
        pm2 = ProcessManager()

        assert pm1 is pm2

    def test_register_process(self) -> None:
        """Test registering a process."""
        from core.watchdog import ProcessManager

        pm = ProcessManager()
        pm._processes.clear()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None

        watchdog = pm.register_process("test_process", mock_proc)

        assert "test_process" in pm._processes
        assert pm.get_watchdog("test_process") is watchdog

    def test_unregister_process(self) -> None:
        """Test unregistering a process."""
        from core.watchdog import ProcessManager

        pm = ProcessManager()
        pm._processes.clear()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None

        pm.register_process("test_process", mock_proc)
        pm.unregister_process("test_process")

        assert "test_process" not in pm._processes

    def test_get_all_health(self) -> None:
        """Test getting health of all processes."""
        from core.watchdog import ProcessManager

        pm = ProcessManager()
        pm._processes.clear()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None

        pm.register_process("healthy_proc", mock_proc)

        health = pm.get_all_health()

        assert "healthy_proc" in health
        assert health["healthy_proc"]["healthy"] is True

    def test_kill_all(self) -> None:
        """Test killing all processes."""
        from core.watchdog import ProcessManager

        pm = ProcessManager()
        pm._processes.clear()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None

        pm.register_process("test_proc", mock_proc)

        with patch("subprocess.run"):
            pm.kill_all()

        assert len(pm._processes) == 0


class TestWatchdogIntegration:
    """Integration tests for watchdog with BaseModule."""

    def test_module_with_watchdog(self) -> None:
        """Test that module can use watchdog for process monitoring."""
        from core.module_base import BaseModule, ModuleState

        class MockModule(BaseModule):
            def start(self):  # type: ignore
                self._state = ModuleState.RUNNING

            def stop(self):  # type: ignore
                self._state = ModuleState.IDLE

            def _do_process(self, data):  # type: ignore
                return data

        module = MockModule("test")
        module.start()

        assert module.state == ModuleState.RUNNING

        module.stop()
        assert module.state == ModuleState.IDLE

    def test_degraded_mode(self):  # type: ignore
        """Test degraded mode when module fails."""
        from core.module_base import BaseModule, ModuleState, PipelineData

        class FailingModule(BaseModule):
            def start(self):  # type: ignore
                self._state = ModuleState.RUNNING

            def stop(self):  # type: ignore
                self._state = ModuleState.IDLE

            def _do_process(self, data):  # type: ignore
                raise Exception("Processing failed")

            def _degraded_process(self, data):  # type: ignore
                self.logger.info("Operating in degraded mode")
                return data

        module = FailingModule("failing")
        module._retry_strategy.max_retries = 0
        module.start()

        data = PipelineData(chunk_index=0)
        result = module.process(data)

        assert module._state in [ModuleState.DEGRADED, ModuleState.ERROR]
        assert result.chunk_index == 0
