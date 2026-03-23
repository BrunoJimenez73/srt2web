"""
FFmpeg Process Pool - Reutiliza procesos FFmpeg para mejor rendimiento.

En vez de crear un nuevo proceso FFmpeg para cada operación,
este pool mantiene procesos vivos y los reutiliza.
"""

import subprocess
import threading
import logging
import queue
from typing import Optional, Dict, List
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("srt2web.ffmpeg_pool")


@dataclass
class PooledProcess:
    """Wrapper for a pooled FFmpeg process."""

    process: subprocess.Popen
    ffmpeg_path: str
    last_used: float
    busy: bool = False
    job_id: Optional[str] = None


class FFmpegPool:
    """
    Pool of FFmpeg processes for reusable encoding/muxing operations.

    Benefits:
    - Avoid process creation overhead
    - Reuse FFmpeg initialization
    - Better resource management
    """

    def __init__(self, max_size: int = 4, idle_timeout: float = 30.0):
        """
        Initialize FFmpeg pool.

        Args:
            max_size: Maximum number of processes in pool
            idle_timeout: Seconds before idle process is terminated
        """
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        self._pool: Dict[str, PooledProcess] = {}  # job_id -> PooledProcess
        self._available: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = True

        # Start cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True, name="ffmpeg-pool-cleanup"
        )
        self._cleanup_thread.start()

        logger.info(
            f"FFmpeg pool initialized (max_size={max_size}, idle_timeout={idle_timeout}s)"
        )

    def acquire(self, ffmpeg_path: str, job_id: str) -> Optional[subprocess.Popen]:
        """
        Acquire an FFmpeg process for a job.

        Args:
            ffmpeg_path: Path to FFmpeg executable
            job_id: Unique identifier for the job

        Returns:
            Popen object or None if pool is full
        """
        import time

        with self._lock:
            # Check if we already have a process for this job
            if job_id in self._pool:
                pp = self._pool[job_id]
                if not pp.busy:
                    pp.busy = True
                    pp.last_used = time.time()
                    pp.job_id = job_id
                    logger.debug(f"Reusing existing process for job {job_id}")
                    return pp.process

            # Check pool size
            if len(self._pool) >= self.max_size:
                # Try to find an idle process to reuse
                for jid, pp in list(self._pool.items()):
                    if not pp.busy:
                        # Terminate idle process and create new one
                        self._terminate_process(pp)
                        del self._pool[jid]
                        break
                else:
                    logger.warning(
                        f"FFmpeg pool full ({self.max_size}), cannot create new process"
                    )
                    return None

            # Create new process
            try:
                process = subprocess.Popen(
                    [ffmpeg_path, "-version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                    if hasattr(subprocess, "CREATE_NO_WINDOW")
                    else 0,
                )
                process.wait(timeout=5)

                pp = PooledProcess(
                    process=process,
                    ffmpeg_path=ffmpeg_path,
                    last_used=time.time(),
                    busy=True,
                    job_id=job_id,
                )
                self._pool[job_id] = pp

                logger.debug(f"Created new FFmpeg process for job {job_id}")
                return process

            except Exception as e:
                logger.error(f"Failed to create FFmpeg process: {e}")
                return None

    def release(self, job_id: str):
        """Release a process back to the pool."""
        with self._lock:
            if job_id in self._pool:
                pp = self._pool[job_id]
                pp.busy = False
                pp.job_id = None
                import time

                pp.last_used = time.time()
                logger.debug(f"Released process for job {job_id}")

    def get_stats(self) -> Dict:
        """Get pool statistics."""
        with self._lock:
            total = len(self._pool)
            busy = sum(1 for pp in self._pool.values() if pp.busy)
            return {
                "total_processes": total,
                "busy_processes": busy,
                "available_processes": total - busy,
                "max_size": self.max_size,
            }

    def shutdown(self):
        """Shutdown the pool and terminate all processes."""
        self._running = False
        with self._lock:
            for pp in self._pool.values():
                self._terminate_process(pp)
            self._pool.clear()
        logger.info("FFmpeg pool shut down")

    def _terminate_process(self, pp: PooledProcess):
        """Safely terminate a process."""
        try:
            if pp.process.poll() is None:
                pp.process.terminate()
                pp.process.wait(timeout=5)
        except Exception:
            try:
                pp.process.kill()
            except Exception:
                pass

    def _cleanup_loop(self):
        """Background thread to cleanup idle processes."""
        import time

        while self._running:
            time.sleep(10)  # Check every 10 seconds
            if not self._running:
                break

            with self._lock:
                now = time.time()
                to_remove = []

                for job_id, pp in self._pool.items():
                    if not pp.busy and (now - pp.last_used) > self.idle_timeout:
                        self._terminate_process(pp)
                        to_remove.append(job_id)
                        logger.debug(f"Cleaned up idle process for job {job_id}")

                for job_id in to_remove:
                    del self._pool[job_id]


# Global pool instance
_pool: Optional[FFmpegPool] = None


def get_pool() -> FFmpegPool:
    """Get or create the global FFmpeg pool."""
    global _pool
    if _pool is None:
        _pool = FFmpegPool(max_size=4, idle_timeout=30.0)
    return _pool


def shutdown_pool():
    """Shutdown the global pool."""
    global _pool
    if _pool is not None:
        _pool.shutdown()
        _pool = None
