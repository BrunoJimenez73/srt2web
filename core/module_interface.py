"""
Interfaz base para módulos del pipeline.

Este módulo define la interfaz que todos los módulos del pipeline deben implementar,
facilitando la consistencia, testabilidad y mantenibilidad.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from core.types import ModuleState, ModuleStatus, PipelineData


@runtime_checkable
class ProcessingModule(Protocol):
    """
    Protocolo para módulos de procesamiento del pipeline.
    
    Este protocolo define la interfaz que deben implementar todos los módulos
    del pipeline para garantizar consistencia y facilitar el testing.
    """
    
    name: str
    """Nombre único del módulo."""
    
    enabled: bool
    """Si el módulo está habilitado para procesamiento."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Inicializar el módulo y sus recursos.
        
        Este método se llama una vez al iniciar el pipeline.
        Debe preparar todos los recursos necesarios (modelos, conexiones, etc).
        
        Raises:
            ModuleInitializationError: Si falla la inicialización.
        """
        pass
    
    @abstractmethod
    async def process(self, data: PipelineData) -> PipelineData:
        """
        Procesar datos a través del módulo.
        
        Args:
            data: Datos de entrada del pipeline.
            
        Returns:
            Datos procesados (pueden ser los mismos o modificados).
            
        Raises:
            ModuleProcessingError: Si falla el procesamiento.
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Cerrar y liberar recursos del módulo.
        
        Este método se llama una vez al detener el pipeline.
        Debe liberar todos los recursos (memoria, conexiones, etc).
        
        Raises:
            ModuleShutdownError: Si falla el cierre.
        """
        pass
    
    @abstractmethod
    def get_status(self) -> ModuleStatus:
        """
        Obtener el estado actual del módulo.
        
        Returns:
            Objeto ModuleStatus con información del estado.
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """
        Resetear el estado del módulo a su estado inicial.
        
        Útil para recuperación de errores o reinicio del pipeline.
        """
        pass


class BaseModule(ABC):
    """
    Clase base abstracta para módulos del pipeline.
    
    Implementa la lógica común de gestión de estado y métricas,
    dejando los métodos específicos de procesamiento como abstractos.
    """
    
    def __init__(self, name: str, enabled: bool = True):
        """
        Inicializar el módulo base.
        
        Args:
            name: Nombre único del módulo.
            enabled: Si el módulo está habilitado por defecto.
        """
        self._name = name
        self._enabled = enabled
        self._state = ModuleState.IDLE if enabled else ModuleState.DISABLED
        self._status = ModuleStatus(name=name, enabled=enabled)
        if not enabled:
            self._status.state = ModuleState.DISABLED
        self._last_error: Optional[str] = None
    
    @property
    def name(self) -> str:
        """Obtener nombre del módulo."""
        return self._name
    
    @property
    def enabled(self) -> bool:
        """Obtener estado de habilitación."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        """Establecer estado de habilitación."""
        self._enabled = value
        self._status.enabled = value
        if not value:
            self._state = ModuleState.DISABLED
            self._status.state = ModuleState.DISABLED
    
    @property
    def state(self) -> ModuleState:
        """Obtener estado actual."""
        return self._state
    
    def _set_state(self, state: ModuleState) -> None:
        """
        Establecer estado interno del módulo.
        
        Args:
            state: Nuevo estado.
        """
        self._state = state
        self._status.state = state
    
    def get_status(self) -> ModuleStatus:
        """
        Obtener el estado actual del módulo.
        
        Returns:
            Objeto ModuleStatus con información completa.
        """
        return self._status
    
    def reset(self) -> None:
        """
        Resetear el estado del módulo a IDLE.
        """
        self._state = ModuleState.IDLE
        self._status.state = ModuleState.IDLE
        self._last_error = None
        self._status.last_error = None
        self._status.error_count = 0
    
    def _start_processing(self) -> None:
        """Marcar inicio de procesamiento."""
        self._set_state(ModuleState.PROCESSING)
    
    def _end_processing(self, processing_time: float) -> None:
        """
        Marcar fin de procesamiento y actualizar métricas.
        
        Args:
            processing_time: Tiempo de procesamiento en segundos.
        """
        self._status.update_processing_time(processing_time)
        self._set_state(ModuleState.READY)
    
    def _set_error(self, error: str) -> None:
        """
        Establecer estado de error.
        
        Args:
            error: Descripción del error.
        """
        self._last_error = error
        self._set_state(ModuleState.ERROR)
        self._status.last_error = error
        self._status.error_count += 1
    
    # Métodos abstractos que deben implementar las módulos derivados
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Inicializar el módulo y sus recursos.
        
        Raises:
            ModuleInitializationError: Si falla la inicialización.
        """
        pass
    
    @abstractmethod
    async def process(self, data: PipelineData) -> PipelineData:
        """
        Procesar datos a través del módulo.
        
        Args:
            data: Datos de entrada del pipeline.
            
        Returns:
            Datos procesados.
            
        Raises:
            ModuleProcessingError: Si falla el procesamiento.
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Cerrar y liberar recursos del módulo.
        
        Raises:
            ModuleShutdownError: Si falla el cierre.
        """
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', state={self.state.value}, enabled={self.enabled})>"