"""
SRT Output - Streams processed chunks via SRT protocol.

Pushes the processed (transcribed/translated/dubbed) video
to an SRT server or listener.
"""

import os
import subprocess
import threading
import logging
from typing import Optional

from core.module_base import PipelineData
from core.ffmpeg_utils import ensure_ffmpeg
from modules.outputs.base import BaseOutput

logger = logging.getLogger("srt2web.output.srt")


class SRTOutput(BaseOutput):
    """
    Outputs processed chunks to an SRT endpoint.
    
    Can act as:
    - Caller: connect to an SRT server
    - Listener: accept incoming SRT connections
    """

    def __init__(self, config: Optional[dict] = None):
        super().__init__("srt", config or {})
        self._ffmpeg_path: Optional[str] = None
        self._ffmpeg_proc: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        
        # SRT configuration
        self._url: str = "srt://localhost:9001"
        self._mode: str = "caller"  # caller, listener, rendezvous
        self._latency_ms: int = 200
        self._stream_id: str = ""
        self._passphrase: str = ""
        
        # Video settings
        self._video_bitrate: str = "2500k"
        self._audio_bitrate: str = "128k"
        self._codec: str = "libx264"
        self._preset: str = "medium"
        self._audio_codec: str = "aac"
        
        self._streaming: bool = False
        
        if config:
            self.configure(config)

    def configure(self, config: dict) -> None:
        """Apply configuration."""
        super().configure(config)
        
        self._url = config.get("url", "srt://localhost:9001")
        self._mode = config.get("mode", "caller")
        self._latency_ms = config.get("latency_ms", 200)
        self._stream_id = config.get("stream_id", "")
        self._passphrase = config.get("passphrase", "")
        
        self._video_bitrate = config.get("video_bitrate", "2500k")
        self._audio_bitrate = config.get("audio_bitrate", "128k")
        self._codec = config.get("video_codec", "libx264")
        self._preset = config.get("preset", "medium")
        self._audio_codec = config.get("audio_codec", "aac")

    def start(self) -> None:
        """Initialize SRT output."""
        self._ffmpeg_path = ensure_ffmpeg()
        logger.info(f"SRT output ready: {self._url} (mode: {self._mode})")

    def stop(self) -> None:
        """Stop SRT streaming."""
        self._streaming = False
        if self._ffmpeg_proc:
            try:
                self._ffmpeg_proc.terminate()
                self._ffmpeg_proc.wait(timeout=5)
            except Exception:
                try:
                    self._ffmpeg_proc.kill()
                except Exception:
                    pass
            self._ffmpeg_proc = None
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
        
        logger.info("SRT output stopped")

    def write(self, data: PipelineData) -> None:
        """
        Write chunk to SRT stream.
        
        Args:
            data: PipelineData with video chunk
        """
        video_path = data.video_chunk_path or data.mixed_audio_path
        if not video_path or not os.path.exists(video_path):
            return
        
        # Start streaming if not already
        if not self._streaming:
            self._start_streaming()
        
        # Write to FFmpeg stdin
        if self._ffmpeg_proc and self._ffmpeg_proc.stdin:
            try:
                with open(video_path, "rb") as f:
                    self._ffmpeg_proc.stdin.write(f.read())
            except BrokenPipeError:
                logger.warning("SRT connection lost, attempting reconnect...")
                self._restart_streaming()
            except Exception as e:
                logger.error(f"Error writing to SRT: {e}")

    def _start_streaming(self) -> None:
        """Start FFmpeg SRT streaming process."""
        if self._streaming and self._ffmpeg_proc and self._ffmpeg_proc.poll() is None:
            return
        
        # Build SRT URL with parameters
        srt_params = []
        if self._mode:
            srt_params.append(f"mode={self._mode}")
        if self._latency_ms:
            srt_params.append(f"latency={self._latency_ms}")
        if self._stream_id:
            srt_params.append(f"streamid={self._stream_id}")
        if self._passphrase:
            srt_params.append(f"passphrase={self._passphrase}")
        
        srt_url = self._url
        if srt_params:
            srt_url += "?" + "&".join(srt_params)
        
        cmd = [
            self._ffmpeg_path,
            "-y",
            "-re",  # Read input at native frame rate
            "-f", "mpegts",
            "-i", "pipe:0",
            "-c:v", self._codec,
            "-preset", self._preset,
            "-b:v", self._video_bitrate,
            "-c:a", self._audio_codec,
            "-b:a", self._audio_bitrate,
            "-f", "mpegts",
            srt_url,
        ]
        
        logger.info(f"Starting SRT stream: {srt_url}")
        
        self._ffmpeg_proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        # Monitor thread to log stderr
        def monitor():
            if self._ffmpeg_proc and self._ffmpeg_proc.stderr:
                for line in iter(self._ffmpeg_proc.stderr.readline, b""):
                    try:
                        line_str = line.decode("utf-8", errors="ignore").strip()
                        if line_str:
                            logger.debug(f"[SRT] {line_str}")
                    except Exception:
                        pass
        
        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()
        
        self._streaming = True
        logger.info("SRT streaming started")

    def _restart_streaming(self) -> None:
        """Restart SRT streaming after connection loss."""
        self._streaming = False
        if self._ffmpeg_proc:
            try:
                self._ffmpeg_proc.terminate()
            except Exception:
                pass
            self._ffmpeg_proc = None
        
        import time
        time.sleep(1)  # Brief pause before reconnect
        self._start_streaming()

    def is_streaming(self) -> bool:
        """Check if SRT streaming is active."""
        return (
            self._streaming
            and self._ffmpeg_proc is not None
            and self._ffmpeg_proc.poll() is None
        )

    def get_stream_info(self) -> dict:
        """Get SRT stream information."""
        return {
            "type": "srt",
            "url": self._url,
            "mode": self._mode,
            "latency_ms": self._latency_ms,
            "streaming": self.is_streaming(),
            "video_bitrate": self._video_bitrate,
            "audio_bitrate": self._audio_bitrate,
        }


# Auto-register
def _register():
    """Auto-register this output module."""
    try:
        from core.io_factory import OutputFactory
        OutputFactory.register("srt", SRTOutput)
    except ImportError:
        pass

_register()