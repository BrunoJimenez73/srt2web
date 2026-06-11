"""
FFmpeg Wrapper - Unified interface for FFmpeg process management.

Provides a high-level API for running FFmpeg commands, managing long-running
streams, and handling output/error logs consistently across the project.
"""

import logging
import platform
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any

from core.ffmpeg_utils import find_ffmpeg, find_ffprobe
from core.ffmpeg_pool import FFmpegPool, get_pool
from core.module_base import BaseModule

logger = logging.getLogger("srt2web.ffmpeg_wrapper")


class FFmpegProcess:
    """
    Manages a single long-running FFmpeg process.
    """

    def __init__(
        self,
        args: list[str],
        name: str = "ffmpeg",
        on_stderr: Callable[[str], None] | None = None,
        creation_flags: int | None = None,
    ):
        # Convert all args to strings to avoid WindowsPath issues
        self.args = [str(arg) for arg in args]
        self.name = name
        self.on_stderr = on_stderr
        self.creation_flags = creation_flags or 0
        self._process: subprocess.Popen[str] | None = None
        self._stop_event = threading.Event()
        self._stderr_thread: threading.Thread | None = None
        # F131: pool reference for slot release on stop
        self._pool_job_id: str | None = None
        self._pool_ref: FFmpegPool | None = None

    def start(self) -> None:
        """Starts the FFmpeg process."""
        logger.info(f"Starting FFmpeg process [{self.name}]: {' '.join(self.args)}")

        try:
            self._process = subprocess.Popen(
                self.args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding="utf-8",
                creationflags=self.creation_flags,
                bufsize=1,
            )

            # Start stderr monitoring thread
            self._stderr_thread = threading.Thread(
                target=self._read_stderr, daemon=True, name=f"ffmpeg-stderr-{self.name}"
            )
            self._stderr_thread.start()

        except Exception as e:
            logger.error(f"Failed to start FFmpeg process [{self.name}]: {e}")
            raise

    def _read_stderr(self) -> None:
        """Reads FFmpeg stderr line by line."""
        if not self._process or not self._process.stderr:
            return

        try:
            for line in self._process.stderr:
                if self._stop_event.is_set():
                    break
                if self.on_stderr:
                    self.on_stderr(line.strip())
        except Exception as e:
            logger.debug(f"Stderr reading stopped for [{self.name}]: {e}")

    def stop(self, timeout: float = 5.0) -> None:
        """Stops the FFmpeg process gracefully then forcefully. Releases pool slot."""
        self._stop_event.set()

        if not self._process:
            self._release_pool()
            return

        try:
            # Try SIGTERM first
            self._process.terminate()

            # Wait for process to exit
            start_wait = time.time()
            while time.time() - start_wait < timeout:
                if self._process.poll() is not None:
                    break
                time.sleep(0.1)

            # Force kill if still running
            if self._process.poll() is None:
                logger.warning(f"FFmpeg process [{self.name}] did not terminate, killing...")
                self._process.kill()

        except Exception as e:
            logger.error(f"Error stopping FFmpeg process [{self.name}]: {e}")
        finally:
            if self._stderr_thread:
                self._stderr_thread.join(timeout=1.0)
            self._process = None
            self._release_pool()

    def _release_pool(self) -> None:
        """Release the pool slot if one was acquired."""
        if self._pool_ref is not None and self._pool_job_id is not None:
            self._pool_ref.release(self._pool_job_id)
            self._pool_job_id = None

    @property
    def is_alive(self) -> bool:
        """Check if process is still running."""
        return self._process is not None and self._process.poll() is None

    @property
    def returncode(self) -> int | None:
        return self._process.poll() if self._process else None


class FFmpegWrapper:
    """
    High-level wrapper for FFmpeg and FFprobe operations.
    """

    def __init__(self, name: str = "ffmpeg_wrapper", pool: FFmpegPool | None = None):
        self.name = name
        self.ffmpeg_path = str(find_ffmpeg())
        self.ffprobe_path = str(find_ffprobe())
        self._creation_flags = self._get_default_creation_flags()
        self._pool = pool or get_pool()

    def _get_default_creation_flags(self) -> int | None:
        """Returns Windows-specific flags to hide console windows."""
        if platform.system() == "Windows":
            # CREATE_NO_WINDOW = 0x08000000
            return 0x08000000
        return None

    def run_command(
        self, args: list[str], capture_output: bool = True, timeout: float | None = None
    ) -> subprocess.CompletedProcess[str]:
        """
        Runs a short-lived FFmpeg command.
        F131: acquires a pool slot before running.
        """
        job_id = f"{self.name}_{int(time.time() * 1000)}"
        if not self._pool.acquire(self.ffmpeg_path, job_id, timeout=30.0):
            raise RuntimeError(f"FFmpegPool: timeout waiting for slot (job={job_id})")
        try:
            full_args = [self.ffmpeg_path, *args]
            logger.debug(f"Running FFmpeg command: {' '.join(full_args)}")

            result = subprocess.run(
                full_args,
                capture_output=capture_output,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                creationflags=self._creation_flags or 0,
                check=True,
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg command failed: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error running FFmpeg: {e}")
            raise
        finally:
            self._pool.release(job_id)

    def run_probe(self, args: list[str], capture_output: bool = True) -> subprocess.CompletedProcess[str]:
        """
        Runs an FFprobe command.
        """
        full_args = [self.ffprobe_path, *args]
        logger.debug(f"Running FFprobe command: {' '.join(full_args)}")

        try:
            return subprocess.run(
                full_args,
                capture_output=capture_output,
                text=True,
                encoding="utf-8",
                creationflags=self._creation_flags or 0,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"FFprobe command failed: {e.stderr}")
            raise

    def create_process(
        self, args: list[str], process_name: str = "ffmpeg", on_stderr: Callable[[str], None] | None = None
    ) -> FFmpegProcess:
        """
        Creates and returns a managed FFmpeg process.
        F131: acquires a pool slot before creating.
        """
        job_id = f"{process_name}_{int(time.time() * 1000)}"
        if not self._pool.acquire(self.ffmpeg_path, job_id, timeout=30.0):
            raise RuntimeError(f"FFmpegPool: timeout waiting for slot (job={job_id})")
        full_args = [self.ffmpeg_path, *args]
        process = FFmpegProcess(
            args=full_args, name=process_name, on_stderr=on_stderr, creation_flags=self._creation_flags
        )
        process._pool_job_id = job_id
        process._pool_ref = self._pool
        return process


class FFmpegModule(BaseModule):
    """
    Base class for modules that use FFmpeg.
    Provides common FFmpeg functionality and wrapper instance.
    """

    def __init__(self, module_name: str, config: dict[str, Any] | None = None, pool: FFmpegPool | None = None):
        super().__init__(module_name, config)
        self.ffmpeg = FFmpegWrapper(name=module_name, pool=pool)
        self.logger = logging.getLogger(f"srt2web.module.{module_name}")

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
