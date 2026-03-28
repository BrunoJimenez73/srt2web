"""
RTMP Output - Streams to RTMP servers.

Supports pushing the processed stream to external RTMP servers
(e.g., YouTube, Twitch, or custom RTMP endpoints).
"""

import os
import sys
import time
import logging
import subprocess
import threading
from typing import Optional

from core.output_sink import OutputSink
from core.module_base import PipelineData
from core.ffmpeg_utils import ensure_ffmpeg, get_video_duration

logger = logging.getLogger("srt2web.output.rtmp")


class RTMPOutput(OutputSink):
    """
    Outputs processed chunks to an RTMP server.

    This allows streaming the processed (transcribed/translated/dubbed)
    video to external platforms like YouTube, Twitch, or custom servers.
    """

    name = "rtmp_output"

    def __init__(self, config: Optional[dict] = None):
        self._config: dict = config or {}
        self._ffmpeg_path: Optional[str] = None
        self._ffmpeg_proc: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None

        self._url: str = ""
        self._video_bitrate: str = "2500k"
        self._audio_bitrate: str = "128k"
        self._codec: str = "libx264"
        self._preset: str = "medium"
        self._audio_codec: str = "aac"
        self._streaming: bool = False
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
        self._video_bitrate = config.get("video_bitrate", "2500k")
        self._audio_bitrate = config.get("audio_bitrate", "128k")
        self._codec = config.get("video_codec", "libx264")
        self._preset = config.get("preset", "medium")
        self._audio_codec = config.get("audio_codec", "aac")

    def start(self) -> None:
        """Start FFmpeg RTMP streamer."""
        self.stop()

        self._ffmpeg_path = ensure_ffmpeg()

        cmd = [
            self._ffmpeg_path,
            "-y",
            "-listen",
            "1",
            "-i",
            "pipe:0",
            "-c:v",
            self._codec,
            "-preset",
            self._preset,
            "-b:v",
            self._video_bitrate,
            "-c:a",
            self._audio_codec,
            "-b:a",
            self._audio_bitrate,
            "-f",
            "flv",
            self._url,
        ]

        logger.info(f"Starting RTMP output: pushing to {self._url}")

        self._ffmpeg_proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            ),
        )

        self._monitor_thread = threading.Thread(
            target=self._monitor_ffmpeg,
            daemon=True,
            name="rtmp-output-monitor",
        )
        self._monitor_thread.start()

        self._streaming = True

        try:
            from core.watchdog import FFmpegWatchdog

            self._watchdog = FFmpegWatchdog(
                hang_timeout=30,
                max_restarts=5,
            )
            self._watchdog.attach_process(
                self._ffmpeg_proc,
                "RTMP Output",
                restart_callback=self._restart,
            )
            self._watchdog.start()
        except ImportError:
            pass

    def _restart(self) -> None:
        """Restart the RTMP output."""
        logger.info("Restarting RTMP output...")
        self._ffmpeg_proc = None
        self.start()

    def stop(self) -> None:
        """Stop FFmpeg RTMP streamer."""
        if self._watchdog:
            self._watchdog.stop()
            self._watchdog = None

        if self._ffmpeg_proc:
            try:
                self._ffmpeg_proc.stdin.close()
            except Exception:
                pass

            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self._ffmpeg_proc.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    self._ffmpeg_proc.terminate()
                self._ffmpeg_proc.wait(timeout=5)
            except Exception:
                try:
                    self._ffmpeg_proc.kill()
                except:
                    pass
            finally:
                self._ffmpeg_proc = None

        self._streaming = False

    def _monitor_ffmpeg(self) -> None:
        """Monitor FFmpeg stderr."""
        if not self._ffmpeg_proc or not self._ffmpeg_proc.stderr:
            return

        try:
            for line in self._ffmpeg_proc.stderr:
                line = line.strip()
                if line:
                    if "error" in line.lower():
                        logger.error(f"[FFmpeg RTMP] {line}")
                    elif "warning" in line.lower():
                        logger.warning(f"[FFmpeg RTMP] {line}")
                    else:
                        logger.debug(f"[FFmpeg RTMP] {line}")
        except Exception:
            pass

        if self._ffmpeg_proc:
            returncode = self._ffmpeg_proc.poll()
            if returncode is not None:
                self._streaming = False
                if returncode != 0:
                    logger.error(f"RTMP FFmpeg exited with code {returncode}")

    def write(self, data: PipelineData) -> None:
        """
        Write processed chunk to RTMP stream.

        Args:
            data: PipelineData with video_chunk_path or mixed_audio_path
        """
        if not self._streaming or not self._ffmpeg_proc:
            return

        video_path = data.video_chunk_path or data.mixed_audio_path
        if not video_path or not os.path.exists(video_path):
            return

        try:
            if self._ffmpeg_proc.stdin:
                with open(video_path, "rb") as f:
                    self._ffmpeg_proc.stdin.write(f.read())
        except BrokenPipeError:
            logger.warning("RTMP connection lost, attempting reconnect...")
            self._restart()
        except Exception as e:
            logger.error(f"Error writing to RTMP: {e}")

    def is_streaming(self) -> bool:
        """Check if RTMP streaming is active."""
        return (
            self._streaming
            and self._ffmpeg_proc is not None
            and self._ffmpeg_proc.poll() is None
        )

    def get_stream_info(self) -> dict:
        """Get RTMP stream information."""
        return {
            "type": "rtmp",
            "url": self._url,
            "video_bitrate": self._video_bitrate,
            "audio_bitrate": self._audio_bitrate,
            "codec": self._codec,
            "preset": self._preset,
            "streaming": self.is_streaming(),
        }


def _register():
    """Auto-register this output module."""
    try:
        from core.io_factory import OutputFactory

        OutputFactory.register("rtmp", RTMPOutput)
    except ImportError:
        pass
