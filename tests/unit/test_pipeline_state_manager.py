"""
Tests for Pipeline State Manager.

Verifies state transitions, module tracking, callbacks,
and history management.
"""

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline_state_manager import (  # noqa: E402
    VALID_TRANSITIONS,
    ModuleState,
    ModuleStateInfo,
    PipelineState,
    PipelineStateManager,
    StateTransition,
)


class TestValidTransitions:
    """Test valid state transition table."""

    def test_idle_can_only_start(self):
        """From IDLE, can only transition to STARTING."""
        assert PipelineState.STARTING in VALID_TRANSITIONS[PipelineState.IDLE]
        assert PipelineState.RUNNING not in VALID_TRANSITIONS[PipelineState.IDLE]
        assert PipelineState.STOPPING not in VALID_TRANSITIONS[PipelineState.IDLE]

    def test_starting_can_reach_running_or_error(self):
        """From STARTING, can reach RUNNING, ERROR or back to IDLE."""
        allowed = VALID_TRANSITIONS[PipelineState.STARTING]
        assert PipelineState.RUNNING in allowed
        assert PipelineState.ERROR in allowed
        assert PipelineState.IDLE in allowed

    def test_running_can_stop_or_error(self):
        """From RUNNING, can transition to STOPPING or ERROR."""
        allowed = VALID_TRANSITIONS[PipelineState.RUNNING]
        assert PipelineState.STOPPING in allowed
        assert PipelineState.ERROR in allowed
        assert PipelineState.IDLE not in allowed

    def test_stopping_can_go_idle_or_error(self):
        """From STOPPING, can go to IDLE or ERROR."""
        allowed = VALID_TRANSITIONS[PipelineState.STOPPING]
        assert PipelineState.IDLE in allowed
        assert PipelineState.ERROR in allowed

    def test_error_can_go_idle_or_stopping(self):
        """From ERROR, can recover to IDLE or STOPPING."""
        allowed = VALID_TRANSITIONS[PipelineState.ERROR]
        assert PipelineState.IDLE in allowed
        assert PipelineState.STOPPING in allowed


class TestStateTransitions:
    """Test state transition logic."""

    def setup_method(self):
        self.manager = PipelineStateManager()

    def test_initial_state_is_idle(self):
        """Manager should start in IDLE state."""
        assert self.manager.state == PipelineState.IDLE
        assert self.manager.is_idle is True
        assert self.manager.is_running is False

    def test_valid_transition_idle_to_starting(self):
        """Should allow IDLE -> STARTING."""
        result = self.manager.transition_to(PipelineState.STARTING)
        assert result is True
        assert self.manager.state == PipelineState.STARTING

    def test_valid_transition_starting_to_running(self):
        """Should allow STARTING -> RUNNING."""
        self.manager.transition_to(PipelineState.STARTING)
        result = self.manager.transition_to(PipelineState.RUNNING)
        assert result is True
        assert self.manager.state == PipelineState.RUNNING
        assert self.manager.is_running is True

    def test_valid_transition_running_to_stopping(self):
        """Should allow RUNNING -> STOPPING."""
        self.manager.transition_to(PipelineState.STARTING)
        self.manager.transition_to(PipelineState.RUNNING)
        result = self.manager.transition_to(PipelineState.STOPPING)
        assert result is True
        assert self.manager.state == PipelineState.STOPPING

    def test_valid_transition_stopping_to_idle(self):
        """Should allow STOPPING -> IDLE."""
        self.manager.transition_to(PipelineState.STARTING)
        self.manager.transition_to(PipelineState.RUNNING)
        self.manager.transition_to(PipelineState.STOPPING)
        result = self.manager.transition_to(PipelineState.IDLE)
        assert result is True
        assert self.manager.state == PipelineState.IDLE

    def test_invalid_transition_idle_to_running(self):
        """Should NOT allow IDLE -> RUNNING directly."""
        result = self.manager.transition_to(PipelineState.RUNNING)
        assert result is False
        assert self.manager.state == PipelineState.IDLE

    def test_invalid_transition_idle_to_stopping(self):
        """Should NOT allow IDLE -> STOPPING."""
        result = self.manager.transition_to(PipelineState.STOPPING)
        assert result is False

    def test_invalid_transition_running_to_idle(self):
        """Should NOT allow RUNNING -> IDLE directly."""
        self.manager.transition_to(PipelineState.STARTING)
        self.manager.transition_to(PipelineState.RUNNING)
        result = self.manager.transition_to(PipelineState.IDLE)
        assert result is False

    def test_error_recovery(self):
        """Should allow recovery from ERROR to IDLE."""
        self.manager.transition_to(PipelineState.STARTING)
        self.manager.transition_to(PipelineState.ERROR)
        result = self.manager.transition_to(PipelineState.IDLE)
        assert result is True
        assert self.manager.state == PipelineState.IDLE

    def test_transition_with_reason(self):
        """Transition should record reason."""
        self.manager.transition_to(PipelineState.STARTING, reason="User started")
        history = self.manager.get_state_history()
        assert len(history) == 1
        assert history[0]["reason"] == "User started"


