"""
WebRTC Output - Streaming via WebRTC protocol.

Provides WebRTC streaming capabilities with subtitle support via data channels.
"""

import logging
import threading
from typing import Optional, Dict

from core.output_sink import OutputSink
from core.module_base import PipelineData, ModuleStatus, ModuleState

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
        self._engines: Dict[str, any] = {'webrtc': self._engine}
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
        """Write data to WebRTC stream."""
        # In WebRTC mode, the engine handles streaming automatically
        # The video/audio tracks pull from the pipeline output
        if self._engine.running:
            pass  # Engine handles streaming internally

    def get_stream_info(self) -> dict:
        """Get WebRTC stream information."""
        return {
            "type": "webrtc",
            "engine": "aiortc",
            "status": "running" if self._running else "stopped"
        }

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
            }
        )


# Auto-register in factory
from core.io_factory import OutputFactory
OutputFactory.register("webrtc", WebRTCOutput)