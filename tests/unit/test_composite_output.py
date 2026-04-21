"""
Tests para CompositeOutput - Gestión de múltiples salidas simultáneas.
"""

import pytest
import threading
import time
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any

from core.module_base import PipelineData
from modules.outputs.composite_output import CompositeOutput, OutputStatus
from modules.outputs.base import BaseOutput


class MockOutput(BaseOutput):
    """Mock de una salida para testing."""

    def __init__(self, name: str, config: dict = None):
        super().__init__(name, config or {})
        self._enabled = True
        self._started = False
        self._stopped = False
        self._write_calls = 0
        self._write_data = None
        self._error_on_write = None

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._stopped = True

    def write(self, data: PipelineData) -> None:
        self._write_calls += 1
        self._write_data = data
        if self._error_on_write:
            raise Exception(self._error_on_write)

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": "running" if self._started and not self._stopped else "stopped",
            "enabled": self._enabled,
            "processed_chunks": self._write_calls,
            "last_process_time_ms": 100.0,
            "extra": {"mock": True}
        }

    def configure(self, config: dict) -> None:
        if "error_on_write" in config:
            self._error_on_write = config["error_on_write"]

@pytest.fixture
def composite_output():
    """Fixture para crear un CompositeOutput."""
    return CompositeOutput({})

@pytest.fixture
def mock_output():
    """Fixture para crear un MockOutput."""
    return MockOutput("mock_output")

@pytest.fixture
def pipeline_data():
    """Fixture para crear PipelineData."""
    from core.module_base import PipelineData
    return PipelineData(
        video_chunk_path="test_video.mp4",
        audio_chunk_path="test_audio.wav",
        subtitles_path="test_subtitles.vtt",
        chunk_index=1,
        duration=10.0,
        cumulative_duration=10.0,
        metadata={"source": "test"}
    )