class TestModuleTracking:
    """Test module state tracking."""

    def setup_method(self):
        self.manager = PipelineStateManager()

    def test_register_module(self):
        """Should register module with default state."""
        self.manager.register_module("transcriber")
        info = self.manager.get_module_state("transcriber")
        assert info is not None
        assert info.state == ModuleState.IDLE
        assert info.enabled is True

    def test_register_module_disabled(self):
        """Should register module as disabled."""
        self.manager.register_module("tts_engine", enabled=False)
        info = self.manager.get_module_state("tts_engine")
        assert info.enabled is False

    def test_update_module_state(self):
        """Should update module state."""
        self.manager.register_module("transcriber")
        self.manager.update_module_state("transcriber", ModuleState.RUNNING, processed_chunks=5)
        info = self.manager.get_module_state("transcriber")
        assert info.state == ModuleState.RUNNING
        assert info.processed_chunks == 5

    def test_update_module_error(self):
        """Should track module errors."""
        self.manager.register_module("translator")
        self.manager.update_module_state("translator", ModuleState.ERROR, error="Connection failed")
        info = self.manager.get_module_state("translator")
        assert info.state == ModuleState.ERROR
        assert info.last_error == "Connection failed"

    def test_get_enabled_modules(self):
        """Should return only enabled modules."""
        self.manager.register_module("transcriber", enabled=True)
        self.manager.register_module("tts_engine", enabled=False)
        self.manager.register_module("translator", enabled=True)
        enabled = self.manager.get_enabled_modules()
        assert len(enabled) == 2
        assert "transcriber" in enabled
        assert "tts_engine" not in enabled
        assert "translator" in enabled

    def test_update_module_extra(self):
        """Should track extra module info."""
        self.manager.register_module("video_muxer")
        self.manager.update_module_state("video_muxer", ModuleState.RUNNING, extra={"using_gpu": True})
        info = self.manager.get_module_state("video_muxer")
        assert info.extra["using_gpu"] is True


class TestCallbacks:
    """Test state change callbacks."""

    def test_state_change_callback_invoked(self):
        """Callback should be invoked on state change."""
        transitions = []

        def callback(old_state, new_state, reason):
            transitions.append((old_state, new_state, reason))

        manager = PipelineStateManager()
        manager.set_callback(callback)
        manager.transition_to(PipelineState.STARTING, reason="Test")

        assert len(transitions) == 1
        assert transitions[0] == ("idle", "starting", "Test")

    def test_callback_not_called_on_invalid_transition(self):
        """Callback should NOT be invoked on invalid transition."""
        transitions = []

        def callback(old_state, new_state, reason):
            transitions.append((old_state, new_state, reason))

        manager = PipelineStateManager()
        manager.set_callback(callback)
        manager.transition_to(PipelineState.RUNNING)  # Invalid from IDLE

        assert len(transitions) == 0


class TestUptime:
    """Test uptime tracking."""

    def test_uptime_zero_when_not_started(self):
        """Uptime should be 0 when not started."""
        manager = PipelineStateManager()
        assert manager.uptime == 0.0

    def test_uptime_increases_when_running(self):
        """Uptime should track time since start."""
        manager = PipelineStateManager()
        manager.transition_to(PipelineState.STARTING)
        manager.transition_to(PipelineState.RUNNING)
        uptime = manager.uptime
        assert uptime >= 0.0


class TestStatusAndHistory:
    """Test status reporting and history."""

    def setup_method(self):
        self.manager = PipelineStateManager()

    def test_get_status(self):
        """Should return complete status dict."""
        self.manager.register_module("transcriber")
        self.manager.transition_to(PipelineState.STARTING)
        self.manager.transition_to(PipelineState.RUNNING)

        status = self.manager.get_status()
        assert status["state"] == "running"
        assert status["is_running"] is True
        assert status["module_count"] == 1
        assert status["enabled_modules"] == 1
        assert status["transitions"] == 2

    def test_get_state_history(self):
        """Should return history of transitions."""
        self.manager.transition_to(PipelineState.STARTING)
        self.manager.transition_to(PipelineState.RUNNING)
        self.manager.transition_to(PipelineState.STOPPING)
        self.manager.transition_to(PipelineState.IDLE)

        history = self.manager.get_state_history()
        assert len(history) == 4
        assert history[0]["from_state"] == "idle"
        assert history[0]["to_state"] == "starting"
        assert history[-1]["to_state"] == "idle"

    def test_history_limited_to_count(self):
        """Should limit history to requested count."""
        for _ in range(30):
            self.manager.transition_to(PipelineState.STARTING)
            self.manager.transition_to(PipelineState.IDLE)

        history = self.manager.get_state_history(count=5)
        assert len(history) <= 5

    def test_reset(self):
        """Reset should return to IDLE and clear module states."""
        self.manager.register_module("transcriber")
        self.manager.transition_to(PipelineState.STARTING)
        self.manager.transition_to(PipelineState.RUNNING)
        self.manager.update_module_state("transcriber", ModuleState.RUNNING)

        self.manager.reset()

        assert self.manager.state == PipelineState.IDLE
        assert self.manager.is_running is False
        module = self.manager.get_module_state("transcriber")
        assert module.state == ModuleState.IDLE

    def test_clear_history(self):
        """Clear history should remove all transitions."""
        self.manager.transition_to(PipelineState.STARTING)
        self.manager.transition_to(PipelineState.RUNNING)
        self.manager.clear_history()
        assert len(self.manager.get_state_history()) == 0


class TestStateTransitionDataclass:
    """Test StateTransition dataclass."""

    def test_to_dict(self):
        """Should serialize to dict."""
        t = StateTransition(
            timestamp=1234567890.0,
            from_state="idle",
            to_state="running",
            reason="test",
        )
        d = t.to_dict()
        assert d["from_state"] == "idle"
        assert d["to_state"] == "running"
        assert d["reason"] == "test"


class TestModuleStateInfoDataclass:
    """Test ModuleStateInfo dataclass."""

    def test_to_dict(self):
        """Should serialize to dict."""
        info = ModuleStateInfo(
            name="test",
            state=ModuleState.RUNNING,
            enabled=True,
            processed_chunks=10,
            extra={"gpu": True},
        )
        d = info.to_dict()
        assert d["name"] == "test"
        assert d["state"] == "running"
        assert d["enabled"] is True
        assert d["processed_chunks"] == 10
        assert d["extra"]["gpu"] is True
