"""
F107 — Pipeline init timeout deja state colgado en 'starting'.

Regression tests covering:
- Timeout transitions state STARTING -> ERROR (not stuck in STARTING).
- Real exceptions inside init thread are surfaced (not masked as 'timed out').
- After timeout sets ERROR, the API reset_error_state() + retry path works.
- SRT2WEB_PIPELINE_INIT_TIMEOUT env var overrides the default.
- Concurrent start() while an init thread is alive is rejected cleanly.
- Already-initialized pipelines skip the init thread entirely.
- Default timeout is the documented value (300s).
- Happy path through start() still works.
"""

from __future__ import annotations

import contextlib
import time

import pytest

from core.exceptions import PipelineError
from core.module_base import BaseModule, ModuleState, PipelineData
from core.unified_pipeline import (
    _DEFAULT_INIT_TIMEOUT_S,
    PipelineState,
    UnifiedPipeline,
    _get_init_timeout,
)


class _DummyModule(BaseModule):
    def __init__(self, name: str = "dummy", config: dict | None = None) -> None:
        super().__init__(name, config)

    def start(self) -> None:  # type: ignore[override]
        self._state = ModuleState.RUNNING

    def stop(self) -> None:  # type: ignore[override]
        self._state = ModuleState.IDLE

    def _do_process(self, data: PipelineData) -> PipelineData:
        return data


def _drain_state(pipeline: UnifiedPipeline) -> None:
    """Stop pipeline best-effort to avoid leaking background workers."""
    with contextlib.suppress(Exception):
        pipeline._stop_event.set()


