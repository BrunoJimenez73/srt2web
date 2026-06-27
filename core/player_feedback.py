"""
PlayerFeedbackMonitor — Feedback loop player -> servidor (F171).

Recibe métricas del player vía WebSocket y decide adaptaciones del pipeline
para evitar rebuffering y mantener buffer saludable.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("srt2web.player_feedback")


@dataclass
class PlayerState:
    buffer_ms: float = 0.0
    target_buffer_ms: float = 12000.0
    bandwidth_bps: float = 0.0
    dropped_frames: int = 0
    stalled: bool = False
    stall_duration_ms: float = 0.0
    last_stall_time: float = 0.0
    last_update: float = 0.0


@dataclass
class AdaptationState:
    chunk_reduced: bool = False
    concurrency_reduced: bool = False
    original_chunk_duration: float = 10.0
    original_max_concurrent: int = 4
    adapted_at: float = 0.0
    last_healthy_at: float = field(default_factory=time.time)

    def is_adapted(self) -> bool:
        return self.chunk_reduced or self.concurrency_reduced

    def reset(self) -> None:
        self.chunk_reduced = False
        self.concurrency_reduced = False
        self.adapted_at = 0.0


class PlayerFeedbackMonitor:
    """
    Monitorea feedback del player y decide adaptaciones.

    Thresholds (configurables via dict en __init__):
    - buffer_low_ms (5000): si buffer < esto, considerar reducción
    - buffer_critical_ms (2000): si buffer < esto, acción inmediata
    - stall_cooldown_s (30): tiempo sin stalls para considerar recuperación
    - healthy_buffer_ms (15000): buffer necesario para considerar saludable
    - healthy_duration_s (60): tiempo con buffer saludable para restaurar
    - chunk_reduction_factor (0.5): factor de reducción de chunk_duration
    - concurrency_reduction (2): workers máximos durante adaptación
    """

    def __init__(
        self,
        thresholds: dict[str, Any] | None = None,
        on_adapt: Callable[[str, dict[str, Any]], None] | None = None,
        on_restore: Callable[[], None] | None = None,
    ) -> None:
        self._player = PlayerState()
        self._adaptation = AdaptationState()
        self._lock = threading.Lock()
        self._on_adapt = on_adapt
        self._on_restore = on_restore

        self.thresholds = {
            "buffer_low_ms": 5000,
            "buffer_critical_ms": 2000,
            "stall_cooldown_s": 30,
            "healthy_buffer_ms": 15000,
            "healthy_duration_s": 60,
            "chunk_reduction_factor": 0.5,
            "concurrency_reduction": 2,
            "adapt_cooldown_s": 15,
        }
        if thresholds:
            self.thresholds.update(thresholds)

        self._last_adapt_time: float = 0.0
        self._stall_events: list[float] = []
        self._max_stall_history = 10

    def record_buffer(self, buffer_ms: float, target_buffer_ms: float) -> None:
        """Actualizar nivel de buffer desde el player."""
        with self._lock:
            self._player.buffer_ms = buffer_ms
            self._player.target_buffer_ms = target_buffer_ms
            self._player.last_update = time.time()
        self._evaluate()

    def record_stall(self, duration_ms: float) -> None:
        """Registrar un evento de rebuffering/stall."""
        with self._lock:
            self._player.stalled = True
            self._player.stall_duration_ms = duration_ms
            self._player.last_stall_time = time.time()
            self._stall_events.append(time.time())
            if len(self._stall_events) > self._max_stall_history:
                self._stall_events = self._stall_events[-self._max_stall_history :]
        logger.warning(f"Player stall detected: {duration_ms}ms")
        self._evaluate()

    def record_bandwidth(self, bps: float) -> None:
        """Actualizar ancho de banda estimado desde el player."""
        with self._lock:
            self._player.bandwidth_bps = bps

    def record_buffered(self, level_ms: float) -> None:
        """Registrar evento de buffer append."""
        with self._lock:
            self._player.buffer_ms = level_ms
            self._player.last_update = time.time()

    def clear_stall(self) -> None:
        """El player reporta que ya no está stalled."""
        with self._lock:
            self._player.stalled = False
            self._player.stall_duration_ms = 0.0
            self._player.last_stall_time = 0.0  # Reset so recent_stalled is False

    def _evaluate(self) -> None:
        """Evaluar si se necesita adaptación."""
        now = time.time()
        with self._lock:
            player = self._player
            adaptation = self._adaptation

            # Cooldown entre adaptaciones
            if now - self._last_adapt_time < self.thresholds.get("adapt_cooldown_s", 15):
                return

            recent_stalled = now - player.last_stall_time < self.thresholds.get("stall_cooldown_s", 30)
            buffer_critical = player.buffer_ms < self.thresholds.get("buffer_critical_ms", 2000)
            buffer_low = player.buffer_ms < self.thresholds.get("buffer_low_ms", 5000)
            buffer_healthy = player.buffer_ms > self.thresholds.get("healthy_buffer_ms", 15000)

            # TO-DO adapt
            if (recent_stalled or buffer_critical) and not adaptation.is_adapted():
                adaptation.adapted_at = now
                adaptation.chunk_reduced = True
                adaptation.concurrency_reduced = True
                self._last_adapt_time = now
                chunk_dur = self.thresholds.get("chunk_reduction_factor", 0.5)
                max_conc = self.thresholds.get("concurrency_reduction", 2)
                reason = "stall" if recent_stalled else "buffer_critical"
                logger.info(
                    f"Player feedback adapt: reducing chunk*{chunk_dur}, " f"concurrency={max_conc} (reason={reason})"
                )
                if self._on_adapt:
                    self._on_adapt(
                        reason,
                        {
                            "chunk_duration_factor": chunk_dur,
                            "max_concurrent": max_conc,
                        },
                    )
                return

            if buffer_low and not adaptation.is_adapted():
                adaptation.adapted_at = now
                adaptation.chunk_reduced = True
                self._last_adapt_time = now
                chunk_dur = self.thresholds.get("chunk_reduction_factor", 0.5)
                logger.info(
                    f"Player feedback adapt: reducing chunk*{chunk_dur} "
                    f"(reason=buffer_low, buffer={player.buffer_ms:.0f}ms)"
                )
                if self._on_adapt:
                    self._on_adapt(
                        "buffer_low",
                        {
                            "chunk_duration_factor": chunk_dur,
                        },
                    )
                return

            # TO-DO restore
            if adaptation.is_adapted() and buffer_healthy:
                healthy_since = now - adaptation.adapted_at
                if healthy_since >= self.thresholds.get("healthy_duration_s", 60):
                    logger.info(
                        f"Player feedback restore: buffer healthy for {healthy_since:.0f}s "
                        f"(buffer={player.buffer_ms:.0f}ms)"
                    )
                    adaptation.reset()
                    adaptation.last_healthy_at = now
                    self._last_adapt_time = now
                    if self._on_restore:
                        self._on_restore()
                    return

            # Update healthy timestamp if buffer is healthy
            if buffer_healthy:
                adaptation.last_healthy_at = now

    def get_state(self) -> dict[str, Any]:
        """Estado actual del monitor (para debug)."""
        with self._lock:
            return {
                "player": {
                    "buffer_ms": self._player.buffer_ms,
                    "target_buffer_ms": self._player.target_buffer_ms,
                    "bandwidth_bps": self._player.bandwidth_bps,
                    "dropped_frames": self._player.dropped_frames,
                    "stalled": self._player.stalled,
                    "stall_duration_ms": self._player.stall_duration_ms,
                    "last_stall_time": self._player.last_stall_time,
                    "last_update": self._player.last_update,
                },
                "adaptation": {
                    "chunk_reduced": self._adaptation.chunk_reduced,
                    "concurrency_reduced": self._adaptation.concurrency_reduced,
                    "is_adapted": self._adaptation.is_adapted(),
                    "adapted_at": self._adaptation.adapted_at,
                    "last_healthy_at": self._adaptation.last_healthy_at,
                },
                "stall_count": len(self._stall_events),
            }


__all__ = ["PlayerFeedbackMonitor"]
