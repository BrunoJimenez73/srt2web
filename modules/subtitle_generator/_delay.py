import logging
import time

from core.subtitle_sync_monitor import SubtitleSyncMonitor

logger = logging.getLogger("srt2web.module.subtitle_generator")


class DelayCompensator:
    """Estimates pipeline delay and applies drift correction for subtitle sync."""

    def __init__(
        self,
        smoothing_factor: float = 0.1,
        dead_zone: float = 1.0,
        max_delay_increase: float = 2.0,
    ) -> None:
        self._pipeline_start_wall: float = 0.0
        self._pipeline_delay_smoothed: float = 0.0
        self._smoothing_factor = smoothing_factor
        self._dead_zone = dead_zone
        self._max_delay_increase = max_delay_increase
        self._drift_monitor: SubtitleSyncMonitor | None = None

    def configure(
        self,
        smoothing_factor: float | None = None,
        dead_zone: float | None = None,
        max_delay_increase: float | None = None,
    ) -> None:
        if smoothing_factor is not None:
            self._smoothing_factor = smoothing_factor
        if dead_zone is not None:
            self._dead_zone = dead_zone
        if max_delay_increase is not None:
            self._max_delay_increase = max_delay_increase

    def reset(self) -> None:
        self._pipeline_start_wall = time.time()
        self._pipeline_delay_smoothed = 0.0

    def set_drift_monitor(self, monitor: SubtitleSyncMonitor | None) -> None:
        self._drift_monitor = monitor

    def estimate_delay(self, chunk_start_time: float) -> float:
        """
        Estimate pipeline delay using damped EMA.

        Returns a monotonically non-decreasing smoothed delay value.
        """
        wall_elapsed = time.time() - self._pipeline_start_wall
        raw_delay = wall_elapsed - chunk_start_time

        if raw_delay >= 0:
            if self._pipeline_delay_smoothed == 0:
                self._pipeline_delay_smoothed = raw_delay
            else:
                diff = raw_delay - self._pipeline_delay_smoothed
                if abs(diff) < self._dead_zone:
                    pass
                elif diff > 0:
                    self._pipeline_delay_smoothed = (
                        1 - self._smoothing_factor
                    ) * self._pipeline_delay_smoothed + self._smoothing_factor * raw_delay
                    max_allowed = self._pipeline_delay_smoothed + self._max_delay_increase
                    if raw_delay > max_allowed:
                        self._pipeline_delay_smoothed = max_allowed

        return self._pipeline_delay_smoothed

    def apply_drift_correction(self, shifted_start: float, wall_elapsed: float) -> float:
        """
        Feed data into the drift monitor and apply correction to shifted_start.

        Returns corrected shifted_start.
        """
        if self._drift_monitor is None:
            return shifted_start

        audio_wall_ms = wall_elapsed * 1000
        sub_media_ms = shifted_start * 1000
        try:
            self._drift_monitor.check_sync(audio_wall_ms, sub_media_ms)
            drift_ms = self._drift_monitor.get_drift_ms()
            if abs(drift_ms) > 100:
                correction_s = drift_ms / 1000.0
                correction_s = max(-3.0, min(3.0, correction_s))
                shifted_start += correction_s
                logger.info(
                    f"[SubtitleGen] Drift correction: drift={drift_ms:.0f}ms, "
                    f"shift=+{correction_s:.2f}s -> shifted={shifted_start:.1f}s"
                )
        except Exception as e:
            logger.error(f"[SubtitleGen] Drift monitor error: {e}")

        return shifted_start
