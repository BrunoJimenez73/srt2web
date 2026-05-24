"""
Factory para crear inputs y outputs dinámicamente.

Permite registrar y crear fuentes de entrada y destinos de salida
de forma flexible, facilitando la extensión del sistema.
"""

import importlib
import logging
import pkgutil
from typing import Any

from core.input_source import InputSource
from core.output_sink import OutputSink

logger = logging.getLogger("srt2web.factory")


class InputFactory:
    """
    Factory para crear fuentes de entrada.

    Usage:
        InputFactory.register("srt", SRTInput)
        input_source = InputFactory.create("srt", config)
    """

    _inputs: dict[str, type[InputSource]] = {}  # noqa: RUF012
    _initialized: bool = False

    @classmethod
    def register(cls, name: str, input_class: type[InputSource]) -> None:
        """Registrar una nueva fuente de entrada."""
        if not issubclass(input_class, InputSource):
            raise TypeError(f"{input_class} must inherit from InputSource")
        if name not in cls._inputs:
            cls._inputs[name] = input_class
            logger.info(f"Registered input source: {name}")

    @classmethod
    def create(cls, input_type: str, config: dict[str, Any]) -> InputSource:
        cls._ensure_initialized()
        if input_type not in cls._inputs:
            available = ", ".join(cls._inputs.keys()) if cls._inputs else "none"
            raise ValueError(f"Unknown input type: '{input_type}'. Available: {available}")
        return cls._inputs[input_type](config)  # type: ignore[call-arg,arg-type]

    @classmethod
    def available(cls) -> list[str]:
        cls._ensure_initialized()
        return list(cls._inputs.keys())

    @classmethod
    def _ensure_initialized(cls) -> None:
        if not cls._initialized:
            cls._auto_register()
            cls._initialized = True

    @classmethod
    def _auto_register(cls) -> None:
        loaded = set()
        try:
            import modules.inputs

            for _, modname, _ in pkgutil.iter_modules(modules.inputs.__path__):
                if modname.endswith("_input") and not modname.startswith("base") and modname not in loaded:
                    loaded.add(modname)
                    try:
                        importlib.import_module(f"modules.inputs.{modname}")
                        logger.debug(f"Loaded input module: {modname}")
                    except Exception as e:
                        logger.warning(f"Failed to load input module {modname}: {e}")
        except ImportError as e:
            logger.debug(f"No inputs package found: {e}")


class OutputFactory:
    """
    Factory para crear destinos de salida.

    Mantiene un registro único de tipos. La clase CompositeOutput
    se registra automáticamente pero se usa solo internamente — no
    aparece en la lista de tipos disponibles para el usuario.

    Usage:
        OutputFactory.register("rtmp", RTMPOutput)
        output = OutputFactory.create("rtmp", config)
        outputs = OutputFactory.create_multiple([{"type": "rtmp", ...}, ...])
    """

    _outputs: dict[str, type[OutputSink]] = {}  # noqa: RUF012
    _initialized: bool = False
    # Tipos internos que no se muestran al usuario en /api/outputs/available
    _internal_types = frozenset({"hls", "composite"})

    @classmethod
    def register(cls, name: str, output_class: type[OutputSink]) -> None:
        """Registrar un nuevo destino de salida."""
        if not issubclass(output_class, OutputSink):
            raise TypeError(f"{output_class} must inherit from OutputSink")
        if name not in cls._outputs:
            cls._outputs[name] = output_class
            logger.info(f"Registered output sink: {name}")

    @classmethod
    def create(cls, output_type: str, config: dict[str, Any]) -> OutputSink:
        """Crear un destino de salida por tipo."""
        cls._ensure_initialized()
        if output_type not in cls._outputs:
            available = ", ".join(t for t in cls._outputs if t not in cls._internal_types) or "none"
            raise ValueError(f"Unknown output type: '{output_type}'. Available: {available}")
        return cls._outputs[output_type](config)  # type: ignore[call-arg,arg-type]

    @classmethod
    def create_multiple(cls, output_configs: list[dict[str, Any]]) -> list[OutputSink]:
        """Crear múltiples destinos de salida a partir de una lista de configs."""
        cls._ensure_initialized()
        outputs: list[OutputSink] = []
        for i, cfg in enumerate(output_configs):
            output_type = cfg.get("type")
            if not output_type:
                logger.warning(f"Output config #{i} has no 'type', skipping")
                continue
            output_name = cfg.get("name") or f"{output_type}_{i + 1}"
            # Garantizar nombre único
            existing_names = {o.name for o in outputs}
            base = output_name
            counter = 2
            while output_name in existing_names:
                output_name = f"{base}_{counter}"
                counter += 1
            output = cls.create(output_type, cfg)
            output.name = output_name
            outputs.append(output)
        return outputs

    @classmethod
    def available(cls) -> list[str]:
        """Listar tipos de output disponibles para el usuario (sin internos)."""
        cls._ensure_initialized()
        return [t for t in cls._outputs if t not in cls._internal_types]

    @classmethod
    def _ensure_initialized(cls) -> None:
        if not cls._initialized:
            cls._auto_register()
            cls._initialized = True

    @classmethod
    def _auto_register(cls) -> None:
        loaded = set()
        try:
            import modules.outputs

            for _, modname, _ in pkgutil.iter_modules(modules.outputs.__path__):
                if modname.endswith("_output") and not modname.startswith("base") and modname not in loaded:
                    loaded.add(modname)
                    try:
                        importlib.import_module(f"modules.outputs.{modname}")
                        logger.debug(f"Loaded output module: {modname}")
                    except Exception as e:
                        logger.warning(f"Failed to load output module {modname}: {e}")
        except ImportError as e:
            logger.debug(f"No outputs package found: {e}")


def auto_discover() -> None:
    """Fuerza el descubrimiento de todos los inputs y outputs disponibles."""
    InputFactory._ensure_initialized()
    OutputFactory._ensure_initialized()
    logger.info(f"Available inputs:  {InputFactory.available()}")
    logger.info(f"Available outputs: {OutputFactory.available()}")
