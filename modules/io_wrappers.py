"""
I/O Module Wrappers - Adapters to convert InputSource/OutputSink to modules.

These wrappers allow existing InputSource and OutputSink implementations
to work as modules in the pipeline, with toggle, state, and metrics.
"""

import logging
from typing import Optional, Dict, Any

from core.module_base import (
    BaseModule, ModuleState, ModuleStatus, PipelineData
)
from core.input_source import InputSource
from core.output_sink import OutputSink


logger = logging.getLogger("srt2web.io_wrappers")


class InputModuleWrapper(BaseModule):
    """
    Wrapper that converts an InputSource into a pipeline module.
    
    This allows InputSource to:
    - Have enable/disable toggle
    - Report state like other modules
    - Integrate into the pipeline uniformly
    
    The wrapper acts as an INPUT module that produces PipelineData.
    """
    
    # Class property to identify input modules
    is_input_module = True
    
    def __init__(
        self,
        name: str,
        input_source: InputSource,
        config: Optional[dict] = None,
    ):
        super().__init__(name, config)
        self._input_source = input_source
        self._chunks_received = 0
        self._is_listening = False
        
        if config:
            self.configure(config)

    @property
    def input_source(self) -> InputSource:
        """Get the wrapped InputSource."""
        return self._input_source

    def configure(self, config: dict) -> None:
        """Apply configuration to wrapper and input source."""
        super().configure(config)
        
        input_config = config.get("input_config", {})
        if input_config:
            self._input_source.configure(input_config)

    def start(self) -> None:
        """Start the input source."""
        if not self.enabled:
            self._state = ModuleState.DISABLED
            return
            
        try:
            self._state = ModuleState.STARTING
            self._input_source.start()
            self._is_listening = True
            self._state = ModuleState.RUNNING
            logger.info(f"Input module {self.name} started")
        except Exception as e:
            self._state = ModuleState.ERROR
            self._error_message = str(e)
            logger.error(f"Failed to start input {self.name}: {e}")
            raise

    def stop(self) -> None:
        """Stop the input source."""
        try:
            self._state = ModuleState.STOPPING
            self._input_source.stop()
            self._is_listening = False
            self._state = ModuleState.IDLE
            logger.info(f"Input module {self.name} stopped")
        except Exception as e:
            logger.error(f"Error stopping input {self.name}: {e}")
            self._state = ModuleState.ERROR

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        For input modules, we PRODUCE data instead of processing it.
        
        This is called by the pipeline to get the next chunk.
        Returns new PipelineData with data from input source.
        """
        if not self._is_listening:
            return data
            
        try:
            chunk = self._input_source.get_next_chunk()
            if chunk:
                self._chunks_received += 1
                return chunk
        except Exception as e:
            logger.error(f"Error getting chunk from {self.name}: {e}")
            
        return data

    def is_receiving(self) -> bool:
        """Check if input is receiving data."""
        return self._is_listening and self._input_source.is_receiving()

    def get_status(self) -> ModuleStatus:
        """Get status including input-specific info."""
        status = super().get_status()
        status.extra["input_type"] = self._input_source.name
        status.extra["is_receiving"] = self.is_receiving()
        status.extra["chunks_received"] = self._chunks_received
        status.extra["connection_info"] = self._input_source.get_connection_info()
        return status

    def get_connection_info(self) -> dict:
        """Get connection info for UI."""
        return self._input_source.get_connection_info()


class OutputModuleWrapper(BaseModule):
    """
    Wrapper that converts an OutputSink into a pipeline module.
    
    This allows OutputSink to:
    - Have enable/disable toggle
    - Report state like other modules
    - Integrate into the pipeline uniformly
    
    The wrapper acts as an OUTPUT module that consumes PipelineData.
    """
    
    # Class property to identify output modules
    is_output_module = True
    
    def __init__(
        self,
        name: str,
        output_sink: OutputSink,
        config: Optional[dict] = None,
    ):
        super().__init__(name, config)
        self._output_sink = output_sink
        self._chunks_written = 0
        self._is_writing = False
        
        if config:
            self.configure(config)

    @property
    def output_sink(self) -> OutputSink:
        """Get the wrapped OutputSink."""
        return self._output_sink

    def configure(self, config: dict) -> None:
        """Apply configuration to wrapper and output sink."""
        super().configure(config)
        
        output_config = config.get("output_config", {})
        if output_config:
            self._output_sink.configure(output_config)

    def start(self) -> None:
        """Start the output sink."""
        if not self.enabled:
            self._state = ModuleState.DISABLED
            return
            
        try:
            self._state = ModuleState.STARTING
            self._output_sink.start()
            self._is_writing = True
            self._state = ModuleState.RUNNING
            logger.info(f"Output module {self.name} started")
        except Exception as e:
            self._state = ModuleState.ERROR
            self._error_message = str(e)
            logger.error(f"Failed to start output {self.name}: {e}")
            raise

    def stop(self) -> None:
        """Stop the output sink."""
        try:
            self._state = ModuleState.STOPPING
            self._output_sink.stop()
            self._is_writing = False
            self._state = ModuleState.IDLE
            logger.info(f"Output module {self.name} stopped")
        except Exception as e:
            logger.error(f"Error stopping output {self.name}: {e}")
            self._state = ModuleState.ERROR

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        For output modules, we CONSUME data (write to output).
        
        This is called by the pipeline to write processed data.
        Returns the data unchanged (pass-through).
        """
        if not self._is_writing or not data:
            return data
            
        try:
            self._output_sink.write(data)
            self._chunks_written += 1
        except Exception as e:
            logger.error(f"Error writing to {self.name}: {e}")
            
        return data

    def get_stream_info(self) -> dict:
        """Get stream info for UI."""
        return self._output_sink.get_stream_info()

    def get_status(self) -> ModuleStatus:
        """Get status including output-specific info."""
        status = super().get_status()
        status.extra["output_type"] = self._output_sink.name
        status.extra["is_writing"] = self._is_writing
        status.extra["chunks_written"] = self._chunks_written
        status.extra["stream_info"] = self._output_sink.get_stream_info()
        return status

    def get_connection_info(self) -> dict:
        """Get connection info for UI."""
        return self._output_sink.get_stream_info()
