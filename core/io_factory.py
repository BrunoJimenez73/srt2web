"""
Factory para crear inputs y outputs dinámicamente.

Permite registrar y crear fuentes de entrada y destinos de salida
de forma flexible, facilitando la extensión del sistema.
"""

from typing import Dict, Type, Optional, List
import logging
import importlib
import pkgutil

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

    _inputs: Dict[str, Type[InputSource]] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, name: str, input_class: Type[InputSource]) -> None:
        """Registrar una nueva fuente de entrada."""
        if not issubclass(input_class, InputSource):
            raise TypeError(f"{input_class} must inherit from InputSource")
        cls._inputs[name] = input_class
        logger.info(f"Registered input source: {name}")

    @classmethod
    def create(cls, input_type: str, config: dict) -> InputSource:
        """
        Crear una fuente de entrada por tipo.

        Args:
            input_type: Tipo de input a crear ("srt", "file", etc.)
            config: Configuración para el input

        Returns:
            Instancia del InputSource

        Raises:
            ValueError: Si el tipo no está registrado
        """
        cls._ensure_initialized()

        if input_type not in cls._inputs:
            available = ", ".join(cls._inputs.keys()) if cls._inputs else "none"
            raise ValueError(
                f"Unknown input type: '{input_type}'. Available: {available}"
            )

        return cls._inputs[input_type](config)

    @classmethod
    def available(cls) -> List[str]:
        """Listar tipos de input disponibles."""
        cls._ensure_initialized()
        return list(cls._inputs.keys())

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Inicializar auto-registro si no se ha hecho."""
        if not cls._initialized:
            cls._auto_register()
            cls._initialized = True

    @classmethod
    def _auto_register(cls) -> None:
        """Auto-registrar todos los inputs del paquete modules/inputs."""
        try:
            import modules.inputs

            for importer, modname, ispkg in pkgutil.iter_modules(
                modules.inputs.__path__
            ):
                if modname.endswith("_input") and not modname.startswith("base"):
                    try:
                        module = importlib.import_module(f"modules.inputs.{modname}")
                        # El módulo debe auto-registrarse en su __init__.py
                        logger.debug(f"Loaded input module: {modname}")
                    except Exception as e:
                        logger.warning(f"Failed to load input module {modname}: {e}")
        except ImportError as e:
            logger.debug(f"No inputs package found: {e}")


class OutputFactory:
    """
    Factory para crear destinos de salida.

    Usage:
        OutputFactory.register("hls", HLSOutput)
        output_sink = OutputFactory.create("hls", config)
    """

    _outputs: Dict[str, Type[OutputSink]] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, name: str, output_class: Type[OutputSink]) -> None:
        """Registrar un nuevo destino de salida."""
        if not issubclass(output_class, OutputSink):
            raise TypeError(f"{output_class} must inherit from OutputSink")
        cls._outputs[name] = output_class
        logger.info(f"Registered output sink: {name}")

    @classmethod
    def create(cls, output_type: str, config: dict) -> OutputSink:
        """
        Crear un destino de salida por tipo.

        Args:
            output_type: Tipo de output a crear ("web", "srt", etc.)
            config: Configuración para el output

        Returns:
            Instancia del OutputSink

        Raises:
            ValueError: Si el tipo no está registrado
        """
        cls._ensure_initialized()

        if output_type not in cls._outputs:
            available = ", ".join(cls._outputs.keys()) if cls._outputs else "none"
            raise ValueError(
                f"Unknown output type: '{output_type}'. Available: {available}"
            )

        return cls._outputs[output_type](config)

    @classmethod
    def available(cls) -> List[str]:
        """Listar tipos de output disponibles."""
        cls._ensure_initialized()
        return list(cls._outputs.keys())

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Inicializar auto-registro si no se ha hecho."""
        if not cls._initialized:
            cls._auto_register()
            cls._initialized = True

    @classmethod
    def _auto_register(cls) -> None:
        """Auto-registrar todos los outputs del paquete modules/outputs."""
        try:
            import modules.outputs

            for importer, modname, ispkg in pkgutil.iter_modules(
                modules.outputs.__path__
            ):
                if modname.endswith("_output") and not modname.startswith("base"):
                    try:
                        module = importlib.import_module(f"modules.outputs.{modname}")
                        # El módulo debe auto-registrarse en su __init__.py
                        logger.debug(f"Loaded output module: {modname}")
                    except Exception as e:
                        logger.warning(f"Failed to load output module {modname}: {e}")
        except ImportError as e:
            logger.debug(f"No outputs package found: {e}")


def auto_discover() -> None:
    """Fuerza el descubrimiento de todos los inputs y outputs disponibles."""
    InputFactory._ensure_initialized()
    OutputFactory._ensure_initialized()
    logger.info(f"Available inputs: {InputFactory.available()}")
    logger.info(f"Available outputs: {OutputFactory.available()}")
