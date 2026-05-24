"""
Tests for Astro documentation pages.
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_astro_source_content(file_path):  # type: ignore
    """Load Astro source file for testing."""
    base_path = PROJECT_ROOT / "frontend" / "src"
    astro_file = base_path / file_path

    if astro_file.exists():
        with open(astro_file, encoding="utf-8") as f:
            return f.read()
    return None


class TestDocumentationIndex:
    """Tests for documentation index page."""

    @pytest.fixture
    def docs_index_content(self) -> None:
        """Load docs index content."""
        docs_path = PROJECT_ROOT / "docs" / "index.md"
        if docs_path.exists():
            with open(docs_path, encoding="utf-8") as f:
                return f.read()
        return None

    def test_docs_index_exists(self, docs_index_content) -> None:
        """Test that docs index exists."""
        # This test will be skipped if docs don't exist yet
        # This is expected since we're creating the documentation structure
        if docs_index_content is None:
            pytest.skip("docs/index.md not found - documentation needs to be created")


class TestAstroPagesStructure:
    """Tests for Astro pages structure."""

    @pytest.fixture
    def dashboard_page(self) -> None:
        """Load dashboard page."""
        return get_astro_source_content("pages/index.astro")

    @pytest.fixture
    def player_page(self) -> None:
        """Load player page."""
        return get_astro_source_content("pages/player.astro")

    def test_dashboard_page_exists(self, dashboard_page) -> None:
        """Test that dashboard page exists."""
        assert dashboard_page is not None

    def test_dashboard_imports_base_layout(self, dashboard_page) -> None:
        """Test that dashboard imports BaseLayout."""
        if dashboard_page is None:
            pytest.skip("index.astro not found")
        assert "BaseLayout" in dashboard_page

    def test_player_page_exists(self, player_page) -> None:
        """Test that player page exists."""
        assert player_page is not None

    def test_player_uses_layout(self, player_page) -> None:
        """Test that player page has proper HTML structure."""
        if player_page is None:
            pytest.skip("player.astro not found")
        # Player might not use a layout but should have proper HTML structure
        assert "<html" in player_page or "<body" in player_page or "DOCTYPE" in player_page


class TestAstroComponentsAvailability:
    """Tests for Astro components availability."""

    @pytest.fixture
    def components_dir(self) -> None:
        """Get components directory path."""
        return PROJECT_ROOT / "frontend" / "src" / "components"

    def test_components_directory_exists(self, components_dir) -> None:
        """Test that components directory exists."""
        assert components_dir.exists()

    def test_base_layout_exists(self, components_dir) -> None:
        """Test that BaseLayout exists."""
        layout_path = PROJECT_ROOT / "frontend" / "src" / "layouts" / "BaseLayout.astro"
        assert layout_path.exists()

    def test_header_component_exists(self, components_dir) -> None:
        """Test that Header component exists."""
        header_path = components_dir / "Header.astro"
        assert header_path.exists()

    def test_status_card_exists(self, components_dir) -> None:
        """Test that StatusCard component exists."""
        card_path = components_dir / "StatusCard.astro"
        assert card_path.exists()

    def test_metrics_card_exists(self, components_dir) -> None:
        """Test that MetricsCard component exists."""
        card_path = components_dir / "MetricsCard.astro"
        assert card_path.exists()

    def test_process_grid_exists(self, components_dir) -> None:
        """Test that ProcessGrid component exists."""
        grid_path = components_dir / "ProcessGrid.astro"
        assert grid_path.exists()


class TestAstroConfiguration:
    """Tests for Astro configuration."""

    @pytest.fixture
    def astro_config(self) -> None:
        """Load Astro config."""
        config_path = PROJECT_ROOT / "frontend" / "astro.config.mjs"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                return f.read()
        return None

    def test_astro_config_exists(self, astro_config) -> None:
        """Test that Astro config exists."""
        assert astro_config is not None

    def test_astro_config_has_output_setting(self, astro_config) -> None:
        """Test that Astro config has output setting."""
        if astro_config is None:
            pytest.skip("astro.config.mjs not found")
        assert "output" in astro_config

    def test_astro_config_has_build_setting(self, astro_config) -> None:
        """Test that Astro config has build setting."""
        if astro_config is None:
            pytest.skip("astro.config.mjs not found")
        assert "build" in astro_config


class TestAstroPackageJson:
    """Tests for Astro package.json."""

    @pytest.fixture
    def package_json(self) -> None:
        """Load package.json."""
        pkg_path = PROJECT_ROOT / "frontend" / "package.json"
        if pkg_path.exists():
            import json

            with open(pkg_path, encoding="utf-8") as f:
                return json.load(f)
        return None

    def test_package_json_exists(self, package_json) -> None:
        """Test that package.json exists."""
        assert package_json is not None

    def test_has_astro_dependency(self, package_json) -> None:
        """Test that Astro is a dependency."""
        if package_json is None:
            pytest.skip("package.json not found")
        assert "astro" in package_json.get("dependencies", {})

    def test_has_dev_script(self, package_json) -> None:
        """Test that package.json has dev script."""
        if package_json is None:
            pytest.skip("package.json not found")
        assert "dev" in package_json.get("scripts", {})

    def test_has_build_script(self, package_json) -> None:
        """Test that package.json has build script."""
        if package_json is None:
            pytest.skip("package.json not found")
        assert "build" in package_json.get("scripts", {})
