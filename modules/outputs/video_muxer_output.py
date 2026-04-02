"""
Video Muxer Output - Unified output with selectable engine.

Provides a single output sink that can use different engines:
- HLS: HTTP Live Streaming (default, compatible)
- WebRTC: Real-time streaming (low latency)

The engine can be switched via configuration.
"""

import os
import logging
from typing import Optional

from core.module_base import PipelineData
from core.output_sink import OutputSink
from modules.outputs.hls_output import HLSOutput

logger = logging.getLogger("srt2web.output.video_muxer")


class VideoMuxerOutput(OutputSink):
    """
    Output sink that delegates to a specific engine.
    
    Currently supports:
    - HLS engine (default): Compatible with all browsers
    - WebRTC engine (planned): Ultra-low latency
    """
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__("video_muxer", config or {})
        self._engine_type = "hls"  # hls, webrtc
        self._engine = None
        self._engines = {}
        
        if config:
            self.configure(config)
    
    def configure(self, config: dict) -> None:
        """Configure engine and its settings."""
        super().configure(config)
        
        # Get engine type
        self._engine_type = config.get("engine", "hls")
        
        # Configure appropriate engine
        if self._engine_type == "hls":
            if "hls" not in self._engines:
                self._engines["hls"] = HLSOutput(config)
            self._engine = self._engines["hls"]
            self._engine.configure(config)
        elif self._engine_type == "webrtc":
            # TODO: Implement WebRTC engine
            # For now, fallback to HLS
            logger.warning("WebRTC engine not yet implemented, using HLS")
            self._engine_type = "hls"
            if "hls" not in self._engines:
                self._engines["hls"] = HLSOutput(config)
            self._engine = self._engines["hls"]
            self._engine.configure(config)
        else:
            raise ValueError(f"Unknown engine type: {self._engine_type}")
        
        logger.info(f"VideoMuxer configured with engine: {self._engine_type}")
    
    def start(self) -> None:
        """Start the selected engine."""
        if self._engine:
            self._engine.start()
        logger.info(f"VideoMuxer started with {self._engine_type} engine")
    
    def stop(self) -> None:
        """Stop all engines."""
        for engine in self._engines.values():
            engine.stop()
        logger.info("VideoMuxer stopped")
    
    def write(self, data: PipelineData) -> None:
        """Write data to the active engine."""
        if self._engine:
            self._engine.write(data)
        else:
            logger.error("No engine configured")
    
    def get_stream_info(self) -> dict:
        """Get stream info from active engine."""
        info = {
            "type": "video_muxer",
            "engine": self._engine_type,
        }
        if self._engine:
            engine_info = self._engine.get_stream_info()
            info.update(engine_info)
        return info
    
    def get_engine_status(self) -> dict:
        """Get status of all engines."""
        return {
            "current_engine": self._engine_type,
            "available_engines": ["hls"],  # webrtc when implemented
            "hls": self._engines.get("hls").get_stream_info() if "hls" in self._engines else None,
            "webrtc": None,  # TODO
        }


# Auto-register
def _register():
    """Auto-register this output module."""
    try:
        from core.io_factory import OutputFactory
        OutputFactory.register("video_muxer", VideoMuxerOutput)
        # Keep aliases for backward compatibility
        OutputFactory.register("web", VideoMuxerOutput)
        OutputFactory.register("hls", VideoMuxerOutput)
    except ImportError:
        pass

_register()