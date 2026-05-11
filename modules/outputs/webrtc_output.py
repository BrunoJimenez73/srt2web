"""
WebRTC Output - Streaming via WebRTC protocol.

Provides WebRTC streaming capabilities with subtitle support via data channels.
"""

import logging
from pathlib import Path
from typing import Optional

from core.module_base import ModuleState, ModuleStatus, PipelineData
from core.output_sink import OutputSink

logger = logging.getLogger("srt2web.output.webrtc")


class WebRTCOutput(OutputSink):
    """
    WebRTC output sink using aiortc for streaming.

    Provides real-time streaming via WebRTC with support for:
    - Video/audio tracks
    - Data channel for subtitles
    """

    def __init__(self, config: dict):
        super().__init__("webrtc", config)

        # Import and initialize WebRTC engine
        from modules.webrtc_engine import WebRTCEngine

        self._engine = WebRTCEngine(config)

        # State
        self._engines: dict[str, any] = {"webrtc": self._engine}
        self._running = False

        # Directory
        self._output_dir = config.get("output_dir", "./output")

        logger.info("WebRTC output initialized")

    def configure(self, config: dict) -> None:
        """Apply configuration."""
        super().configure(config)
        if self._engine:
            self._engine.config.update(config)
        logger.info("WebRTC output configured")

    def start(self) -> None:
        """Start the WebRTC output and engine."""
        self._engine.set_output_dir(self._output_dir)
        self._engine.start()
        self._running = True
        logger.info("WebRTC output started")

    def stop(self) -> None:
        """Stop the WebRTC output and engine."""
        self._running = False
        self._engine.stop()
        logger.info("WebRTC output stopped")

    def write(self, data: PipelineData) -> None:
        """Write data to WebRTC stream - push paths for tracks to consume."""
        if not self._engine.running:
            return

        video_path = getattr(data, "video_path", None) or getattr(data, "video_chunk_path", None)
        if video_path and Path(video_path).exists():
            self._engine.push_video_path(video_path)

        audio_path = getattr(data, "mixed_audio_path", None)
        if audio_path and Path(audio_path).exists():
            self._engine.push_audio_path(audio_path)

        duration = getattr(data, "cumulative_duration", 0) or getattr(data, "duration", 0)
        if duration:
            self._engine.update_accumulated_duration(duration)

    def get_stream_info(self) -> dict:
        """Get WebRTC stream information."""
        return {"type": "webrtc", "engine": "aiortc", "status": "running" if self._running else "stopped"}

    @property
    def _webrtc_engine(self) -> Optional[any]:
        """Get the underlying WebRTC engine."""
        return self._engine

    def get_status(self) -> ModuleStatus:
        """Get status including WebRTC info."""
        return ModuleStatus(
            name="video_muxer",
            state=ModuleState.RUNNING if self._running else ModuleState.IDLE,
            enabled=True,
            processed_chunks=0,
            last_process_time_ms=0.0,
            extra={
                "encoder_mode": "webrtc",
                "actual_encoder": "webrtc",
                "using_gpu": False,
                "gpu_available": {},
                "encoder_label": "CPU (WebRTC)",
            },
        )


# Auto-register in factory
from core.io_factory import OutputFactory

OutputFactory.register("webrtc", WebRTCOutput)
