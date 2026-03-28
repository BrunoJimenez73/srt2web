"""
Output Sink - Base class for output sinks that are also pipeline modules.

Provides a common interface for different types of output sinks that can
be used as modules in the processing pipeline:
- Web/HLS: Streaming via HLS for browser
- SRT: SRT protocol for re-transmission
- RTMP: RTMP protocol (YouTube, Twitch, etc.)
- Audio: Audio-only output
"""

from abc import abstractmethod
from typing import Optional
import logging

from core.module_base import BaseModule, PipelineData


class OutputSink(BaseModule):
    """
    Base class for all output sinks that are also pipeline modules.

    Attributes:
        name: Identifier for the output type
        config: Specific configuration for the output
    """

    def __init__(
        self,
        name: str,
        config: Optional[dict] = None,
        circuit_breaker = None,
        retry_strategy = None,
    ):
        super().__init__(name, config, circuit_breaker, retry_strategy)
        self.logger = logging.getLogger(f"srt2web.output.{name}")
        self._output_dir: str = ""
        self._is_writing = False

    @abstractmethod
    def start(self) -> None:
        """
        Start the output sink.
        Must initialize necessary resources.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the output sink.
        Must release all resources.
        """
        pass

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Write data to the output sink.
        
        For output sinks, this method consumes data rather than producing it.
        
        Args:
            data: PipelineData with the data to write
            
        Returns:
            PipelineData (unchanged, pass-through)
        """
        if not self._is_writing or not data:
            return data
            
        try:
            self.write(data)
        except Exception as e:
            self.logger.error(f"Error writing to {self.name}: {e}")
            
        return data

    @abstractmethod
    def write(self, data: PipelineData) -> None:
        """
        Write data to the output destination.

        Args:
            PipelineData with the data to write.
        """
        pass

    def get_stream_info(self) -> dict:
        """
        Get stream information for the client.

        Returns:
            Dict with URLs, ports, etc.
        """
        return {"type": self.name}

    def set_output_dir(self, output_dir: str) -> None:
        """Set the output directory."""
        self._output_dir = output_dir

    def is_streaming(self) -> bool:
        """
        Check if the output is actively streaming.

        Returns:
            True if streaming, False otherwise.
        """
        return self._is_writing and self._check_is_streaming()

    @abstractmethod
    def _check_is_streaming(self) -> bool:
        """
        Internal method to check if the output is actually streaming.
        Must be implemented by subclasses.

        Returns:
            True if streaming, False otherwise.
        """
        pass

    def configure(self, config: dict) -> None:
        """
        Apply output-specific configuration.
        Override in subclasses to handle specific configuration.
        """
        super().configure(config)
        self.config = config
