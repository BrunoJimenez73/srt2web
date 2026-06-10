"""
F115: Tests for core.chunk_clock.ChunkClock.

Covers:
  - Constructor validation (chunk_duration, clamp bounds)
  - First chunk: no drift correction
  - Sequential chunks: nominal duration -> linear cumulative
  - Drift accumulation: small positive deltas add up
  - Clamping upper bound: jumps > max_delta_multiplier*chunk_duration are capped
  - Clamping lower bound: tiny deltas < min_delta_s pull cumulative backward
  - Negative deltas (clock went backward): pulled to min
  - Reset clears state
  - update_chunk_duration: returns True on change, resets cumulative,
    does NOT reset on no-op
  - Property accessors (chunk_duration, cumulative, has_previous_mtime)
  - Real file mtimes via os.utime to control timing exactly
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.chunk_clock import (
    DEFAULT_MAX_DELTA_MULTIPLIER,
    DEFAULT_MIN_DELTA_S,
    ChunkClock,
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _touch_with_mtime(path: Path, mtime: float) -> float:
    """Create file with explicit mtime, return that mtime."""
    path.write_text("x")
    os.utime(path, (mtime, mtime))
    return path.stat().st_mtime


# -----------------------------------------------------------------------------
# Constructor
# -----------------------------------------------------------------------------


class TestChunkClockConstructor:
    def test_basic_construction(self) -> None:
        c = ChunkClock(chunk_duration=10.0)
        assert c.chunk_duration == 10.0
        assert c.cumulative == 0.0
        assert c.has_previous_mtime is False

    def test_invalid_chunk_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="chunk_duration must be > 0"):
            ChunkClock(chunk_duration=0)
        with pytest.raises(ValueError, match="chunk_duration must be > 0"):
            ChunkClock(chunk_duration=-5.0)

    def test_invalid_min_delta_raises(self) -> None:
        with pytest.raises(ValueError, match="min_delta_s must be >= 0"):
            ChunkClock(chunk_duration=10.0, min_delta_s=-1.0)

    def test_invalid_max_delta_multiplier_raises(self) -> None:
        with pytest.raises(ValueError, match=r"max_delta_multiplier must be >= 1\.0"):
            ChunkClock(chunk_duration=10.0, max_delta_multiplier=0.5)

    def test_constants_exposed(self) -> None:
        assert DEFAULT_MIN_DELTA_S == 0.5
        assert DEFAULT_MAX_DELTA_MULTIPLIER == 2.0


# -----------------------------------------------------------------------------
# First chunk
# -----------------------------------------------------------------------------


class TestChunkClockFirstChunk:
    def test_first_chunk_returns_zero(self) -> None:
        c = ChunkClock(chunk_duration=10.0)
        assert c.record_mtime(1000.0) == 0.0
        # Internal state advances by chunk_duration for next call
        assert c.cumulative == 10.0
        assert c.has_previous_mtime is True

    def test_first_chunk_ignores_mtime_value(self) -> None:
        """No drift correction on first chunk regardless of mtime magnitude."""
        c = ChunkClock(chunk_duration=10.0)
        # First call always returns 0.0
        assert c.record_mtime(0.0) == 0.0
        c.reset()
        assert c.record_mtime(1e15) == 0.0
        c.reset()
        assert c.record_mtime(-100.0) == 0.0


# -----------------------------------------------------------------------------
# Sequential chunks
# -----------------------------------------------------------------------------


class TestChunkClockSequentialChunks:
    def test_nominal_chunks_are_linear(self) -> None:
        """If chunks arrive exactly every `chunk_duration` seconds, cumulative is linear."""
        c = ChunkClock(chunk_duration=10.0)
        assert c.record_mtime(1000.0) == pytest.approx(0.0)
        assert c.record_mtime(1010.0) == pytest.approx(10.0)
        assert c.record_mtime(1020.0) == pytest.approx(20.0)
        assert c.record_mtime(1030.0) == pytest.approx(30.0)
        assert c.cumulative == 40.0

    def test_drift_accumulates(self) -> None:
        """A consistent 0.5s extra per chunk adds up."""
        c = ChunkClock(chunk_duration=10.0)
        c.record_mtime(1000.0)
        # 10.5s delta -> correction +0.5
        assert c.record_mtime(1010.5) == pytest.approx(10.5)
        # cumulative becomes 20.5; next delta 10.5 -> correction +0.5
        assert c.record_mtime(1021.0) == pytest.approx(21.0)
        assert c.record_mtime(1031.5) == pytest.approx(31.5)


# -----------------------------------------------------------------------------
# Clamping
# -----------------------------------------------------------------------------


class TestChunkClockClamping:
    def test_upper_clamp_default(self) -> None:
        """A 60s gap with chunk_duration=10 should clamp to 20s (2x default)."""
        c = ChunkClock(chunk_duration=10.0)
        c.record_mtime(1000.0)
        # delta = 60, clamped to 20, correction = 20 - 10 = +10
        # cumulative = 10 + 10 = 20, snapshot = 20
        cum = c.record_mtime(1060.0)
        assert cum == pytest.approx(20.0)
        assert c.cumulative == 30.0  # 20 + 10

    def test_upper_clamp_custom_multiplier(self) -> None:
        c = ChunkClock(chunk_duration=5.0, max_delta_multiplier=3.0)
        c.record_mtime(1000.0)
        # 100s gap -> clamp to 15s
        # correction = 15 - 5 = +10, cumulative = 5 + 10 = 15, snapshot = 15
        cum = c.record_mtime(1100.0)
        assert cum == pytest.approx(15.0)

    def test_lower_clamp_pulls_backward(self) -> None:
        """A 0.1s gap (below min) -> correction = 0.5 - 10 = -9.5"""
        c = ChunkClock(chunk_duration=10.0)
        c.record_mtime(1000.0)
        # delta = 0.1, clamped to 0.5
        # cumulative = 10 + (0.5 - 10) = 0.5
        # snapshot = 0.5
        cum = c.record_mtime(1000.1)
        assert cum == pytest.approx(0.5)
        assert c.cumulative == pytest.approx(10.5)  # 0.5 + 10

    def test_lower_clamp_zero_delta(self) -> None:
        """Same mtime twice in a row: delta=0, clamped to min."""
        c = ChunkClock(chunk_duration=10.0)
        c.record_mtime(1000.0)
        # delta = 0, clamped to 0.5
        # cumulative was 10, after correction: 10 + (0.5 - 10) = 0.5
        # snapshot = 0.5
        assert c.record_mtime(1000.0) == pytest.approx(0.5)
        # next: cumulative 0.5 + 10 = 10.5, then correction 0.5 - 10 = -9.5
        # new cumulative = 10.5 - 9.5 = 1.0, snapshot = 1.0
        assert c.record_mtime(1000.0) == pytest.approx(1.0)
        # next: cumulative 1.0 + 10 = 11.0, then -9.5 = 1.5, snapshot = 1.5
        assert c.record_mtime(1000.0) == pytest.approx(1.5)

    def test_negative_delta_clamped_to_min(self) -> None:
        """Clock going backward: delta is negative, clamp raises to min."""
        c = ChunkClock(chunk_duration=10.0)
        c.record_mtime(1000.0)
        # Clock went backward by 5s: raw_delta = -5, clamped to 0.5
        # correction = 0.5 - 10 = -9.5
        # cumulative = 10 - 9.5 = 0.5, snapshot = 0.5
        cum = c.record_mtime(995.0)
        assert cum == pytest.approx(0.5)


# -----------------------------------------------------------------------------
# Reset
# -----------------------------------------------------------------------------


class TestChunkClockReset:
    def test_reset_clears_state(self) -> None:
        c = ChunkClock(chunk_duration=10.0)
        c.record_mtime(1000.0)
        c.record_mtime(1010.0)
        assert c.cumulative == 20.0
        assert c.has_previous_mtime is True

        c.reset()
        assert c.cumulative == 0.0
        assert c.has_previous_mtime is False
        # Next call should be treated as a first chunk
        assert c.record_mtime(2000.0) == 0.0

    def test_reset_does_not_change_chunk_duration(self) -> None:
        c = ChunkClock(chunk_duration=10.0)
        c.reset()
        assert c.chunk_duration == 10.0

    def test_reset_idempotent(self) -> None:
        c = ChunkClock(chunk_duration=10.0)
        c.reset()
        c.reset()
        c.reset()
        assert c.cumulative == 0.0


# -----------------------------------------------------------------------------
# update_chunk_duration
# -----------------------------------------------------------------------------


class TestUpdateChunkDuration:
    def test_no_op_returns_false(self) -> None:
        c = ChunkClock(chunk_duration=10.0)
        assert c.update_chunk_duration(10.0) is False
        assert c.update_chunk_duration(10) is False  # int == float

    def test_change_returns_true_and_resets(self) -> None:
        c = ChunkClock(chunk_duration=10.0)
        c.record_mtime(1000.0)
        c.record_mtime(1010.0)
        assert c.cumulative == 20.0
        assert c.has_previous_mtime is True

        changed = c.update_chunk_duration(15.0)
        assert changed is True
        assert c.chunk_duration == 15.0
        assert c.cumulative == 0.0
        assert c.has_previous_mtime is False

    def test_invalid_new_duration_raises(self) -> None:
        c = ChunkClock(chunk_duration=10.0)
        with pytest.raises(ValueError, match="new_duration must be > 0"):
            c.update_chunk_duration(0)
        with pytest.raises(ValueError, match="new_duration must be > 0"):
            c.update_chunk_duration(-1.0)

    def test_after_change_uses_new_clamp_bounds(self) -> None:
        """After update_chunk_duration, the new bounds apply to subsequent calls."""
        c = ChunkClock(chunk_duration=10.0)
        c.update_chunk_duration(5.0)  # change to 5s
        c.record_mtime(1000.0)
        # Delta of 8s: within [0.5, 2*5=10], no clamp
        # correction = 8 - 5 = +3, cumulative = 5 + 3 = 8, snapshot = 8
        cum = c.record_mtime(1008.0)
        assert cum == pytest.approx(8.0)


# -----------------------------------------------------------------------------
# Property accessors
# -----------------------------------------------------------------------------


class TestPropertyAccessors:
    def test_cumulative_reflects_state(self) -> None:
        c = ChunkClock(chunk_duration=10.0)
        assert c.cumulative == 0.0
        c.record_mtime(1000.0)
        assert c.cumulative == 10.0
        c.record_mtime(1010.0)
        assert c.cumulative == 20.0

    def test_has_previous_mtime(self) -> None:
        c = ChunkClock(chunk_duration=10.0)
        assert c.has_previous_mtime is False
        c.record_mtime(1000.0)
        assert c.has_previous_mtime is True
        c.reset()
        assert c.has_previous_mtime is False


# -----------------------------------------------------------------------------
# Real files via os.utime
# -----------------------------------------------------------------------------


class TestChunkClockWithRealFiles:
    """Integration: ChunkClock fed from real file mtimes."""

    def test_5_chunks_at_10s_each(self, tmp_path: Path) -> None:
        """5 chunks of 10s each, written 10s apart via os.utime."""
        c = ChunkClock(chunk_duration=10.0)
        base = 1_700_000_000.0  # arbitrary epoch
        for i in range(5):
            p = tmp_path / f"chunk_{i:06d}.ts"
            _touch_with_mtime(p, base + i * 10)
            cum = c.record_mtime(p.stat().st_mtime)
            assert cum == pytest.approx(10.0 * i), f"chunk {i}: cum={cum}"

    def test_drift_accumulation_via_files(self, tmp_path: Path) -> None:
        """Chunks 0.1s apart — should clamp to min, pulling cumulative backward."""
        c = ChunkClock(chunk_duration=10.0)
        base = 1_700_000_000.0
        for i in range(4):
            p = tmp_path / f"chunk_{i:06d}.ts"
            _touch_with_mtime(p, base + i * 0.1)
            c.record_mtime(p.stat().st_mtime)
        # i=0: 0.0
        # i=1: cumulative 10, delta 0.1, clamp 0.5, correction -9.5, snapshot 0.5
        # i=2: cumulative 10.5, delta 0.1, clamp 0.5, correction -9.5, snapshot 1.0
        # i=3: cumulative 11.0, delta 0.1, clamp 0.5, correction -9.5, snapshot 1.5
        assert c.cumulative == pytest.approx(11.5)  # 1.5 + 10

    def test_jump_clamps_via_files(self, tmp_path: Path) -> None:
        """A 100s gap between two files clamps to 2x default."""
        c = ChunkClock(chunk_duration=10.0)
        p1 = tmp_path / "a.ts"
        p2 = tmp_path / "b.ts"
        _touch_with_mtime(p1, 1_700_000_000.0)
        _touch_with_mtime(p2, 1_700_000_100.0)  # 100s later
        c.record_mtime(p1.stat().st_mtime)
        cum = c.record_mtime(p2.stat().st_mtime)
        # delta=100, clamp 20, correction +10, snapshot 20
        assert cum == pytest.approx(20.0)


# -----------------------------------------------------------------------------
# Long-running drift scenario
# -----------------------------------------------------------------------------


class TestChunkClockDriftScenario:
    """Simulate the long-running drift scenario F108 documented (180 chunks, 0.05s drift each)."""

    def test_180_chunks_at_10_05s_each(self) -> None:
        c = ChunkClock(chunk_duration=10.0)
        mtime = 1000.0
        snapshots: list[float] = []
        for _ in range(180):
            cum = c.record_mtime(mtime)
            snapshots.append(cum)
            mtime += 10.05
        # First snapshot: 0.0
        assert snapshots[0] == pytest.approx(0.0)
        # Snapshot at chunk i: i*10 + i*0.05 = i*10.05
        # After 179 corrections: 179 * 10.05 = 1798.95
        assert snapshots[179] == pytest.approx(179 * 10.05)
        # Cumulative offset is the drift: 179 * 0.05 = 8.95s
        # (i.e. the actual elapsed time is 180 * 10.05 = 1809s, but cumulative
        # counts nominal 1790s + drift 8.95s = 1798.95s)
        drift = snapshots[179] - 179 * 10
        assert drift == pytest.approx(8.95, abs=0.01)

    def test_drift_resets_on_chunk_duration_change(self) -> None:
        """Changing chunk_duration mid-stream resets cumulative to 0."""
        c = ChunkClock(chunk_duration=10.0)
        c.record_mtime(1000.0)
        c.record_mtime(1010.5)  # +0.5 drift
        c.record_mtime(1021.0)  # +0.5 more drift
        assert c.cumulative > 30.0

        # Operator changes chunk_duration mid-stream
        c.update_chunk_duration(15.0)
        assert c.cumulative == 0.0
        # Next chunk starts fresh
        assert c.record_mtime(2000.0) == 0.0
        assert c.cumulative == 15.0
