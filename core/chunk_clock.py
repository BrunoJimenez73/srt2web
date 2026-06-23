"""
core.chunk_clock — Cumulative duration tracking via PTS/PCR or file mtime.

Extracted from the inline drift-correction blocks in:
  - modules/inputs/srt_input.py (was at lines 586-591 in pre-F115 layout)
  - modules/inputs/rtmp_input.py (was at lines 334-342 in pre-F115 layout)

Both inputs use the same pattern: measure wall-clock delta between
consecutive chunk files via their mtime, clamp the delta to a sane
range, and add the difference vs the nominal chunk_duration to a
cumulative offset. Downstream modules (transcriber, TTS) use that
cumulative offset to keep audio + subtitles in sync with the actual
recording wall clock, even when FFmpeg's chunk writing drifts a few
ms per chunk.

**PTS/PCR mode** (preferred): extracts timing directly from the MPEG-TS
container. Eliminates mtime-based drift (~0.05s/chunk = 9s over 30min)
caused by async FFmpeg writes.

This module exists for three reasons:
  1. **Testability** — drift correction has subtle edge cases (first
     chunk, jumps in mtime when FFmpeg restarts, clock going backward)
     that are easier to test in isolation than via the input modules.
  2. **Single source of truth** — before F115, srt_input and rtmp_input
     had the same 7 lines copied verbatim. Any future change (e.g.
     different clamp bounds, additional metadata) had to be made in
     two places. Now it's in one.
  3. **Smaller input modules** — srt_input.py was 735 lines (above
     the 500-line target). Extracting ~10 lines plus the related
     state (`_last_chunk_mtime`, `_cumulative_duration`) helps a bit,
     and more importantly, makes the file easier to navigate.

Typical usage in an input module:

    from core.chunk_clock import ChunkClock

    class SRTInput(InputModule):
        def __init__(self, config):
            self._chunk_duration = config.get("chunk_duration_sec", 10)
            self._clock = ChunkClock(chunk_duration=self._chunk_duration)
            ...

        def _process_chunk(self, chunk_path: Path) -> PipelineData:
            # PTS-based (preferred): extract from container
            pts = get_first_packet_pts(chunk_path)
            if pts is not None:
                cumulative = self._clock.record_pts(pts)
            else:
                # Fallback: mtime-based
                mtime = chunk_path.stat().st_mtime
                cumulative = self._clock.record_mtime(mtime)
            return PipelineData(
                ...,
                cumulative_duration=cumulative,
            )

        def configure(self, config):
            new_dur = config.get("chunk_duration_sec", self._chunk_duration)
            if self._clock.update_chunk_duration(new_dur):
                self.logger.info("chunk_duration changed, resetting cumulative")
            self._chunk_duration = new_dur
"""

from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)


# Default clamp bounds for the wall-clock delta. The values are picked
# to tolerate a few hundred ms of jitter per chunk while rejecting
# pathological cases (FFmpeg paused, clock went backward, two chunks
# written in the same millisecond).
DEFAULT_MIN_DELTA_S: Final[float] = 0.5
DEFAULT_MAX_DELTA_MULTIPLIER: Final[float] = 2.0


