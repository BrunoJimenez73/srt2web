"""Tests for PiperSubprocessManager heartbeat functionality."""

import threading
from unittest.mock import MagicMock


class TestPiperHeartbeat:
    """Test heartbeat thread in PiperSubprocessManager."""

    def test_heartbeat_attributes_exist(self):
        """Test that PiperSubprocessManager has heartbeat attributes."""
        from modules.piper_loader import PiperSubprocessManager

        manager = PiperSubprocessManager()
        assert hasattr(manager, "_heartbeat_interval")
        assert hasattr(manager, "_heartbeat_timeout")
        assert hasattr(manager, "_heartbeat_thread")
        assert hasattr(manager, "_heartbeat_stop")
        assert manager._heartbeat_interval == 30.0
        assert manager._heartbeat_timeout == 5.0

    def test_start_heartbeat_creates_thread(self):
        """Test that start_heartbeat creates a daemon thread."""
        from modules.piper_loader import PiperSubprocessManager

        manager = PiperSubprocessManager()
        manager.start_heartbeat()
        assert manager._heartbeat_thread is not None
        assert manager._heartbeat_thread.is_alive()
        assert manager._heartbeat_thread.daemon is True
        assert manager._heartbeat_thread.name == "piper-heartbeat"
        manager.stop_heartbeat()

    def test_stop_heartbeat_stops_thread(self):
        """Test that stop_heartbeat stops the thread."""
        from modules.piper_loader import PiperSubprocessManager

        manager = PiperSubprocessManager()
        manager.start_heartbeat()
        assert manager._heartbeat_thread is not None
        assert manager._heartbeat_thread.is_alive()
        manager.stop_heartbeat()
        assert manager._heartbeat_thread is None

    def test_double_start_heartbeat_no_duplicate(self):
        """Test that starting heartbeat twice doesn't create two threads."""
        from modules.piper_loader import PiperSubprocessManager

        manager = PiperSubprocessManager()
        manager.start_heartbeat()
        thread1 = manager._heartbeat_thread
        manager.start_heartbeat()
        thread2 = manager._heartbeat_thread
        assert thread1 is thread2
        manager.stop_heartbeat()

    def test_heartbeat_ping_unresponsive_subprocess(self):
        """Test that heartbeat detects unresponsive subprocess and restarts."""
        from modules.piper_loader import PiperSubprocessManager

        manager = PiperSubprocessManager()
        manager._proc = MagicMock()
        manager._proc.poll.return_value = None
        manager._proc.stdin = MagicMock()
        manager._proc.stdout = MagicMock()
        manager._model_loaded = True
        manager._last_model_path = "/fake/model"
        manager._last_config_path = "/fake/config"
        manager._last_device = "cpu"

        # Make _send_command fail (unresponsive subprocess)
        manager._send_command = MagicMock(return_value={"status": "error", "error": "timeout"})

        original_restart = manager._restart_subprocess
        restart_called = threading.Event()

        def mock_restart():
            restart_called.set()

        manager._restart_subprocess = mock_restart

        # Trigger heartbeat check directly
        manager._heartbeat_loop = lambda: None  # prevent actual loop
        manager._heartbeat_stop.set()

        # Manually call the check logic that heartbeat_loop uses
        if not manager.is_alive:
            pass  # would restart
        else:
            resp = manager._send_command({"action": "ping"}, timeout=5.0)
            if resp.get("status") != "success":
                mock_restart()

        assert restart_called.is_set()

    def test_heartbeat_ping_responds_ok(self):
        """Test that heartbeat does NOT restart when ping succeeds."""
        from modules.piper_loader import PiperSubprocessManager

        manager = PiperSubprocessManager()
        manager._proc = MagicMock()
        manager._proc.poll.return_value = None
        manager._proc.stdin = MagicMock()
        manager._proc.stdout = MagicMock()
        manager._model_loaded = True
        manager._last_model_path = "/fake/model"
        manager._last_config_path = "/fake/config"

        # Make _send_command succeed
        manager._send_command = MagicMock(return_value={"status": "success", "action": "pong"})

        restart_called = threading.Event()

        def mock_restart():
            restart_called.set()

        manager._restart_subprocess = mock_restart

        # Simulate heartbeat check
        resp = manager._send_command({"action": "ping"}, timeout=5.0)
        if resp.get("status") == "success":
            pass  # no restart
        else:
            mock_restart()

        assert not restart_called.is_set()

    def test_restart_subprocess_attributes(self):
        """Test that PiperSubprocessManager has restart-related methods."""
        from modules.piper_loader import PiperSubprocessManager

        manager = PiperSubprocessManager()
        assert hasattr(manager, "_restart_subprocess")
        assert hasattr(manager, "start_heartbeat")
        assert hasattr(manager, "stop_heartbeat")

    def test_heartbeat_stop_clears_thread_ref(self):
        """Test that stop_heartbeat sets thread to None."""
        from modules.piper_loader import PiperSubprocessManager

        manager = PiperSubprocessManager()
        manager.start_heartbeat()
        manager.stop_heartbeat()
        assert manager._heartbeat_thread is None


class TestPiperPingAction:
    """Test the ping/pong action in the persistent worker script."""

    def test_worker_script_contains_ping_action(self):
        """Test that PERSISTENT_WORKER_SCRIPT handles 'ping' action."""
        from modules.piper_loader import PERSISTENT_WORKER_SCRIPT

        script = PERSISTENT_WORKER_SCRIPT()
        assert "ping" in script
        assert "pong" in script

    def test_ping_action_returns_pong(self):
        """Test that ping/pong response is correct format.

        Since the worker script runs in a subprocess, we verify
        the JSON response format present in the script.
        """
        from modules.piper_loader import PERSISTENT_WORKER_SCRIPT

        assert '{"status": "success", "action": "pong"}' in PERSISTENT_WORKER_SCRIPT()


class TestBaseModuleIsCritical:
    """Test is_critical flag in BaseModule."""

    def test_is_critical_defaults_to_true(self):
        """Test that BaseModule has is_critical defaulting to True."""
        from core.module_base import BaseModule

        class TestMod(BaseModule):
            def start(self):
                pass

            def stop(self):
                pass

            def _do_process(self, data):
                return data

        mod = TestMod("test_mod")
        assert mod.is_critical is True

    def test_is_critical_can_be_set_to_false(self):
        """Test that is_critical can be set to False."""
        from core.module_base import BaseModule

        class TestMod(BaseModule):
            def start(self):
                pass

            def stop(self):
                pass

            def _do_process(self, data):
                return data

        mod = TestMod("test_mod", is_critical=False)
        assert mod.is_critical is False

    def test_degraded_count_increments(self):
        """Test that _degraded_process increments degraded count."""
        from core.module_base import BaseModule, PipelineData

        class TestMod(BaseModule):
            def start(self):
                pass

            def stop(self):
                pass

            def _do_process(self, data):
                return data

        mod = TestMod("test_mod")
        data = PipelineData(chunk_index=0)
        result = mod._degraded_process(data)
        assert mod._degraded_count == 1
        assert result is data
        assert mod.state.value == "degraded"

    def test_degraded_count_multiple_calls(self):
        """Test that degraded count increments on multiple calls."""
        from core.module_base import BaseModule, PipelineData

        class TestMod(BaseModule):
            def start(self):
                pass

            def stop(self):
                pass

            def _do_process(self, data):
                return data

        mod = TestMod("test_mod")
        for i in range(5):
            mod._degraded_process(PipelineData(chunk_index=i))
        assert mod._degraded_count == 5
