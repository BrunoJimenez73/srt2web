"""
Tests para verificar la refactorización del frontend
"""
import pytest
from pathlib import Path
import re


class TestFrontendStructure:
    @pytest.fixture
    def frontend_root(self) -> None:
        return Path(__file__).parent.parent.parent / "frontend"

    def test_store_directory_exists(self, frontend_root) -> None:
        store_dir = frontend_root / "src" / "lib" / "store"
        assert store_dir.exists(), "store/ directory missing"

    def test_store_index_has_exports(self, frontend_root) -> None:
        index_file = frontend_root / "src" / "lib" / "store" / "index.ts"
        assert index_file.exists()
        content = index_file.read_text(encoding='utf-8')
        assert "pipelineStatus" in content
        assert "startEffects" in content
        assert "stopEffects" in content


class TestDashboardRefactor:
    @pytest.fixture
    def dashboard_file(self) -> None:
        return Path(__file__).parent.parent.parent / "frontend" / "src" / "lib" / "dashboard.ts"

    def test_dashboard_uses_signals(self, dashboard_file) -> None:
        content = dashboard_file.read_text(encoding='utf-8')
        assert "from './modules/pipeline-control'" in content
        assert "from './modules/config-collector'" in content

    def test_handle_functions_exist(self, dashboard_file) -> None:
        content = dashboard_file.read_text(encoding='utf-8')
        assert "handleStart" in content
        assert "handleStop" in content
        assert "handleSaveConfig" in content


class TestEffectsImplementation:
    @pytest.fixture
    def effects_file(self) -> None:
        return Path(__file__).parent.parent.parent / "frontend" / "src" / "lib" / "store" / "effects.ts"

    def test_effects_file_exists(self, effects_file) -> None:
        assert effects_file.exists()

    def test_effects_use_signals(self, effects_file) -> None:
        content = effects_file.read_text(encoding='utf-8')
        # Buscar patrones como pipelineStatus.value
        matches = re.findall(r'\w+\.value', content)
        assert len(matches) > 0, "Effects should use signal .value"

    def test_start_effects_exists(self, effects_file) -> None:
        content = effects_file.read_text(encoding='utf-8')
        assert "function startEffects" in content or "export function startEffects" in content


class TestBuildOutput:
    @pytest.fixture
    def server_static(self) -> None:
        return Path(__file__).parent.parent.parent / "server" / "static"

    def test_build_exists(self, server_static) -> None:
        assert server_static.exists()

    def test_index_html_exists(self, server_static) -> None:
        assert (server_static / "index.html").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
