"""
SRT Ingest Module — receives SRT stream via FFmpeg.

Listens for incoming SRT connections (or connects to a caller)
and writes MPEG-TS chunks to disk for pipeline processing.
"""

import logging
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from core.ffmpeg_utils import ensure_ffmpeg
from core.module_base import BaseModule, ModuleState, PipelineData

logger = logging.getLogger("srt2web.module.srt_ingest")


class SRTIngest(BaseModule):
    """
    Receives an SRT stream and produces segmented MPEG-TS chunks.

    This module runs FFmpeg as a subprocess that listens for (or connects to)
    an SRT stream, and writes fixed-duration segments to the output directory.
    """

    def __init__(self, config: Optional[dict] = None, output_dir: str = "./output"):
        self._ffmpeg_path: Optional[str] = None
        self._ffmpeg_proc: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._output_dir = output_dir
        self._chunks_dir = ""
        self._last_chunk_index = -1

        # SRT config
        self._srt_port = 9000
        self._srt_mode = "listener"
        self._srt_latency_ms = 400
        self._srt_caller_address = ""
        self._chunk_duration = 4
        self._output_dir = Path(output_dir)  # Convert to Path
        super().__init__("srt_ingest", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        # SRT-specific config is usually passed from the parent srt section
        self._srt_port = config.get("listen_port", self._srt_port)
        self._srt_mode = config.get("mode", self._srt_mode)
        self._srt_latency_ms = config.get("latency_ms", self._srt_latency_ms)
        self._srt_caller_address = config.get("caller_address", self._srt_caller_address)
        self._chunk_duration = config.get("chunk_duration_sec", self._chunk_duration)
        self.enabled = True  # Always enabled — it's the input

    def start(self) -> None:
        """Start FFmpeg SRT receiver."""
        # Ensure any old process is dead first
        self.stop()
        time.sleep(0.5)  # Give the OS a moment to release the port

        self._last_chunk_index = -1  # CRITICAL: Reset index on start!
        self._state = ModuleState.STARTING

        # Ensure FFmpeg is available
        self._ffmpeg_path = ensure_ffmpeg()

        # Create chunks directory
        self._chunks_dir = Path(self._output_dir) / "chunks"
        self._chunks_dir.mkdir(parents=True, exist_ok=True)

        # Clean old chunks
        for f in self._chunks_dir.glob("chunk_*.ts"):
            try:
                f.unlink()
            except OSError:
                pass

        # Build SRT URL
        latency_us = self._srt_latency_ms * 1000
        if self._srt_mode == "caller" and self._srt_caller_address:
            srt_url = f"srt://{self._srt_caller_address}:{self._srt_port}" f"?mode=caller&latency={latency_us}"
        else:
            srt_url = f"srt://0.0.0.0:{self._srt_port}?mode=listener&latency={latency_us}"

        # Build FFmpeg command for segmented output
        chunk_pattern = str(self._chunks_dir / "chunk_%06d.ts")

        cmd = [
            self._ffmpeg_path,
            "-y",
            "-i",
            srt_url,
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

        logger.info(f"Starting SRT ingest: {' '.join(cmd)}")

        # Start FFmpeg process
        self._ffmpeg_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=(subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0),
        )

        # Monitor thread reads stderr for logs
        self._monitor_thread = threading.Thread(
            target=self._monitor_ffmpeg,
            daemon=True,
            name="srt-ingest-monitor",
        )
        self._monitor_thread.start()

        self._state = ModuleState.RUNNING

    def stop(self) -> None:
        """Stop FFmpeg SRT receiver."""
        self._state = ModuleState.STOPPING

        if self._ffmpeg_proc:
            try:
                # On Windows, terminate() doesn't always kill the tree of subprocesses
                # which can lead to bound ports (like 9000) staying busy.
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self._ffmpeg_proc.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    self._ffmpeg_proc.terminate()

                self._ffmpeg_proc.wait(timeout=2)
            except Exception as e:
                try:
                    self._ffmpeg_proc.kill()
                except:
                    pass
                logger.debug(f"Process cleanup: {e}")
            finally:
                self._ffmpeg_proc = None

        self._state = ModuleState.IDLE

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Not used directly — the ingest module produces data via get_next_chunk().
        This is a passthrough for pipeline compatibility.
        """
        return data

    def get_next_chunk(self) -> Optional[PipelineData]:
        """
        Check for new chunk files and return the next one as PipelineData.

        Returns None if no new chunk is available.
        """
        if not self._chunks_dir:
            return None

        # Ensure _chunks_dir is a Path object
        chunks_path = Path(self._chunks_dir) if isinstance(self._chunks_dir, str) else self._chunks_dir

        # Find all chunk files
        chunks = sorted(chunks_path.glob("chunk_*.ts"))

        if not chunks:
            return None

        # We process chunks in order, keeping track of what's been processed.
        # Only process completed chunks (not the one currently being written).
        # The last file in the sorted list might still be in progress,
        # so we process up to second-to-last.
        if len(chunks) < 2:
            return None

        # Find next unprocessed chunk
        next_index = self._last_chunk_index + 1

        # Parse index from filename (chunk_000000.ts → 0)
        processable = []
        for chunk_path in chunks[:-1]:  # Exclude last (in-progress)
            fname = chunk_path.name
            try:
                idx = int(fname.replace("chunk_", "").replace(".ts", ""))
                if idx > self._last_chunk_index:
                    processable.append((idx, chunk_path))
            except ValueError:
                continue

        if not processable:
            return None

        # Return the oldest unprocessed chunk
        processable.sort()
        idx, chunk_path = processable[0]
        self._last_chunk_index = idx

        from core.ffmpeg_utils import get_video_duration

        actual_duration = get_video_duration(chunk_path) or self._chunk_duration

        logger.info(f"New chunk available: {chunk_path}")

        return PipelineData(
            chunk_index=idx,
            timestamp=time.time(),
            duration=actual_duration,
            video_chunk_path=chunk_path,
        )

    def _monitor_ffmpeg(self) -> None:
        """Monitor FFmpeg stderr for log output."""
        if not self._ffmpeg_proc or not self._ffmpeg_proc.stderr:
            return

        try:
            for line in self._ffmpeg_proc.stderr:
                line = line.strip()
                if line:
                    # Don't spam debug with every FFmpeg line
                    if "error" in line.lower():
                        logger.error(f"[FFmpeg] {line}")
                    elif "warning" in line.lower():
                        logger.warning(f"[FFmpeg] {line}")
                    else:
                        logger.debug(f"[FFmpeg] {line}")
        except Exception:
            pass

        # Check if process exited
        if self._ffmpeg_proc:
            returncode = self._ffmpeg_proc.poll()
            if returncode is not None and returncode != 0:
                self._state = ModuleState.ERROR
                self._error_message = f"FFmpeg exited with code {returncode}"
                logger.error(self._error_message)

    def is_receiving(self) -> bool:
        """Check if FFmpeg process is running and receiving data."""
        if self._ffmpeg_proc is None:
            return False
        return self._ffmpeg_proc.poll() is None

    def get_srt_url(self) -> str:
        """Get the SRT URL that OBS/VMix should connect to."""
        latency_us = self._srt_latency_ms * 1000
        return f"srt://127.0.0.1:{self._srt_port}?mode=caller&latency={latency_us}"
