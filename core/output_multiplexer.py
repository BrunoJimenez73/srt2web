"""
Output Multiplexer - Permite escribir a múltiples outputs simultáneamente.

Gestiona una lista de OutputModuleWrapper instances y escribe
a todos los outputs habilitados.
"""

import logging
from typing import List, Optional, Dict, Any

from core.module_base import PipelineData, ModuleState

logger = logging.getLogger("srt2web.output_multiplexer")


class OutputMultiplexer:
    """
    Permite escribir a múltiples outputs simultáneamente.
    
    Ejemplo de uso:
        multiplexer = OutputMultiplexer()
        multiplexer.add_output(hls_output_module)
        multiplexer.add_output(rtmp_output_module)
        multiplexer.write(processed_data)
    """
    
    def __init__(self):
        self._outputs: List[Any] = []  # List of OutputModuleWrapper
        self._chunks_written = 0
        self._enabled = True
    
    @property
    def enabled(self) -> bool:
        """Check if multiplexer is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Enable/disable multiplexer."""
        self._enabled = value
    
    def add_output(self, output_module: Any) -> None:
        """
        Add an output module to the multiplexer.
        
        Args:
            output_module: OutputModuleWrapper instance
        """
        if output_module not in self._outputs:
            self._outputs.append(output_module)
            logger.info(f"Added output to multiplexer: {output_module.name}")
    
    def remove_output(self, output_module: Any) -> None:
        """
        Remove an output module from the multiplexer.
        
        Args:
            output_module: OutputModuleWrapper instance to remove
        """
        if output_module in self._outputs:
            self._outputs.remove(output_module)
            logger.info(f"Removed output from multiplexer: {output_module.name}")
    
    def get_outputs(self) -> List[Any]:
        """
        Get all output modules in the multiplexer.
        
        Returns:
            List of OutputModuleWrapper instances
        """
        return self._outputs.copy()
    
    def write(self, data: PipelineData) -> None:
        """
        Write data to all enabled output modules.
        
        Args:
            data: PipelineData to write
        """
        if not self._enabled or not data:
            return
        
        successful_writes = 0
        failed_writes = 0
        
        for output_module in self._outputs:
            if not output_module.enabled:
                continue
            
            if output_module.state != ModuleState.RUNNING:
                continue
            
            try:
                # Call the output module's process method
                output_module.process(data)
                successful_writes += 1
            except Exception as e:
                logger.error(f"Error writing to output {output_module.name}: {e}")
                failed_writes += 1
        
        if successful_writes > 0:
            self._chunks_written += 1
        
        if failed_writes > 0:
            logger.warning(f"Multiplexer: {successful_writes} successful, {failed_writes} failed writes")
    
    def start_all(self) -> None:
        """Start all enabled output modules."""
        for output_module in self._outputs:
            if output_module.enabled:
                try:
                    output_module.start()
                    logger.info(f"Started output: {output_module.name}")
                except Exception as e:
                    logger.error(f"Failed to start output {output_module.name}: {e}")
    
    def stop_all(self) -> None:
        """Stop all output modules."""
        for output_module in self._outputs:
            try:
                output_module.stop()
                logger.info(f"Stopped output: {output_module.name}")
            except Exception as e:
                logger.error(f"Error stopping output {output_module.name}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all outputs in the multiplexer.
        
        Returns:
            Dict with status information
        """
        outputs_status = []
        for output_module in self._outputs:
            try:
                status = output_module.get_status()
                outputs_status.append(status.to_dict())
            except Exception as e:
                logger.error(f"Error getting status from {output_module.name}: {e}")
        
        return {
            "enabled": self._enabled,
            "chunks_written": self._chunks_written,
            "outputs_count": len(self._outputs),
            "outputs": outputs_status
        }
    
    def get_output_by_name(self, name: str) -> Optional[Any]:
        """
        Get an output module by name.
        
        Args:
            name: Name of the output module
            
        Returns:
            OutputModuleWrapper instance or None
        """
        for output_module in self._outputs:
            if output_module.name == name:
                return output_module
        return None
    
    def enable_output(self, name: str, enabled: bool = True) -> bool:
        """
        Enable or disable a specific output.
        
        Args:
            name: Name of the output module
            enabled: True to enable, False to disable
            
        Returns:
            True if output was found and modified
        """
        output_module = self.get_output_by_name(name)
        if output_module:
            output_module.enabled = enabled
            logger.info(f"Output {name} {'enabled' if enabled else 'disabled'}")
            return True
        return False