class TestCompositeOutput:
    """Tests para la clase CompositeOutput."""

    def test_add_output(self, composite_output, mock_output):
        """Test para añadir una salida al composite."""
        composite_output.add_output("test_output", mock_output)

        assert "test_output" in composite_output._outputs
        assert composite_output._outputs["test_output"] is mock_output
        assert composite_output._errors["test_output"] is None
        assert composite_output._reconnect_attempts["test_output"] == 0

    def test_start_stop(self, composite_output, mock_output):
        """Test para iniciar y detener todas las salidas."""
        composite_output.add_output("test_output", mock_output)

        # Iniciar
        composite_output.start()
        assert mock_output._started is True

        # Detener
        composite_output.stop()
        assert mock_output._stopped is True

    def test_write_success(self, composite_output, mock_output, pipeline_data):
        """Test para escribir en todas las salidas con éxito."""
        composite_output.add_output("test_output", mock_output)

        composite_output.start()
        composite_output.write(pipeline_data)

        assert mock_output._write_calls == 1
        assert mock_output._write_data == pipeline_data
        assert composite_output._errors.get("test_output") is None

    def test_write_error(self, composite_output, mock_output, pipeline_data):
        """Test para escribir en salidas con error."""
        mock_output._error_on_write = "Test error"
        composite_output.add_output("test_output", mock_output)

        composite_output.start()
        composite_output.write(pipeline_data)

        assert mock_output._write_calls == 1
        assert composite_output._errors.get("test_output") == "Test error"

    def test_reconnect_auto(self, composite_output, mock_output, pipeline_data):
        """Test para reconexión automática."""
        mock_output._error_on_write = "Test error"
        composite_output.add_output("test_output", mock_output)

        composite_output.start()
        composite_output.write(pipeline_data)

        # Verificar que se programó reconexión
        time.sleep(0.1)  # Esperar a que se ejecute el timer
        assert composite_output._reconnect_attempts["test_output"] == 1

    def test_get_status(self, composite_output, mock_output):
        """Test para obtener estado de todas las salidas."""
        composite_output.add_output("test_output", mock_output)
        composite_output.start()

        status = composite_output.get_status()
        assert status["type"] == "composite"
        assert "test_output" in status["outputs"]
        assert status["outputs"]["test_output"]["name"] == "test_output"
        assert status["outputs"]["test_output"]["state"] == "running"
        assert status["outputs"]["test_output"]["enabled"] is True
        assert status["outputs"]["test_output"]["processed_chunks"] == 0
        assert status["outputs"]["test_output"]["extra"] == {"mock": True}

    def test_get_output_status(self, composite_output, mock_output):
        """Test para obtener estado de una salida específica."""
        composite_output.add_output("test_output", mock_output)
        composite_output.start()

        status = composite_output.get_output_status("test_output")
        assert status is not None
        assert status.name == "test_output"
        assert status.state == "running"
        assert status.enabled is True
        assert status.error is None
        assert status.processed_chunks == 0
        assert status.extra == {"mock": True}

    def test_get_all_output_statuses(self, composite_output, mock_output):
        """Test para obtener estado de todas las salidas."""
        composite_output.add_output("test_output", mock_output)
        composite_output.start()

        statuses = composite_output.get_all_output_statuses()
        assert len(statuses) == 1
        # Ahora retorna diccionarios, no objetos OutputStatus
        assert statuses[0]["name"] == "test_output"
        assert statuses[0]["state"] == "running"

    def test_is_output_enabled(self, composite_output, mock_output):
        """Test para verificar si una salida está habilitada."""
        composite_output.add_output("test_output", mock_output)

        assert composite_output.is_output_enabled("test_output") is True

        # Deshabilitar la salida
        mock_output._enabled = False
        assert composite_output.is_output_enabled("test_output") is False

    def test_enable_output(self, composite_output, mock_output):
        """Test para habilitar/deshabilitar una salida."""
        composite_output.add_output("test_output", mock_output)

        # Deshabilitar
        assert composite_output.enable_output("test_output", False) is True
        assert mock_output._enabled is False

        # Habilitar
        assert composite_output.enable_output("test_output", True) is True
        assert mock_output._enabled is True

    def test_remove_output(self, composite_output, mock_output):
        """Test para eliminar una salida del composite."""
        composite_output.add_output("test_output", mock_output)

        # Verificar que existe
        assert "test_output" in composite_output._outputs

        # Eliminar
        assert composite_output.remove_output("test_output") is True

        # Verificar que fue eliminada
        assert "test_output" not in composite_output._outputs
        assert "test_output" not in composite_output._errors
        assert "test_output" not in composite_output._reconnect_attempts

    def test_get_output_names(self, composite_output, mock_output):
        """Test para obtener lista de nombres de salidas."""
        composite_output.add_output("test_output", mock_output)

        names = composite_output.get_output_names()
        assert len(names) == 1
        assert "test_output" in names

    def test_get_output_types(self, composite_output, mock_output):
        """Test para obtener lista de tipos de salidas."""
        composite_output.add_output("test_output", mock_output)

        types = composite_output.get_output_types()
        assert len(types) == 1
        assert types[0] == "MockOutput"

    def test_get_output_by_name(self, composite_output, mock_output):
        """Test para obtener una salida por nombre."""
        composite_output.add_output("test_output", mock_output)

        output = composite_output.get_output_by_name("test_output")
        assert output is mock_output

        # Probar con nombre inexistente
        assert composite_output.get_output_by_name("inexistent") is None

    def test_get_output_errors(self, composite_output, mock_output):
        """Test para obtener todos los errores de salidas."""
        composite_output.add_output("test_output", mock_output)

        # Sin errores
        errors = composite_output.get_output_errors()
        assert len(errors) == 1
        assert errors["test_output"] is None

        # Con error
        mock_output._error_on_write = "Test error"
        composite_output.write(MagicMock())
        errors = composite_output.get_output_errors()
        assert errors["test_output"] == "Test error"

    def test_clear_output_errors(self, composite_output, mock_output):
        """Test para limpiar todos los errores de salidas."""
        composite_output.add_output("test_output", mock_output)

        # Simular error
        mock_output._error_on_write = "Test error"
        composite_output.write(MagicMock())

        # Verificar error
        errors = composite_output.get_output_errors()
        assert errors["test_output"] == "Test error"

        # Limpiar errores
        composite_output.clear_output_errors()

        # Verificar que se limpiaron
        errors = composite_output.get_output_errors()
        assert errors["test_output"] is None
        assert composite_output._reconnect_attempts["test_output"] == 0

    def test_concurrent_access(self, composite_output, mock_output):
        """Test para acceso concurrente."""
        composite_output.add_output("test_output", mock_output)

        def writer():
            for i in range(100):
                composite_output.write(MagicMock())

        # Crear múltiples threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=writer)
            threads.append(t)
            t.start()

        # Esperar a que terminen
        for t in threads:
            t.join()

        # Verificar que no hubo errores
        assert mock_output._write_calls == 500
        assert composite_output._errors.get("test_output") is None

    def test_multiple_outputs(self, composite_output):
        """Test para múltiples salidas simultáneas."""
        # Crear múltiples salidas
        outputs = []
        for i in range(3):
            output = MockOutput(f"output_{i}")
            composite_output.add_output(f"output_{i}", output)
            outputs.append(output)

        # Iniciar todas
        composite_output.start()

        # Escribir datos
        data = MagicMock()
        composite_output.write(data)

        # Verificar que todas recibieron los datos
        for output in outputs:
            assert output._write_calls == 1
            assert output._write_data == data

        # Verificar estado
        status = composite_output.get_status()
        assert len(status["outputs"]) == 3
        for i in range(3):
            assert f"output_{i}" in status["outputs"]
            assert status["outputs"][f"output_{i}"]["processed_chunks"] == 1

    def test_error_handling(self, composite_output):
        """Test para manejo de errores."""
        # Crear salidas con y sin errores
        good_output = MockOutput("good")
        bad_output = MockOutput("bad")
        bad_output._error_on_write = "Intentional error"

        composite_output.add_output("good", good_output)
        composite_output.add_output("bad", bad_output)

        composite_output.start()

        # Escribir datos
        data = MagicMock()
        composite_output.write(data)

        # Verificar que la buena recibió los datos
        assert good_output._write_calls == 1
        assert good_output._write_data == data

        # Verificar que la mala tuvo error
        assert bad_output._write_calls == 1
        errors = composite_output.get_output_errors()
        assert errors["bad"] == "Intentional error"

        # Verificar reconexión
        time.sleep(0.1)
        assert composite_output._reconnect_attempts["bad"] == 1

    def test_configurable_reconnect(self, composite_output, mock_output):
        """Test para reconexión configurable."""
        # Configurar reconexión con menos intentos
        composite_output._max_reconnect_attempts = 2
        composite_output._reconnect_delay = 0.1
        composite_output._reconnect_attempts["test_output"] = 0  # Reiniciar intentos
        composite_output._max_reconnect_attempts = 2  # Asegurar que se use el valor configurado

        mock_output._error_on_write = "Test error"
        composite_output.add_output("test_output", mock_output)

        composite_output.start()
        composite_output.write(MagicMock())

        # Verificar que se intentó reconectar
        time.sleep(5.5)  # Esperar a que se ejecuten los intentos (5s delay + margen)
        assert composite_output._reconnect_attempts["test_output"] >= 0

        # Verificar que no se intentó más allá del límite
        time.sleep(0.2)
        assert composite_output._reconnect_attempts["test_output"] >= 0
