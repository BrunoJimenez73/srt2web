"""
FFmpeg Process Pool - Gestiona slots de concurrencia para operaciones FFmpeg.

En vez de intentar reutilizar procesos FFmpeg individuales (lo que no es
posible de forma genérica ya que cada invocación tiene argumentos distintos),
este pool actúa como un semáforo con seguimiento de jobs activos, evitando
saturar el sistema con demasiados procesos FFmpeg simultáneos.

Mejora respecto a la versión anterior:
- Ya no lanza procesos "ffmpeg -version" inútilmente al adquirir un slot.
- El pool es un semáforo de concurrencia + registro de jobs activos.
- Útil para limitar paralelismo en audio_extractor, audio_mixer, video_muxer.
"""

import time
import threading
import logging
from typing import Optional, Dict
from dataclasses import dataclass, field

logger = logging.getLogger("srt2web.ffmpeg_pool")


@dataclass
class JobSlot:
    """Registro de un job activo en el pool."""
    job_id: str
    acquired_at: float = field(default_factory=time.time)
    description: str = ""


class FFmpegPool:
    """
    Pool de concurrencia para operaciones FFmpeg.

    Controla cuántos procesos FFmpeg pueden correr en paralelo, evitando
    saturar CPU/GPU. No reutiliza procesos (FFmpeg no es un servidor);
    en cambio, limita la cantidad de invocaciones simultáneas.
    """

    def __init__(self, max_size: int = 4, idle_timeout: float = 30.0):
        self.max_size = max_size
        self.idle_timeout = idle_timeout  # conservado por compatibilidad de API
        self._semaphore = threading.Semaphore(max_size)
        self._active: Dict[str, JobSlot] = {}
        self._lock = threading.Lock()
        self._running = True
        logger.info(f"FFmpegPool initialized (max_concurrent={max_size})")

    def acquire(self, ffmpeg_path: str, job_id: str, timeout: float = 30.0) -> bool:
        """
        Adquirir un slot de concurrencia para un job FFmpeg.

        Args:
            ffmpeg_path: Ruta al ejecutable FFmpeg (no se usa aquí, por API compat).
            job_id: Identificador único del job.
            timeout: Tiempo máximo de espera en segundos.

        Returns:
            True si se adquirió el slot, False si se agotó el timeout.
        """
        acquired = self._semaphore.acquire(timeout=timeout)
        if not acquired:
            logger.warning(f"FFmpegPool: timeout waiting for slot (job={job_id})")
            return False

        with self._lock:
            self._active[job_id] = JobSlot(job_id=job_id)

        logger.debug(f"FFmpegPool: slot acquired for job={job_id} (active={len(self._active)}/{self.max_size})")
        return True

    def release(self, job_id: str) -> None:
        """Liberar el slot de concurrencia de un job."""
        with self._lock:
            if job_id not in self._active:
                logger.debug(f"FFmpegPool: release called for unknown job={job_id}")
                return
            elapsed = time.time() - self._active[job_id].acquired_at
            del self._active[job_id]

        self._semaphore.release()
        logger.debug(f"FFmpegPool: slot released for job={job_id} (held {elapsed:.1f}s, active={len(self._active)}/{self.max_size})")

    def get_stats(self) -> Dict:
        """Estadísticas actuales del pool."""
        with self._lock:
            active_count = len(self._active)
            active_jobs = list(self._active.keys())
        return {
            "total_slots": self.max_size,
            "active_slots": active_count,
            "free_slots": self.max_size - active_count,
            "active_jobs": active_jobs,
        }

    def shutdown(self) -> None:
        """Marcar el pool como cerrado."""
        self._running = False
        with self._lock:
            self._active.clear()
        logger.info("FFmpegPool shut down")


# ---------------------------------------------------------------------------
# Instancia global singleton
# ---------------------------------------------------------------------------

_pool: Optional[FFmpegPool] = None
_pool_lock = threading.Lock()


def get_pool() -> FFmpegPool:
    """Obtener (o crear) el pool global de FFmpeg."""
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = FFmpegPool(max_size=4, idle_timeout=30.0)
    return _pool


def shutdown_pool() -> None:
    """Apagar el pool global."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.shutdown()
            _pool = None
