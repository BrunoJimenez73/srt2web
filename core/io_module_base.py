"""
IO Module Base - Base class for Input/Output modules.

Provides a unified interface that combines BaseModule with I/O capabilities.
This allows Input and Output to be treated as modules in the pipeline.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
import logging

from core.module_base import BaseModule, ModuleState, ModuleStatus, PipelineData


class IOModuleType(str):
    """Types of I/O modules."""
    INPUT = "input"
    OUTPUT = "output"


class IOBaseModule(BaseModule, ABC):
    """
    Abstract base class for Input/Output modules.
    
    Extends BaseModule with I/O specific functionality:
    - Connection state management
    - I/O statistics (chunks read/written)
    - Connection info for UI
    
    Subclasses must implement:
    - start() / stop() - from BaseModule
    - _do_io_process() - produce (input) or consume (output) data
    """

    def __init__(
        self,
        name: str,
        module_type: IOModuleType,
        config: Optional[dict] = None,
    ):
        super().__init__(name, config)
        self.module_type = module_type
        self._io_state = ModuleState.IDLE
        self._chunks_processed = 0
        self._connection_info = {}
        self._is_connected = False

    @property
    def io_state(self) -> ModuleState:
        """Get I/O specific state."""
        return self._io_state

    @property
    def is_connected(self) -> bool:
        """Check if I/O is connected/active."""
        return self._is_connected

    def get_io_stats(self) -> dict:
        """Get I/O statistics."""
        return {
            "chunks_processed": self._chunks_processed,
            "is_connected": self._is_connected,
            "io_state": self._io_state.value,
        }

    def get_connection_info(self) -> dict:
        """
        Get connection information for UI display.
        Override in subclasses to provide specific info.
        """
        return self._connection_info

    def configure(self, config: dict) -> None:
        """Apply configuration to this I/O module."""
        super().configure(config)
        
        io_config = config.get(f"{self.module_type.value}_config", {})
        if io_config:
            self._configure_io(io_config)

    @abstractmethod
    def _configure_io(self, config: dict) -> None:
        """
        Configure I/O specific settings.
        Override in subclasses to handle specific config.
        """
        pass

    @abstractmethod
    def _do_io_process(self, data: Optional[PipelineData]) -> PipelineData:
        """
        Process I/O operation.
        
        For INPUT modules: Produces data (gets next chunk from source)
        For OUTPUT modules: Consumes data (writes to destination)
        
        Args:
            data: PipelineData (for output modules, data to write)
            
        Returns:
            PipelineData (for input modules, data from source; for output, passes through)
        """
        pass

    def _update_connection_state(self, connected: bool) -> None:
        """Update connection state."""
        self._is_connected = connected
        if connected and self._state == ModuleState.IDLE:
            self._io_state = ModuleState.RUNNING
        elif not connected:
            self._io_state = ModuleState.IDLE

    def process(self, data: PipelineData) -> PipelineData:
        """
        Process I/O operation.
        
        For INPUT: Returns new PipelineData with fresh chunk
        For OUTPUT: Writes data and returns it unchanged
        """
        if not self.enabled or self._state == ModuleState.DISABLED:
            return data

        try:
            result = self._do_io_process(data)
            if result is not None:
                self._chunks_processed += 1
            return result
        except Exception as e:
            self.logger.error(f"I/O error in {self.name}: {e}")
            self._is_connected = False
            self._io_state = ModuleState.ERROR
            raise

    def get_status(self) -> ModuleStatus:
        """Get module status including I/O info."""
        status = super().get_status()
        status.extra.update(self.get_io_stats())
        status.extra["connection_info"] = self.get_connection_info()
        return status

    def reset_error(self) -> None:
        """Clear error state."""
        super().reset_error()
        self._io_state = ModuleState.IDLE


class InputModule(IOBaseModule):
    """
    Base class for Input modules.
    
    Input modules PRODUCE data - they read from sources
    (SRT, RTMP, File) and create PipelineData chunks.
    """
    
    def __init__(self, name: str, config: Optional[dict] = None):
        super().__init__(name, IOModuleType.INPUT, config)
        self._source_type = "unknown"
        self._last_chunk_time = 0.0

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        For InputModule, _do_process is called but we actually
        produce data in _do_io_process.
        
        This wraps _do_io_process to match BaseModule interface.
        """
        return self._do_io_process(None)

    @abstractmethod
    def _configure_io(self, config: dict) -> None:
        """Configure input specific settings."""
        pass

    def get_source_type(self) -> str:
        """Get the type of input source."""
        return self._source_type


class OutputModule(IOBaseModule):
    """
    Base class for Output modules.
    
    Output modules CONSUME data - they write PipelineData
    to destinations (HLS, SRT, RTMP, File).
    """
    
    def __init__(self, name: str, config: Optional[dict] = None):
        super().__init__(name, IOModuleType.OUTPUT, config)
        self._sink_type = "unknown"

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        For OutputModule, _do_process writes data to output.
        
        This wraps _do_io_process to match BaseModule interface.
        """
        return self._do_io_process(data)

    @abstractmethod
    def _configure_io(self, config: dict) -> None:
        """Configure output specific settings."""
        pass

    def get_sink_type(self) -> str:
        """Get the type of output sink."""
        return self._sink_type
