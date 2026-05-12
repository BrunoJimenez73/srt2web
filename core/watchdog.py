"""
FFmpeg Watchdog - Monitors FFmpeg processes for crashes and hangs.

Provides automatic restart capability when FFmpeg fails.
"""

import logging
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from typing import Any, Optional

logger = logging.getLogger("srt2web.watchdog")


class FFmpegWatchdog:
    """
    Monitors FFmpeg processes for crashes and hangs.

    Features:
    - Detects process crashes
    - Detects hangs (no output for timeout period)
    - Automatic restart with configurable attempts
    - Callback hooks for restart events
    """

    def __init__(
        self,
        check_interval: float = 5.0,
        hang_timeout: float = 60.0,
        max_restarts: int = 10,
        restart_delay: float = 2.0,
    ) -> None:
        """
        Args:
            check_interval: Seconds between health checks
            hang_timeout: Seconds without output before considering hung
            max_restarts: Maximum restart attempts before giving up
            restart_delay: Seconds to wait before restarting
        """
        self.check_interval = check_interval
        self.hang_timeout = hang_timeout
        self.max_restarts = max_restarts
        self.restart_delay = restart_delay

        self._process: Optional[subprocess.Popen[bytes]] = None
        self._stop_event = threading.Event()
        self._watch_thread: Optional[threading.Thread] = None
        self._last_output_time = time.time()
        self._restart_count = 0
        self._is_hung = False
        self._restart_callback: Optional[Callable[[], None]] = None
        self._process_name = "FFmpeg"

    @property
    def restart_count(self) -> int:
        """Number of restarts performed."""
        return self._restart_count

    @property
    def is_healthy(self) -> bool:
        """Check if process is healthy."""
        if self._process is None:
            return False
        if self._process.poll() is not None:
            return False
        return not self._is_hung

    def attach_process(
        self,
        process: subprocess.Popen[bytes],
        process_name: str = "FFmpeg",
        restart_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Attach watchdog to a running process.

        Args:
            process: The Popen process to monitor
            process_name: Human-readable name for logging
            restart_callback: Function to call to restart the process
        """
        self._process = process
        self._process_name = process_name
        self._restart_callback = restart_callback
        self._last_output_time = time.time()
        self._is_hung = False

    def detach(self) -> None:
        """Detach from the monitored process."""
        self._process = None
        self._restart_callback = None
        self._restart_count = 0

    def start(self) -> None:
        """Start the watchdog monitoring thread."""
        if self._watch_thread is not None and self._watch_thread.is_alive():
            return

        self._stop_event.clear()
        self._watch_thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
            name="ffmpeg-watchdog",
        )
        self._watch_thread.start()
        logger.info(f"{self._process_name} watchdog started")

    def stop(self) -> None:
        """Stop the watchdog monitoring thread."""
        self._stop_event.set()
        if self._watch_thread and self._watch_thread.is_alive():
            self._watch_thread.join(timeout=5)
        logger.info(f"{self._process_name} watchdog stopped")

    def notify_activity(self) -> None:
        """Call this when the process produces output."""
        self._last_output_time = time.time()
        if self._is_hung:
            self._is_hung = False
            logger.info(f"{self._process_name} recovered from hang")

    def _watch_loop(self) -> None:
        """Main watchdog loop (runs in background thread)."""
        while not self._stop_event.is_set():
            try:
                self._check_health()
            except Exception as e:
                logger.error(f"Watchdog error: {e}")

            self._stop_event.wait(self.check_interval)

    def _check_health(self) -> None:
        """Check process health and restart if needed."""
        if self._process is None:
            return

        proc = self._process

        if proc.poll() is not None:
            returncode = proc.returncode
            logger.error(f"{self._process_name} crashed with exit code {returncode}")
            self._handle_crash()
            return

        time_since_output = time.time() - self._last_output_time
        if time_since_output > self.hang_timeout and not self._is_hung:
            self._is_hung = True
            logger.warning(f"{self._process_name} appears hung " f"(no output for {time_since_output:.0f}s)")
            self._handle_hang()

    def _handle_crash(self) -> None:
        """Handle process crash."""
        self._attempt_restart("crash")

    def _handle_hang(self) -> None:
        """Handle process hang."""
        if self._process and self._process.poll() is None:
            logger.info(f"Killing hung {self._process_name}...")
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self._process.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    self._process.kill()
            except Exception as e:
                logger.error(f"Failed to kill process: {e}")

        self._attempt_restart("hang")

    def _attempt_restart(self, reason: str) -> None:
        """Attempt to restart the process."""
        if self._restart_count >= self.max_restarts:
            logger.error(f"{self._process_name} max restarts ({self.max_restarts}) reached. " "Giving up.")
            return

        self._restart_count += 1
        logger.info(
            f"Attempting to restart {self._process_name} "
            f"(reason: {reason}, attempt {self._restart_count}/{self.max_restarts})"
        )

        time.sleep(self.restart_delay)

        if self._restart_callback:
            try:
                self._restart_callback()
                self._last_output_time = time.time()
                self._is_hung = False
                logger.info(f"{self._process_name} restarted successfully")
            except Exception as e:
                logger.error(f"Failed to restart {self._process_name}: {e}")
        else:
            logger.warning(f"{self._process_name} cannot restart: no restart callback set")


class ProcessManager:
    """
    Manages multiple FFmpeg processes with watchdog support.

    Ensures only one instance of each process type runs at a time,
    and automatically cleans up orphaned processes.
    """

    _instance: Optional["ProcessManager"] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool

    def __new__(cls) -> "ProcessManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._processes: dict[str, FFmpegWatchdog] = {}
        self._initialized = True
        logger.info("ProcessManager initialized")

    def register_process(
        self,
        name: str,
        process: subprocess.Popen[bytes],
        restart_callback: Optional[Callable[[], None]] = None,
        **watchdog_kwargs: Any,
    ) -> FFmpegWatchdog:
        """
        Register a process with the manager.

        Args:
            name: Unique identifier for this process
            process: The Popen process to monitor
            restart_callback: Function to restart the process
            **watchdog_kwargs: Arguments for FFmpegWatchdog

        Returns:
            The FFmpegWatchdog instance
        """
        watchdog = FFmpegWatchdog(**watchdog_kwargs)
        watchdog.attach_process(process, name, restart_callback)
        watchdog.start()

        self._processes[name] = watchdog
        logger.info(f"Registered process '{name}' with ProcessManager")

        return watchdog

    def unregister_process(self, name: str) -> None:
        """Unregister and stop monitoring a process."""
        if name in self._processes:
            watchdog = self._processes.pop(name)
            watchdog.detach()
            watchdog.stop()
            logger.info(f"Unregistered process '{name}' from ProcessManager")

    def get_watchdog(self, name: str) -> Optional[FFmpegWatchdog]:
        """Get the watchdog for a registered process."""
        return self._processes.get(name)

    def get_all_health(self) -> dict[str, Any]:
        """Get health status of all monitored processes."""
        return {
            name: {
                "healthy": wd.is_healthy,
                "restart_count": wd.restart_count,
            }
            for name, wd in self._processes.items()
        }

    def kill_all(self) -> None:
        """Kill all monitored processes."""
        for name, watchdog in self._processes.items():
            if watchdog._process and watchdog._process.poll() is None:
                logger.info(f"Killing process '{name}'...")
                try:
                    if sys.platform == "win32":
                        subprocess.run(
                            [
                                "taskkill",
                                "/F",
                                "/T",
                                "/PID",
                                str(watchdog._process.pid),
                            ],
                            capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                    else:
                        watchdog._process.kill()
                except Exception as e:
                    logger.error(f"Failed to kill '{name}': {e}")

        self._processes.clear()
        logger.info("All processes killed")

    def cleanup_orphans(self) -> int:
        """
        Clean up orphaned FFmpeg processes started by this application.

        Returns:
            Number of processes cleaned up
        """
        cleaned = 0

        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq ffmpeg.exe", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                )
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split(",")
                        if len(parts) >= 2:
                            pid = parts[1].strip('"')
                            try:
                                subprocess.run(
                                    ["taskkill", "/F", "/PID", pid],
                                    capture_output=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                )
                                cleaned += 1
                                logger.info(f"Cleaned up orphan FFmpeg (PID: {pid})")
                            except Exception:
                                pass
            else:
                subprocess.run(
                    ["pkill", "-f", "ffmpeg.*srt2web"],
                    capture_output=True,
                )
                cleaned = 1
                logger.info("Cleaned up orphan FFmpeg processes")
        except Exception as e:
            logger.error(f"Error cleaning up orphans: {e}")

        return cleaned
