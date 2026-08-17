"""
Integration tests for ChunkClock with real file I/O.

These tests use real file I/O (os.utime, temp files) and should run in the integration suite.
"""

import os
import tempfile
from pathlib import Path

import pytest

from core.chunk_clock import ChunkClock


def _touch_with_mtime(path: Path, mtime: float) -> None:
    """Create a file and set its mtime."""
    path.write_bytes(b"")
    os.utime(path, (mtime, mtime))


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])