class ChunkClock:
    """
    Tracks cumulative recording duration using PTS/PCR or file mtime.

    **Preferred mode (PTS/PCR)**: Use :meth:`record_pts` with the PTS
    or PCR value extracted directly from the MPEG-TS container. This
    eliminates mtime-based drift caused by async FFmpeg writes.

    **Fallback mode (mtime)**: Use :meth:`record_mtime` with file mtime.
    Kept for backward compatibility and as fallback when PTS extraction
    fails.

    The clock measures the delta between consecutive timestamps, clamps
    it to a sane range, and adds the difference vs the nominal
    ``chunk_duration`` to a running cumulative offset. Downstream
    consumers use that offset to align transcriber, translator, TTS,
    and subtitle generation with the actual recording wall clock.

    The clock is stateless w.r.t. any specific chunk — it only
    remembers the last timestamp and the cumulative offset. It is
    therefore safe to construct one per input module, and to
    :meth:`reset` on pipeline restart.

    Thread safety: NOT thread-safe. Each input module has its own
    ChunkClock and processes chunks in a single thread (the FFmpeg
    monitor thread). If you need to share a clock across threads,
    wrap it with a lock.
    """

    def __init__(
        self,
        chunk_duration: float,
        *,
        min_delta_s: float = DEFAULT_MIN_DELTA_S,
        max_delta_multiplier: float = DEFAULT_MAX_DELTA_MULTIPLIER,
    ) -> None:
        if chunk_duration <= 0:
            raise ValueError(f"chunk_duration must be > 0, got {chunk_duration}")
        if min_delta_s < 0:
            raise ValueError(f"min_delta_s must be >= 0, got {min_delta_s}")
        if max_delta_multiplier < 1.0:
            raise ValueError(f"max_delta_multiplier must be >= 1.0, got {max_delta_multiplier}")

        self._chunk_duration = float(chunk_duration)
        self._min_delta_s = float(min_delta_s)
        self._max_delta_multiplier = float(max_delta_multiplier)
        self._last_timestamp: float | None = None
        self._cumulative: float = 0.0

    @property
    def chunk_duration(self) -> float:
        """Nominal chunk duration in seconds (used for clamping and increment)."""
        return self._chunk_duration

    @property
    def cumulative(self) -> float:
        """
        Current cumulative duration in seconds.

        After a call to :meth:`record_pts` or :meth:`record_mtime`, this
        includes the just-incremented ``chunk_duration`` for the most
        recent chunk. For example, after recording three 10s chunks,
        ``cumulative`` is 30.0.
        """
        return self._cumulative

    @property
    def has_previous_timestamp(self) -> bool:
        """Whether at least one chunk has been recorded."""
        return self._last_timestamp is not None

    @property
    def has_previous_mtime(self) -> bool:
        """Whether at least one chunk has been recorded. Alias for has_previous_timestamp."""
        return self.has_previous_timestamp

    def record_pts(self, pts_seconds: float) -> float:
        """
        Record a new chunk's PTS (Presentation Time Stamp) in seconds
        and return the cumulative_duration for this chunk.

        PTS is extracted directly from the MPEG-TS container and
        represents the real encoding timestamp. Unlike mtime, PTS
        is monotonically increasing and not affected by async
        filesystem writes.

        Args:
            pts_seconds: PTS value in seconds (raw_pts / clock_rate).

        Returns:
            The cumulative_duration to assign to this chunk, in seconds.
        """
        return self._record_timestamp(pts_seconds)

    def record_mtime(self, mtime: float) -> float:
        """
        Record a new chunk's mtime and return the cumulative_duration
        that should be reported for this chunk.

        The returned value is the starting offset of the chunk in the
        recording timeline (in seconds). It is the value to put in
        ``PipelineData.cumulative_duration`` for this chunk.

        Side effects:
          - If a previous timestamp was recorded, computes the wall-clock
            delta, clamps it to ``[min_delta_s, max_delta_multiplier * chunk_duration]``,
            and adds ``(clamped - chunk_duration)`` to the cumulative
            offset. This corrects the drift caused by FFmpeg's chunk
            writing not being perfectly periodic.
          - Updates ``_last_timestamp`` to the new value.
          - Adds ``chunk_duration`` to the cumulative offset so the
            next call starts from the right position.

        On the first call (no previous timestamp), no drift correction
        is applied — we just return the current cumulative (0.0).

        Note on clamp direction: the clamp is intentionally asymmetric.
        When ``raw_delta < min_delta_s`` (FFmpeg restart, two chunks
        written too close, or clock jitter), the clamped value is
        raised to ``min_delta_s``, which makes the correction
        ``(min_delta_s - chunk_duration)`` NEGATIVE. This pulls the
        cumulative offset backward, which is the conservative
        behavior — downstream consumers will see the new chunk as
        starting slightly before the previous one, never suddenly
        minutes ahead. This matches the pre-F115 inline behavior in
        ``srt_input.py`` and ``rtmp_input.py`` exactly.

        Args:
            mtime: The mtime of the new chunk file (``Path.stat().st_mtime``).

        Returns:
            The cumulative_duration to assign to this chunk, in seconds.
        """
        return self._record_timestamp(mtime)

    def _record_timestamp(self, timestamp: float) -> float:
        """
        Core timestamp recording logic shared by record_pts and record_mtime.

        Args:
            timestamp: The timestamp to record (PTS or mtime).

        Returns:
            The cumulative_duration to assign to this chunk, in seconds.
        """
        if self._last_timestamp is not None:
            raw_delta = timestamp - self._last_timestamp
            upper_bound = self._chunk_duration * self._max_delta_multiplier
            clamped = max(self._min_delta_s, min(raw_delta, upper_bound))
            self._cumulative += clamped - self._chunk_duration

        self._last_timestamp = timestamp
        snapshot = self._cumulative
        self._cumulative += self._chunk_duration
        return snapshot

    def update_chunk_duration(self, new_duration: float) -> bool:
        """
        Update the nominal chunk duration. Returns True if it changed.

        When the duration changes, the cumulative offset is reset to
        0.0 because the old cumulative was measured against the old
        duration — mixing the two time bases would produce incorrect
        offsets. The caller can use the return value to log a warning
        or notify operators.

        This matches the pre-F115 inline behavior in
        ``srt_input.configure()`` and ``rtmp_input.__init__``:

            if new_chunk_duration != self._chunk_duration:
                self._cumulative_duration = 0.0
            self._chunk_duration = new_chunk_duration
        """
        if new_duration <= 0:
            raise ValueError(f"new_duration must be > 0, got {new_duration}")
        if new_duration == self._chunk_duration:
            return False
        self._chunk_duration = float(new_duration)
        self.reset()
        return True

    def reset(self) -> None:
        """
        Reset the clock to its initial state.

        Clears the last timestamp and cumulative offset. Typically called
        on pipeline start/stop or when the chunk_duration changes.
        """
        self._last_timestamp = None
        self._cumulative = 0.0


__all__ = [
    "DEFAULT_MAX_DELTA_MULTIPLIER",
    "DEFAULT_MIN_DELTA_S",
    "ChunkClock",
]