class TestInitTimeoutEnv:
    """SRT2WEB_PIPELINE_INIT_TIMEOUT env var contract."""

    def test_default_is_300_seconds(self) -> None:
        assert _DEFAULT_INIT_TIMEOUT_S == 300.0

    def test_env_override_used(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SRT2WEB_PIPELINE_INIT_TIMEOUT", "12.5")
        assert _get_init_timeout() == 12.5

    def test_env_invalid_falls_back_to_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SRT2WEB_PIPELINE_INIT_TIMEOUT", "not-a-number")
        assert _get_init_timeout() == _DEFAULT_INIT_TIMEOUT_S

    def test_env_zero_or_negative_falls_back_to_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SRT2WEB_PIPELINE_INIT_TIMEOUT", "0")
        assert _get_init_timeout() == _DEFAULT_INIT_TIMEOUT_S
        monkeypatch.setenv("SRT2WEB_PIPELINE_INIT_TIMEOUT", "-5")
        assert _get_init_timeout() == _DEFAULT_INIT_TIMEOUT_S


class TestInitTimeoutResetsState:
    """When init exceeds timeout, state must move STARTING -> ERROR (never stay STARTING)."""

    def test_timeout_sets_state_to_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SRT2WEB_PIPELINE_INIT_TIMEOUT", "0.3")
        pipeline = UnifiedPipeline()

        async def slow_init() -> None:
            time.sleep(2.0)  # blocks longer than 0.3s timeout

        pipeline.initialize = slow_init  # type: ignore[assignment]

        with pytest.raises(PipelineError) as exc:
            pipeline.start()

        assert "timed out" in str(exc.value).lower()
        assert "0" in str(exc.value)  # message includes the actual timeout value (0s rounded)
        assert pipeline.state == PipelineState.ERROR, (
            f"State leaked: expected ERROR, got {pipeline.state.value!r} "
            "— this is the F107 regression that left state stuck in STARTING."
        )
        _drain_state(pipeline)

    def test_after_timeout_retry_works_via_reset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """API flow: route detects ERROR, calls reset_error_state(), then start() should succeed."""
        monkeypatch.setenv("SRT2WEB_PIPELINE_INIT_TIMEOUT", "0.2")
        pipeline = UnifiedPipeline()
        pipeline.register_module(_DummyModule("m1"))

        # First attempt: slow init -> timeout -> ERROR
        async def slow_init() -> None:
            time.sleep(1.5)

        pipeline.initialize = slow_init  # type: ignore[assignment]
        with pytest.raises(PipelineError):
            pipeline.start()
        assert pipeline.state == PipelineState.ERROR

        # Wait for background init thread to finish so retry can spawn a fresh one
        assert pipeline._init_thread is not None
        pipeline._init_thread.join(timeout=3.0)

        # Mirror what server/routes/pipeline.py:117-122 does on retry
        pipeline.reset_error_state()
        assert pipeline.state == PipelineState.IDLE

        # Second attempt: fast init -> success
        async def fast_init() -> None:
            return None

        pipeline.initialize = fast_init  # type: ignore[assignment]
        pipeline.start()
        # State should be RUNNING (or transitioning toward it)
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if pipeline.state == PipelineState.RUNNING:
                break
            time.sleep(0.05)
        assert pipeline.state == PipelineState.RUNNING
        _drain_state(pipeline)


class TestInitExceptionSurfaced:
    """When initialize() raises inside the thread, the real error must propagate."""

    def test_init_exception_is_reraised_not_swallowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SRT2WEB_PIPELINE_INIT_TIMEOUT", "5")
        pipeline = UnifiedPipeline()

        async def broken_init() -> None:
            raise RuntimeError("BOOM: model file not found")

        pipeline.initialize = broken_init  # type: ignore[assignment]

        with pytest.raises(PipelineError) as exc:
            pipeline.start()

        # The user must see the real cause, not a misleading 'timeout' message
        assert "timed out" not in str(exc.value).lower()
        assert "BOOM" in str(exc.value) or "BOOM" in str(exc.value.__cause__)
        assert isinstance(exc.value.__cause__, RuntimeError)
        assert pipeline.state == PipelineState.ERROR

    def test_init_exception_clears_internal_error_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_init_error must be cleared after being surfaced so retries get fresh capture."""
        monkeypatch.setenv("SRT2WEB_PIPELINE_INIT_TIMEOUT", "5")
        pipeline = UnifiedPipeline()

        async def broken_init() -> None:
            raise ValueError("first failure")

        pipeline.initialize = broken_init  # type: ignore[assignment]

        with pytest.raises(PipelineError):
            pipeline.start()

        assert pipeline._init_error is None, "Stale _init_error would mask a subsequent retry's real outcome"


class TestConcurrentInitRejection:
    """A second start() while an init thread is still alive must reject cleanly."""

    def test_second_start_while_init_in_progress_rejects(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SRT2WEB_PIPELINE_INIT_TIMEOUT", "0.2")
        pipeline = UnifiedPipeline()

        async def slow_init() -> None:
            time.sleep(1.0)

        pipeline.initialize = slow_init  # type: ignore[assignment]

        # First call: times out -> ERROR. Background thread still alive.
        with pytest.raises(PipelineError):
            pipeline.start()
        assert pipeline.state == PipelineState.ERROR
        assert pipeline._init_thread is not None
        assert pipeline._init_thread.is_alive()

        # Mirror the route's reset before retry
        pipeline.reset_error_state()

        # Second call while bg init is STILL alive must NOT spawn a duplicate
        with pytest.raises(PipelineError) as exc:
            pipeline.start()
        assert "already in progress" in str(exc.value).lower()
        assert pipeline.state == PipelineState.ERROR

        # Cleanup: wait for bg thread
        pipeline._init_thread.join(timeout=3.0)
        _drain_state(pipeline)


class TestAlreadyInitializedSkipsThread:
    """If _initialized is already True, start() must not spawn an init thread."""

    def test_initialized_true_skips_init(self) -> None:
        pipeline = UnifiedPipeline()
        pipeline.register_module(_DummyModule("m1"))
        # Pretend init already happened
        pipeline._initialized = True
        pipeline._chunk_queue.queue.clear()  # ensure queues are ready
        # Don't replace initialize() — if start() were to call it, the real (heavy) initialize
        # would run. We assert no thread is created.
        assert pipeline._init_thread is None

        pipeline.start()
        assert pipeline._init_thread is None, "start() spawned an init thread despite _initialized=True"
        # State eventually goes RUNNING
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if pipeline.state == PipelineState.RUNNING:
                break
            time.sleep(0.05)
        assert pipeline.state == PipelineState.RUNNING
        _drain_state(pipeline)


class TestHappyPath:
    """Sanity: fast init still works end-to-end."""

    def test_fast_init_reaches_running(self) -> None:
        pipeline = UnifiedPipeline()
        pipeline.register_module(_DummyModule("m1"))

        async def fast_init() -> None:
            return None

        pipeline.initialize = fast_init  # type: ignore[assignment]
        pipeline.start()
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if pipeline.state == PipelineState.RUNNING:
                break
            time.sleep(0.05)
        assert pipeline.state == PipelineState.RUNNING
        assert pipeline._initialized is True
        assert pipeline._init_error is None
        _drain_state(pipeline)
