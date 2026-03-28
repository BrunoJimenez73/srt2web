"""
RTMP Input - Receives RTMP streams via FFmpeg.

Supports:
- RTMP Pull: Connect to external RTMP server
- RTMP Push: Act as RTMP server (receive from OBS)

FFmpeg handles both modes natively.
"""

import os
import sys
import glob
import time
import logging
import subprocess
import threading
from typing import Optional

from core.input_source import InputSource
from core.module_base import BaseModule
from core.ffmpeg_utils import ensure_ffmpeg

logger = logging.getLogger("srt2web.input.rtmp")


class RTMPInput(InputSource):
    """
    Receives an RTMP stream and produces segmented MPEG-TS chunks.

    Modes:
    - pull: Connect to external RTMP server
    - push: Act as RTMP server (requires rtmpd or similar)

    For push mode, FFmpeg receives from stdin or pipe.
    For pull mode, FFmpeg connects to the RTMP URL.
    """

    name = "rtmp_input"

    def __init__(
        self,
        config: Optional[dict] = None,
        circuit_breaker = None,
        retry_strategy = None,
    ):
        super().__init__("rtmp_input", config, circuit_breaker, retry_strategy)
        self._ffmpeg_path: Optional[str] = None
        self._ffmpeg_proc: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._output_dir: str = "./output"
        self._chunks_dir: str = ""
        self._last_chunk_index = -1
        self._cumulative_duration: float = 0.0  # Track cumulative duration for sync
        self._url: str = ""
        self._mode: str = "pull"
        self._chunk_duration: int = 10
        self._receiving: bool = False
        self._watchdog: Optional[any] = None

        if config:
            self.configure(config)

    @property
    def config(self) -> dict:
        return self._config

    def configure(self, config: dict) -> None:
        """Apply configuration."""
        self._config = config

        self._url = config.get("url", "rtmp://localhost/live/stream")
        self._mode = config.get("mode", "pull")
        self._chunk_duration = config.get("chunk_duration_sec", 10)
        self._output_dir = config.get("output_dir", self._output_dir)

    def set_output_dir(self, output_dir: str) -> None:
        """Set the output directory for chunks."""
        self._output_dir = output_dir
        self._chunks_dir = os.path.join(output_dir, "chunks")

    def start(self) -> None:
        """Start FFmpeg RTMP receiver."""
        self.stop()
        time.sleep(0.5)

        self._last_chunk_index = -1

        self._ffmpeg_path = ensure_ffmpeg()

        self._chunks_dir = os.path.join(self._output_dir, "chunks")
        os.makedirs(self._chunks_dir, exist_ok=True)

        for f in glob.glob(os.path.join(self._chunks_dir, "chunk_*.ts")):
            try:
                os.remove(f)
            except OSError:
                pass

        # Reset cumulative duration tracking
        self._cumulative_duration = 0.0

        chunk_pattern = os.path.join(self._chunks_dir, "chunk_%06d.ts")

        cmd = [
            self._ffmpeg_path,
            "-y",
            "-i",
            self._url,
            "-c",
            "copy",
            "-f",
            "segment",
            "-segment_time",
            str(self._chunk_duration),
            "-segment_format",
            "mpegts",
            "-reset_timestamps",
            "1",
            "-strftime",
            "0",
            "-max_muxing_queue_size",
            "1024",
            "-fflags",
            "+genpts+discardcorrupt",
            "-flush_packets",
            "1",
            chunk_pattern,
        ]

        logger.info(f"Starting RTMP input: {' '.join(cmd[:6])}...")

        self._ffmpeg_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            ),
        )

        self._monitor_thread = threading.Thread(
            target=self._monitor_ffmpeg,
            daemon=True,
            name="rtmp-monitor",
        )
        self._monitor_thread.start()

        self._receiving = True

        try:
            from core.watchdog import FFmpegWatchdog

            self._watchdog = FFmpegWatchdog(
                hang_timeout=60,
                max_restarts=10,
            )
            self._watchdog.attach_process(
                self._ffmpeg_proc,
                "RTMP Input",
                restart_callback=self._restart,
            )
            self._watchdog.start()
        except ImportError:
            pass

    def _restart(self) -> None:
        """Restart the RTMP receiver."""
        logger.info("Restarting RTMP receiver...")
        self._ffmpeg_proc = None
        self.start()

    def stop(self) -> None:
        """Stop FFmpeg RTMP receiver."""
        if self._watchdog:
            self._watchdog.stop()
            self._watchdog = None

        if self._ffmpeg_proc:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self._ffmpeg_proc.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    self._ffmpeg_proc.terminate()
                self._ffmpeg_proc.wait(timeout=2)
            except Exception:
                try:
                    self._ffmpeg_proc.kill()
                except:
                    pass
            finally:
                self._ffmpeg_proc = None

        self._receiving = False

    def _monitor_ffmpeg(self) -> None:
        """Monitor FFmpeg stderr for log output."""
        if not self._ffmpeg_proc or not self._ffmpeg_proc.stderr:
            return

        try:
            for line in self._ffmpeg_proc.stderr:
                line = line.strip()
                if line:
                    if "error" in line.lower():
                        logger.error(f"[FFmpeg] {line}")
                    elif "warning" in line.lower():
                        logger.warning(f"[FFmpeg] {line}")
                    else:
                        logger.debug(f"[FFmpeg] {line}")
        except Exception:
            pass

        if self._ffmpeg_proc:
            returncode = self._ffmpeg_proc.poll()
            if returncode is not None:
                self._receiving = False
                if returncode != 0:
                    logger.error(f"FFmpeg exited with code {returncode}")

    def get_next_chunk(self):
        """Get next available chunk."""
        if not self._chunks_dir:
            return None

        chunks = sorted(glob.glob(os.path.join(self._chunks_dir, "chunk_*.ts")))

        if not chunks or len(chunks) < 2:
            return None

        processable = []
        for chunk_path in chunks[:-1]:
            fname = os.path.basename(chunk_path)
            try:
                idx = int(fname.replace("chunk_", "").replace(".ts", ""))
                if idx > self._last_chunk_index:
                    processable.append((idx, chunk_path))
            except ValueError:
                continue

        if not processable:
            return None

        processable.sort()
        idx, chunk_path = processable[0]
        self._last_chunk_index = idx

        from core.module_base import PipelineData
        from core.ffmpeg_utils import get_video_duration

        actual_duration = get_video_duration(chunk_path) or self._chunk_duration

        # Validate duration (warn if FFmpeg segment duration differs too much)
        duration_diff = abs(actual_duration - self._chunk_duration)
        if duration_diff > 0.05:  # 50ms threshold
            logger.warning(
                f"Chunk {idx} duration {actual_duration:.3f}s differs from "
                f"expected {self._chunk_duration:.3f}s by {duration_diff * 1000:.1f}ms"
            )

        # Set cumulative duration BEFORE processing
        chunk_cumulative = self._cumulative_duration

        # Update cumulative for next chunk
        self._cumulative_duration += actual_duration

        logger.info(
            f"New RTMP chunk: {chunk_path} (cumulative: {chunk_cumulative:.3f}s)"
        )

        return PipelineData(
            chunk_index=idx,
            timestamp=time.time(),
            duration=actual_duration,
            cumulative_duration=chunk_cumulative,
            video_chunk_path=chunk_path,
        )

    def _check_is_receiving(self) -> bool:
        """Check if RTMP stream is being received."""
        if self._ffmpeg_proc is None:
            return False
        return self._ffmpeg_proc.poll() is None and self._receiving

    def is_receiving(self) -> bool:
        """Check if the RTMP input is receiving data."""
        return super().is_receiving()

    def get_connection_info(self) -> dict:
        """Get connection information."""
        return {
            "type": "rtmp",
            "mode": self._mode,
            "url": self._url,
            "receiving": self.is_receiving(),
        }


_input_class = RTMPInput


def _register():
    """Auto-register this input module."""
    try:
        from core.io_factory import InputFactory

        InputFactory.register("rtmp", RTMPInput)
    except ImportError:
        pass
