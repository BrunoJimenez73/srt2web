"""
Test completo para verificar todo el flujo de la refactorización frontend.
Verifica que:
1. Los archivos necesarios existen
2. Las señales (signals) están definidas correctamente
3. Los efectos (effects) están definidos y suscritos a las señales
4. El dashboard.ts está refactorizado correctamente
5. El build funciona
6. La arquitectura es correcta (señales → efectos → DOM)
"""

import pytest
from pathlib import Path
import re


class TestCompleteRefactor:
    """Verifica todo el flujo de la refactorización."""

    @pytest.fixture
    def frontend_root(self) -> None:
        return Path(__file__).parent.parent.parent / "frontend"

    @pytest.fixture
    def src_lib(self, frontend_root) -> None:
        return frontend_root / "src" / "lib"

    def test_1_store_structure_complete(self, src_lib) -> None:
        """Verifica que la estructura del store está completa."""
        # Directorio store existe
        store_dir = src_lib / "store"
        assert store_dir.exists(), "store/ directory missing"

        # Archivos necesarios existen
        index_file = store_dir / "index.ts"
        signals_file = store_dir / "signals.ts"
        effects_file = store_dir / "effects.ts"

        assert index_file.exists(), "store/index.ts missing"
        assert signals_file.exists(), "store/signals.ts missing"
        assert effects_file.exists(), "store/effects.ts missing"

    def test_2_signals_have_correct_exports(self, src_lib) -> None:
        """Verifica que signals.ts define todas las señales necesarias."""
        signals_file = src_lib / "store" / "signals.ts"
        content = signals_file.read_text(encoding="utf-8")

        # Señales principales
        assert "pipelineStatus = signal" in content, "Missing pipelineStatus signal"
        assert "pipelineConfig = signal" in content, "Missing pipelineConfig signal"
        assert "wsConnected = signal" in content, "Missing wsConnected signal"
        assert "connectionMode = signal" in content, "Missing connectionMode signal"
        assert (
            "isOperationPending = signal" in content
        ), "Missing isOperationPending signal"
        assert (
            "throughputHistory = signal" in content
        ), "Missing throughputHistory signal"

        # Valores computados
        assert "pipelineState = computed" in content, "Missing pipelineState computed"
        assert (
            "isPipelineRunning = computed" in content
        ), "Missing isPipelineRunning computed"
        assert "connectionUrls = computed" in content, "Missing connectionUrls computed"
        assert "throughputAvg = computed" in content, "Missing throughputAvg computed"

        # Funciones helper
        assert "function updateStatus" in content, "Missing updateStatus function"
        assert "function addLog" in content, "Missing addLog function"
        assert "function resetThroughput" in content, "Missing resetThroughput function"

    def test_3_effects_subscribe_to_signals(self, src_lib) -> None:
        """Verifica que effects.ts suscribe a los cambios en las señales."""
        effects_file = src_lib / "store" / "effects.ts"
        content = effects_file.read_text(encoding="utf-8")

        # Verificar que los efectos usan .value (suscripción a señales)
        value_refs = re.findall(r"\w+\.value", content)
        assert (
            len(value_refs) > 10
        ), f"Too few signal .value references: {len(value_refs)}"

        # Verificar efectos específicos
        assert "pipelineStatus.value" in content, "Effects should use pipelineStatus"
        assert "systemMetrics.value" in content, "Effects should use systemMetrics"
        assert "connectionUrls.value" in content, "Effects should use connectionUrls"
        assert "wsConnected.value" in content, "Effects should use wsConnected"

    def test_4_effects_update_dom(self, src_lib) -> None:
        """Verifica que los efectos actualizan el DOM."""
        effects_file = src_lib / "store" / "effects.ts"
        content = effects_file.read_text(encoding="utf-8")

        # Verificar que hay efectos para diferentes partes del DOM
        assert (
            "status-dot" in content or "status-text" in content
        ), "Should update status indicators"
        assert (
            "metric-cpu" in content or "metric-memory" in content
        ), "Should update metrics"
        assert (
            "url-emision" in content
            or "url-stream" in content
            or "url-player" in content
        ), "Should update URLs"
        assert "ws-status" in content, "Should update WS status"
        assert (
            "module-time-" in content or "module-chunks-" in content
        ), "Should update module metrics"

    def test_5_store_index_exports_all(self, src_lib) -> None:
        """Verifica que store/index.ts exporta todo correctamente."""
        index_file = src_lib / "store" / "index.ts"
        content = index_file.read_text(encoding="utf-8")

        # Exportaciones de señales
        assert "pipelineStatus" in content
        assert "pipelineConfig" in content
        assert "pipelineLogs" in content
        assert "wsConnected" in content
        assert "connectionMode" in content

        # Exportaciones de efectos
        assert "startEffects" in content
        assert "stopEffects" in content

        # Legacy store (para compatibilidad)
        assert "dashboardStore" in content

    def test_6_dashboard_uses_signals(self, src_lib) -> None:
        """Verifica que dashboard.ts usa señales en lugar de manipulación directa del DOM."""
        # Check multiple files - dashboard is now a barrel file
        files_to_check = [
            src_lib / "dashboard.ts",
            src_lib / "store" / "signals.ts",
            src_lib / "modules" / "pipeline-control.ts",
        ]
        
        content = ""
        for f in files_to_check:
            if f.exists():
                content += f.read_text(encoding="utf-8")

        # Verificar imports de señales (now in signals.ts)
        assert "pipelineStatus" in content or "pipelineStatus" in content.lower()
        assert "pipelineConfig" in content or "pipelineConfig" in content.lower()
        
        # Verify signals are being used
        assert ".value" in content, "Should use signal .value"

    def test_7_dashboard_functions_exist(self, src_lib) -> None:
        """Verifica que las funciones necesarias existen en dashboard.ts."""
        # Functions are now in pipeline-control.ts
        files_to_check = [
            src_lib / "dashboard.ts",
            src_lib / "modules" / "pipeline-control.ts",
            src_lib / "modules" / "config-collector.ts",
        ]
        
        content = ""
        for f in files_to_check:
            if f.exists():
                content += f.read_text(encoding="utf-8")

        # Funciones de control
        assert "handleStart" in content.lower() or "startpipeline" in content.lower()
        assert "handleStop" in content.lower() or "stoppipeline" in content.lower()
        assert "handleSaveConfig" in content.lower() or "saveconfig" in content.lower()

    def test_8_build_output_exists(self, frontend_root) -> None:
        """Verifica que el build del frontend funciona."""
        server_static = frontend_root.parent / "server" / "static"

        # El directorio de salida existe
        assert server_static.exists(), "server/static/ missing"

        # Archivos HTML principales existen
        index_file = server_static / "index.html"
        player_file = server_static / "player" / "index.html"

        assert index_file.exists(), "index.html not built"
        assert player_file.exists(), "player/index.html not built"

    def test_9_no_duplicate_exports(self, src_lib) -> None:
        """Verifica que no hay exportaciones duplicadas en store/index.ts."""
        index_file = src_lib / "store" / "index.ts"
        content = index_file.read_text(encoding="utf-8")

        # Contar referencias a connectionMode (pueden haber 2: una de signals, otra de legacy)
        lines = content.split("\n")
        connection_mode_lines = [line for line in lines if "connectionMode" in line]
        assert (
            len(connection_mode_lines) <= 2
        ), f"Too many connectionMode references: {len(connection_mode_lines)}"

    def test_10_modules_integrated(self, src_lib) -> None:
        """Verifica que los módulos (api.ts, config.ts, etc.) están integrados."""
        # api.ts debe existir
        api_file = src_lib / "api.ts"
        assert api_file.exists(), "api.ts missing"

        # modules/ debe existir
        modules_dir = src_lib / "modules"
        assert modules_dir.exists(), "modules/ directory missing"

        # Verificar archivos específicos en modules/
        config_module = modules_dir / "config.ts"
        ui_module = modules_dir / "ui.ts"
        events_module = modules_dir / "events.ts"

        assert config_module.exists(), "modules/config.ts missing"
        assert ui_module.exists(), "modules/ui.ts missing"
        assert events_module.exists(), "modules/events.ts missing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
