"""
RTMP Input - Receives RTMP streams via FFmpeg.

Supports:
- RTMP Pull: Connect to external RTMP server
- RTMP Push: Act as RTMP server (receive from OBS)

FFmpeg handles both modes natively.
"""

import contextlib
import logging
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from core.ffmpeg_utils import ensure_ffmpeg
from core.input_source import InputSource
from core.module_base import ModuleState, ModuleStatus
from core.subprocess_utils import get_creation_flags

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

    def __init__(self, config: dict[str, Any] | None = None):
        self._ffmpeg_path: str | None = None
        self._ffmpeg_proc: subprocess.Popen[Any] | None = None
        self._monitor_thread: threading.Thread | None = None
        self._output_dir: str = "./output"
        self._chunks_dir: str = ""
        self._last_chunk_index = -1
        self._last_chunk_mtime: float | None = None
        self._cumulative_duration: float = 0.0  # Track cumulative duration for sync

        super().__init__("rtmp", config or {})
        self._url: str = ""
        self._mode: str = "pull"
        self._chunk_duration: int = 10
        self._receiving: bool = False
        self._watchdog: Any | None = None

        # GPU info for hwaccel
        self._gpu_info = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False}
        self._hwaccel_enabled = False
        self._hwaccel_device = "0"

        if config:
            self.configure(config)

    def configure(self, config: dict[str, Any]) -> None:
        """Apply configuration."""
        super().configure(config)

        self._url = config.get("url", "rtmp://localhost/live/stream")
        self._mode = config.get("mode", "pull")
        new_chunk_duration = config.get("chunk_duration_sec", self._chunk_duration)
        if new_chunk_duration != self._chunk_duration:
            logger.info(
                f"RTMP chunk_duration changed: {self._chunk_duration}s → {new_chunk_duration}s, resetting cumulative"
            )
            self._cumulative_duration = 0.0
        self._chunk_duration = new_chunk_duration
        self._output_dir = config.get("output_dir", self._output_dir)

    def set_output_dir(self, output_dir: str) -> None:
        """Set the output directory for chunks."""
        self._output_dir = output_dir
        self._chunks_dir = str(Path(output_dir) / "chunks")

    def start(self) -> None:
        """Start FFmpeg RTMP receiver."""
        self.stop()
        time.sleep(0.5)

        self._last_chunk_index = -1

        self._ffmpeg_path = ensure_ffmpeg()

        self._chunks_dir = str(Path(self._output_dir) / "chunks")
        Path(self._chunks_dir).mkdir(parents=True, exist_ok=True)

        # Detectar soporte GPU para hwaccel
        from core.ffmpeg_utils import check_gpu_support

        self._gpu_info = check_gpu_support(self._ffmpeg_path)
        logger.info(f"RTMP Input GPU support: {self._gpu_info}")

        logger.info(f"RTMP Input URL being used: {self._url}")
        logger.info(f"RTMP Input mode: {self._mode}")

        # Habilitar hwaccel si hay GPU disponible
        if self._gpu_info.get("nvenc"):
            self._hwaccel_enabled = True
            logger.info("RTMP Input: Using NVDEC hardware acceleration")
        elif self._gpu_info.get("qsv"):
            self._hwaccel_enabled = True
            logger.info("RTMP Input: Using QSV hardware acceleration")
        elif self._gpu_info.get("vaapi"):
            self._hwaccel_enabled = True
            logger.info("RTMP Input: Using VAAPI hardware acceleration")
        else:
            self._hwaccel_enabled = False
            logger.info("RTMP Input: No GPU acceleration available, using CPU")

        for f in Path(self._chunks_dir).glob("chunk_*.ts"):
            with contextlib.suppress(OSError):
                f.unlink()

        # Reset cumulative duration tracking
        self._cumulative_duration = 0.0

        chunk_pattern = str(Path(self._chunks_dir) / "chunk_%06d.ts")

        # Construir comando con soporte hwaccel
        cmd = [self._ffmpeg_path, "-y"]

        # Añadir hwaccel si hay GPU disponible
        if self._hwaccel_enabled:
            if self._gpu_info.get("nvenc"):
                cmd.extend(["-hwaccel", "cuda", "-hwaccel_device", self._hwaccel_device])
            elif self._gpu_info.get("qsv"):
                cmd.extend(["-hwaccel", "qsv", "-hwaccel_device", self._hwaccel_device])
            elif self._gpu_info.get("vaapi"):
                cmd.extend(["-hwaccel", "vaapi"])

        # Resto del comando - use listen mode for server
        cmd.extend(
            [
                "-rtmp_listen",
                "1",  # FFmpeg acts as RTMP server
                "-i",
                self._url.split("?")[0],  # Use URL without query params
                "-fflags",
                "nobuffer",
                "-analyzeduration",
                "10000000",
                "-probesize",
                "10000000",
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                "-bsf:v",
                "h264_mp4toannexb",  # Convert from MP4 to AnnexB for TS
                "-f",
                "segment",
                "-segment_time",
                str(self._chunk_duration),
                "-segment_format",
                "mpegts",
                "-reset_timestamps",
                "1",
                "-max_muxing_queue_size",
                "8192",
                chunk_pattern,
            ]
        )

        logger.info(f"Starting RTMP input in LISTEN mode: {self._url}")

        # Debug: log the full command
        logger.info(f"FFmpeg command: {' '.join(cmd)}")

        # Use CREATE_NO_WINDOW on Windows to avoid console popup
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = get_creation_flags()

        # Capture stdout/stderr to see what FFmpeg outputs
        self._ffmpeg_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            creationflags=creation_flags,
        )

        logger.info(f"FFmpeg started with PID {self._ffmpeg_proc.pid}, URL: {self._url}")

        # Small delay to let FFmpeg start
        time.sleep(0.5)

        # Check if process is still running
        if self._ffmpeg_proc.poll() is not None:
            # Process exited immediately - try to read output
            try:
                stdout = self._ffmpeg_proc.stdout
                output = stdout.read(2000) if stdout else ""
                logger.error(f"FFmpeg exited immediately. Output: {output}")
            except Exception:
                logger.error(f"FFmpeg exited immediately with code {self._ffmpeg_proc.returncode}")
            # Continue anyway - the process might work if we give it time

        self._monitor_thread = threading.Thread(
            target=self._monitor_ffmpeg,
            daemon=True,
            name="rtmp-monitor",
        )
        self._monitor_thread.start()

        self._receiving = True

        # Disable watchdog for now - it causes thread join issues on restart
        # The pipeline will handle error detection
        self._watchdog = None
        logger.info("RTMP input started (watchdog disabled)")

    def _restart(self) -> None:
        """Restart the RTMP receiver (called from watchdog thread)."""
        logger.info("Restarting RTMP receiver...")
        self._ffmpeg_proc = None
        # Don't call self.start() from watchdog thread - it will be called externally

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
                        creationflags=get_creation_flags(),
                    )
                else:
                    self._ffmpeg_proc.terminate()
                self._ffmpeg_proc.wait(timeout=2)
            except Exception:
                with contextlib.suppress(Exception):
                    self._ffmpeg_proc.kill()
            finally:
                self._ffmpeg_proc = None

        self._receiving = False

    def _monitor_ffmpeg(self) -> None:
        """Monitor FFmpeg stdout for log output."""
        if not self._ffmpeg_proc or not self._ffmpeg_proc.stdout:
            return

        try:
            while True:
                # Check if process is still running
                if self._ffmpeg_proc.poll() is not None:
                    break

                # Read available stdout
                line = self._ffmpeg_proc.stdout.readline()
                if not line:
                    # Check if process ended
                    if self._ffmpeg_proc.poll() is not None:
                        break
                    time.sleep(0.1)
                    continue

                line = line.strip()
                if line:
                    if "error" in line.lower() or "Error" in line:
                        logger.error(f"[FFmpeg] {line}")
                    elif "warning" in line.lower() or "Warning" in line:
                        logger.warning(f"[FFmpeg] {line}")
                    elif (
                        "input" in line.lower()
                        or "output" in line.lower()
                        or "stream" in line.lower()
                        or "listening" in line.lower()
                    ):
                        logger.info(f"[FFmpeg] {line}")
                    else:
                        logger.debug(f"[FFmpeg] {line}")
        except Exception as e:
            logger.warning(f"Error in monitor: {e}")
            pass

        # Final check
        if self._ffmpeg_proc:
            returncode = self._ffmpeg_proc.poll()
            if returncode is not None:
                self._receiving = False
                logger.error(f"FFmpeg exited with code {returncode}")

    def get_next_chunk(self) -> Any | None:
        """Get next available chunk."""
        if not self._chunks_dir:
            return None

        chunks = sorted(Path(self._chunks_dir).glob("chunk_*.ts"))
        _t0 = time.perf_counter()

        if not chunks or len(chunks) < 2:
            return None

        processable = []
        for chunk_path in chunks[:-1]:
            fname = chunk_path.name
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

        # Medir duración real vía mtime entre chunks consecutivos.
        # Corregimos cumulative_duration retroactivamente para eliminar deriva.
        current_mtime = chunk_path.stat().st_mtime
        if self._last_chunk_mtime is not None:
            prev_duration = current_mtime - self._last_chunk_mtime
            prev_duration = max(0.5, min(prev_duration, self._chunk_duration * 2))
            self._cumulative_duration += prev_duration - self._chunk_duration
        self._last_chunk_mtime = current_mtime

        chunk_cumulative = self._cumulative_duration
        self._cumulative_duration += self._chunk_duration

        logger.info(f"New RTMP chunk: {chunk_path} (cumulative: {chunk_cumulative:.3f}s)")

        return PipelineData(
            chunk_index=idx,
            timestamp=time.time(),
            duration=self._chunk_duration,
            cumulative_duration=chunk_cumulative,
            video_chunk_path=str(chunk_path),
        )

    def is_receiving(self) -> bool:
        """Check if RTMP stream is being received."""
        if self._ffmpeg_proc is None:
            return False
        return self._ffmpeg_proc.poll() is None and self._receiving

    def get_connection_info(self) -> dict[str, Any]:
        """Get connection information."""
        return {
            "type": "rtmp",
            "mode": self._mode,
            "url": self._url,
            "receiving": self.is_receiving(),
        }

    def get_status(self) -> ModuleStatus:
        """Get status including GPU acceleration info."""
        return ModuleStatus(
            name="input",
            state=ModuleState.RUNNING if self.is_receiving() else ModuleState.IDLE,
            enabled=True,
            processed_chunks=self._last_chunk_index + 1 if self._last_chunk_index >= 0 else 0,
            last_process_time_ms=0.0,
            extra={
                "using_gpu": self._hwaccel_enabled,
                "gpu_info": self._gpu_info,
                "encoder_label": "NVDEC"
                if self._gpu_info.get("nvenc")
                else "QSV"
                if self._gpu_info.get("qsv")
                else "VAAPI"
                if self._gpu_info.get("vaapi")
                else "CPU",
                "hwaccel": self._hwaccel_enabled,
            },
        )


_input_class = RTMPInput


def _register() -> None:
    """Auto-register this input module."""
    try:
        from core.io_factory import InputFactory

        InputFactory.register("rtmp", RTMPInput)
    except ImportError:
        pass
