"""
Tests for PTS-based ChunkClock (F150).

Validates that PTS-based timing eliminates the mtime drift (~0.05s/chunk = 9s over 30min).
"""

import pytest
from core.chunk_clock import ChunkClock


class TestChunkClockPTS:
    """Tests for PTS-based timing in ChunkClock."""

    def test_record_pts_basic(self) -> None:
        """record_pts with ideal PTS values should have zero drift."""
        clock = ChunkClock(chunk_duration=5.0)
        # Simulate 6 chunks with perfect 5s PTS intervals
        for i in range(6):
            pts = i * 5.0  # PTS in seconds
            cumulative = clock.record_pts(pts)
            assert cumulative == pytest.approx(i * 5.0, abs=0.001)

    def test_record_pts_with_jitter(self) -> None:
        """PTS with small jitter should still track correctly."""
        clock = ChunkClock(chunk_duration=5.0)
        # Simulate 6 chunks with 5s intervals + 50ms jitter
        for i in range(6):
            pts = i * 5.0 + 0.05  # 50ms jitter
            cumulative = clock.record_pts(pts)
            # First chunk: 0, second: ~5, etc.
            assert cumulative == pytest.approx(i * 5.0, abs=0.1)

    def test_record_pts_vs_mtime_drift(self) -> None:
        """Compare PTS vs mtime: PTS should have zero drift, mtime accumulates drift."""
        chunk_duration = 5.0
        num_chunks = 10
        mtime_drift_per_chunk = 0.05  # 50ms per chunk (simulates async FFmpeg writes)

        pts_clock = ChunkClock(chunk_duration=chunk_duration)
        mtime_clock = ChunkClock(chunk_duration=chunk_duration)

        for i in range(num_chunks):
            pts_seconds = i * chunk_duration
            mtime = i * chunk_duration + mtime_drift_per_chunk * i

            pts_cumulative = pts_clock.record_pts(pts_seconds)
            mtime_cumulative = mtime_clock.record_mtime(mtime)

            # PTS cumulative should be perfect
            assert pts_cumulative == pytest.approx(i * chunk_duration, abs=0.001)

        # After 10 chunks, mtime drift should be ~0.5s, PTS should be perfect
        assert pts_clock.cumulative == pytest.approx(num_chunks * chunk_duration, abs=0.001)
        # Mtime drift is significant (cumulative ~0.5s after 10 chunks)
        assert mtime_clock.cumulative != pts_clock.cumulative

    def test_record_pts_mixed_with_mtime(self) -> None:
        """record_pts and record_mtime can be mixed in the same clock."""
        clock = ChunkClock(chunk_duration=5.0)
        # First chunk via PTS
        c1 = clock.record_pts(0.0)
        assert c1 == 0.0
        # Second chunk via mtime (fallback scenario)
        c2 = clock.record_mtime(5.05)  # 50ms drift
        assert c2 == pytest.approx(5.0, abs=0.1)
        # Third chunk via PTS again
        c3 = clock.record_pts(10.0)
        assert c3 == pytest.approx(10.0, abs=0.1)

    def test_record_pts_first_chunk_returns_zero(self) -> None:
        """First call to record_pts returns 0.0."""
        clock = ChunkClock(chunk_duration=5.0)
        assert clock.record_pts(100.0) == 0.0

    def test_has_previous_timestamp(self) -> None:
        """has_previous_timestamp tracks state correctly."""
        clock = ChunkClock(chunk_duration=5.0)
        assert not clock.has_previous_timestamp
        clock.record_pts(0.0)
        assert clock.has_previous_timestamp
        # has_previous_mtime is an alias
        assert clock.has_previous_mtime

    def test_reset_clears_pts_state(self) -> None:
        """reset() clears PTS state."""
        clock = ChunkClock(chunk_duration=5.0)
        clock.record_pts(0.0)
        clock.record_pts(5.0)
        clock.reset()
        assert not clock.has_previous_timestamp
        assert clock.cumulative == 0.0

    def test_update_chunk_duration_with_pts(self) -> None:
        """update_chunk_duration resets cumulative, works with PTS."""
        clock = ChunkClock(chunk_duration=5.0)
        clock.record_pts(0.0)
        clock.record_pts(5.0)
        assert clock.cumulative == pytest.approx(10.0, abs=0.001)

        changed = clock.update_chunk_duration(10.0)
        assert changed is True
        assert clock.cumulative == 0.0  # Reset
        # New chunks at 10s
        c = clock.record_pts(20.0)
        assert c == 0.0

    def test_pts_large_values(self) -> None:
        """PTS with large values (long stream) should work."""
        clock = ChunkClock(chunk_duration=5.0)
        # Simulate 1 hour stream: PTS starts at 3600s
        base_pts = 3600.0
        for i in range(6):
            pts = base_pts + i * 5.0
            cumulative = clock.record_pts(pts)
            assert cumulative == pytest.approx(i * 5.0, abs=0.001)

    def test_pts_non_monotonic(self) -> None:
        """PTS going backward (stream glitch) should be clamped."""
        clock = ChunkClock(chunk_duration=5.0)
        clock.record_pts(0.0)
        clock.record_pts(5.0)
        # PTS goes backward by 10s (stream glitch)
        c = clock.record_pts(-5.0)
        # Should clamp to min_delta_s (0.5) - chunk_duration
        # cumulative was 10, then + (0.5 - 5.0) = 10 - 4.5 = 5.5
        assert c == pytest.approx(5.5, abs=0.1)
