"""
Pipeline State Manager - Gestion centralizada del estado del pipeline.

Responsabilidades:
- Mantener estado actual del pipeline (IDLE, STARTING, RUNNING, STOPPING, ERROR)
- Transiciones de estado validas
- Notificar callbacks de cambio de estado
- Historial de transiciones
- Estado de modulos individuales
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("srt2web.pipeline.state_manager")


class PipelineState(str, Enum):
    """Estados posibles del pipeline."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class ModuleState(str, Enum):
    """Estados posibles de un modulo."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    DISABLED = "disabled"
    DEGRADED = "degraded"


@dataclass
class StateTransition:
    """Registro de una transicion de estado."""

    timestamp: float
    from_state: str
    to_state: str
    reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "reason": self.reason,
        }


@dataclass
class ModuleStateInfo:
    """Estado de un modulo individual."""

    name: str
    state: ModuleState
    enabled: bool = True
    processed_chunks: int = 0
    last_error: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "enabled": self.enabled,
            "processed_chunks": self.processed_chunks,
            "last_error": self.last_error,
            "extra": self.extra,
        }


# Transiciones validas de estado
VALID_TRANSITIONS: dict[PipelineState, list[PipelineState]] = {
    PipelineState.IDLE: [PipelineState.STARTING],
    PipelineState.STARTING: [PipelineState.RUNNING, PipelineState.ERROR, PipelineState.IDLE],
    PipelineState.RUNNING: [PipelineState.STOPPING, PipelineState.ERROR],
    PipelineState.STOPPING: [PipelineState.IDLE, PipelineState.ERROR],
    PipelineState.ERROR: [PipelineState.IDLE, PipelineState.STOPPING],
}


class PipelineStateManager:
    """
    Gestiona el estado del pipeline y sus modulos.

    Valida transiciones, notifica callbacks y mantiene historial.
    """

    def __init__(self, initial_state: PipelineState = PipelineState.IDLE):
        self._state = initial_state
        self._modules: dict[str, ModuleStateInfo] = {}
        self._history: list[StateTransition] = []
        self._on_state_change: Optional[Callable[[str, str, Optional[str]], None]] = None
        self._started_at: Optional[float] = None
        self._stopped_at: Optional[float] = None

    @property
    def state(self) -> PipelineState:
        """Estado actual del pipeline."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Verificar si el pipeline esta en ejecucion."""
        return self._state in (PipelineState.RUNNING, PipelineState.STARTING)

    @property
    def is_idle(self) -> bool:
        """Verificar si el pipeline esta inactivo."""
        return self._state == PipelineState.IDLE

    @property
    def uptime(self) -> float:
        """Tiempo en ejecucion en segundos."""
        if not self._started_at:
            return 0.0
        end = self._stopped_at or time.time()
        return end - self._started_at

    def set_callback(self, callback: Callable[[str, str, Optional[str]], None]) -> None:
        """Configurar callback para cambios de estado."""
        self._on_state_change = callback

    def can_transition_to(self, target: PipelineState) -> bool:
        """Verificar si una transicion es valida."""
        allowed = VALID_TRANSITIONS.get(self._state, [])
        return target in allowed

    def transition_to(self, target: PipelineState, reason: Optional[str] = None) -> bool:
        """
        Intentar transicionar a un nuevo estado.

        Returns:
            True si la transicion fue exitosa, False si no es valida.
        """
        if not self.can_transition_to(target):
            logger.warning(f"Invalid state transition: {self._state.value} -> {target.value}")
            return False

        old_state = self._state.value
        self._state = target

        # Registrar transicion
        transition = StateTransition(
            timestamp=time.time(),
            from_state=old_state,
            to_state=target.value,
            reason=reason,
        )
        self._history.append(transition)

        # Limitar historial
        if len(self._history) > 500:
            self._history = self._history[-250:]

        # Trackear tiempos
        if target == PipelineState.RUNNING:
            self._started_at = time.time()
        elif target in (PipelineState.IDLE, PipelineState.ERROR):
            if self._state == PipelineState.IDLE and self._started_at:
                self._stopped_at = time.time()

        logger.info(f"Pipeline state: {old_state} -> {target.value}" + (f" ({reason})" if reason else ""))

        # Notificar callback
        if self._on_state_change:
            try:
                self._on_state_change(old_state, target.value, reason)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

        return True

    def register_module(self, name: str, enabled: bool = True) -> None:
        """Registrar un modulo en el state manager."""
        self._modules[name] = ModuleStateInfo(
            name=name,
            state=ModuleState.IDLE,
            enabled=enabled,
        )

    def update_module_state(
        self,
        name: str,
        state: ModuleState,
        processed_chunks: Optional[int] = None,
        error: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> None:
        """Actualizar estado de un modulo."""
        if name not in self._modules:
            self.register_module(name)

        info = self._modules[name]
        info.state = state

        if processed_chunks is not None:
            info.processed_chunks = processed_chunks
        if error is not None:
            info.last_error = error
        if extra is not None:
            info.extra.update(extra)

    def get_module_state(self, name: str) -> Optional[ModuleStateInfo]:
        """Obtener estado de un modulo."""
        return self._modules.get(name)

    def get_all_modules(self) -> dict[str, ModuleStateInfo]:
        """Obtener estado de todos los modulos."""
        return dict(self._modules)

    def get_enabled_modules(self) -> list[str]:
        """Obtener lista de modulos habilitados."""
        return [name for name, info in self._modules.items() if info.enabled and info.state != ModuleState.DISABLED]

    def get_state_history(self, count: int = 20) -> list[dict]:
        """Obtener historial de transiciones."""
        return [t.to_dict() for t in self._history[-count:]]

    def get_status(self) -> dict[str, Any]:
        """Obtener estado completo del pipeline."""
        modules_status = [info.to_dict() for info in self._modules.values()]

        return {
            "state": self._state.value,
            "is_running": self.is_running,
            "uptime_seconds": round(self.uptime, 1),
            "modules": modules_status,
            "module_count": len(self._modules),
            "enabled_modules": len(self.get_enabled_modules()),
            "transitions": len(self._history),
        }

    def reset(self) -> None:
        """Resetear estado a IDLE."""
        self._state = PipelineState.IDLE
        self._started_at = None
        self._stopped_at = None

        for info in self._modules.values():
            info.state = ModuleState.IDLE

    def clear_history(self) -> None:
        """Limpiar historial de transiciones."""
        self._history.clear()
