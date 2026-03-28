"""
Input Source - Base class for input sources that are also pipeline modules.

Provides a common interface for different types of input sources that can
be used as modules in the processing pipeline:
- SRT: SRT protocol for real-time streams
- File: Local video files
- RTMP: RTMP protocol
- Audio: Audio-only source
"""

from abc import abstractmethod
from typing import Optional
import logging

from core.module_base import BaseModule, PipelineData


class InputSource(BaseModule):
    """
    Base class for all input sources that are also pipeline modules.

    Attributes:
        name: Identifier for the input type
        config: Specific configuration for the input
    """

    def __init__(
        self,
        name: str,
        config: Optional[dict] = None,
        circuit_breaker = None,
        retry_strategy = None,
    ):
        super().__init__(name, config, circuit_breaker, retry_strategy)
        self.logger = logging.getLogger(f"srt2web.input.{name}")
        self._output_dir: str = ""
        self._is_listening = False

    @abstractmethod
    def start(self) -> None:
        """
        Start the input source.
        Must initialize resources (FFmpeg processes, open files, etc.)
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the input source.
        Must release all resources.
        """
        pass

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Get the next chunk of data from the input source.
        
        For input sources, this method produces data rather than processing it.
        
        Args:
            data: PipelineData object (ignored for input sources)
            
        Returns:
            PipelineData with the chunk data, or None if no data available
        """
        if not self._is_listening:
            return data
            
        try:
            chunk = self.get_next_chunk()
            if chunk:
                return chunk
        except Exception as e:
            self.logger.error(f"Error getting chunk from {self.name}: {e}")
            
        return data

    @abstractmethod
    def get_next_chunk(self) -> Optional[PipelineData]:
        """
        Obtain the next chunk of data from the input source.
        
        Returns:
            PipelineData with the chunk data, or None if no data available.
        """
        pass

    def is_receiving(self) -> bool:
        """
        Check if the source is active and receiving data.
        
        Returns:
            True if receiving data, False otherwise.
        """
        return self._is_listening and self._check_is_receiving()

    @abstractmethod
    def _check_is_receiving(self) -> bool:
        """
        Internal method to check if the source is actually receiving data.
        Must be implemented by subclasses.
        
        Returns:
            True if receiving data, False otherwise.
        """
        pass

    def get_connection_info(self) -> dict:
        """
        Get connection information for display to the user.
        
        Returns:
            Dict with relevant information (URL, port, etc.)
        """
        return {"type": self.name}

    def set_output_dir(self, output_dir: str) -> None:
        """Set the output directory for temporary files."""
        self._output_dir = output_dir

    def configure(self, config: dict) -> None:
        """
        Apply input-specific configuration.
        Override in subclasses to handle specific configuration.
        """
        super().configure(config)
        self.config = config
