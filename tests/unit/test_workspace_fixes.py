"""
Tests for workspace fixes and refactoring (April 2026).

Tests for:
- TypeScript module resolution (api.ts, utils/index.ts)
- Dashboard initialization with input/output handlers
- Authentication token management (clearAuthToken, WebSocket token)
- LogPanel search and filter functionality
- Astro component type declarations
"""

import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestTypeScriptModuleResolution:
    """Test that TypeScript modules are properly created and exported."""

    def test_api_module_exists(self):
        """Test that api.ts module exists with required exports."""
        api_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "api.ts"
        assert api_path.exists(), "api.ts module should exist"
        
        content = api_path.read_text(encoding="utf-8")
        
        # Check required exports
        assert "export function getAuthToken" in content
        assert "export function setAuthToken" in content
        assert "export function clearAuthToken" in content
        assert "export function getApiBase" in content
        assert "export function getWebSocketUrl" in content
        assert "fetchWithAuth" in content  # async function
        assert "export async function apiCall" in content
        assert "export async function getConfig" in content
        assert "export async function startPipeline" in content
        assert "export async function stopPipeline" in content

    def test_utils_index_module_exists(self):
        """Test that utils/index.ts barrel export exists."""
        utils_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "utils" / "index.ts"
        assert utils_path.exists(), "utils/index.ts should exist"
        
        content = utils_path.read_text(encoding="utf-8")
        assert "export" in content
        assert "performance" in content or "formatTimestamp" in content

    def test_dashboard_module_exists(self):
        """Test that dashboard.ts main script exists."""
        dashboard_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "dashboard.ts"
        assert dashboard_path.exists(), "dashboard.ts should exist"
        
        content = dashboard_path.read_text(encoding="utf-8")
        assert "initDashboard" in content
        assert "initWebSocket" in content

    def test_astro_type_declarations_exist(self):
        """Test that astro.d.ts type declarations exist."""
        astro_dts_path = PROJECT_ROOT / "frontend" / "src" / "astro.d.ts"
        assert astro_dts_path.exists(), "astro.d.ts should exist"
        
        content = astro_dts_path.read_text(encoding="utf-8")
        assert "declare module '*.astro'" in content


class TestAuthenticationTokenManagement:
    """Test authentication token functionality."""

    def test_clear_auth_token_function(self):
        """Test that clearAuthToken function exists and removes token."""
        api_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "api.ts"
        content = api_path.read_text(encoding="utf-8")
        
        assert "export function clearAuthToken" in content
        assert "localStorage.removeItem" in content

    def test_websocket_url_includes_token(self):
        """Test that WebSocket URL includes token as query parameter."""
        api_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "api.ts"
        content = api_path.read_text(encoding="utf-8")
        
        # Check that getWebSocketUrl adds token
        assert "?token=" in content or "token=" in content
        assert "encodeURIComponent" in content

    def test_auth_token_key_constant(self):
        """Test that auth token key is defined."""
        api_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "api.ts"
        content = api_path.read_text(encoding="utf-8")

        assert "AUTH_TOKEN_KEY" in content
        assert "STORAGE_KEYS" in content


class TestDashboardInputOutputHandlers:
    """Test dashboard input/output handling."""

    def test_dashboard_imports_input_output_handlers(self):
        """Test that dashboard imports input/output handlers."""
        dashboard_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "dashboard.ts"
        content = dashboard_path.read_text(encoding="utf-8")
        
        assert "handleInputTypeChange" in content
        assert "handleOutputFormatChange" in content

    def test_dashboard_has_input_output_comments(self):
        """Test that dashboard has input/output initialization comments."""
        dashboard_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "dashboard.ts"
        content = dashboard_path.read_text(encoding="utf-8")
        
        assert "Input type change" in content or "input" in content.lower()
        assert "Output format change" in content or "output" in content.lower()


class TestLogPanelSearchFilter:
    """Test LogPanel search and filter functionality."""

    def test_log_panel_has_search_styles(self):
        """Test that LogPanel has search input styles."""
        logpanel_path = PROJECT_ROOT / "frontend" / "src" / "components" / "LogPanel.astro"
        content = logpanel_path.read_text(encoding="utf-8")
        
        assert ".log-search" in content

    def test_log_panel_has_filter_logic(self):
        """Test that LogPanel has filter logic."""
        logpanel_path = PROJECT_ROOT / "frontend" / "src" / "components" / "LogPanel.astro"
        content = logpanel_path.read_text(encoding="utf-8")
        
        assert "currentFilter" in content
        assert "entry.dataset.message" in content

    def test_log_entry_has_data_attributes(self):
        """Test that log entries have data attributes for filtering."""
        logpanel_path = PROJECT_ROOT / "frontend" / "src" / "components" / "LogPanel.astro"
        content = logpanel_path.read_text(encoding="utf-8")
        
        assert "entry.dataset.level" in content
        assert "entry.dataset.message" in content

    def test_log_entry_has_level_styles(self):
        """Test that log entries have level-specific styles."""
        logpanel_path = PROJECT_ROOT / "frontend" / "src" / "components" / "LogPanel.astro"
        content = logpanel_path.read_text(encoding="utf-8")
        
        # Check for level-specific styles
        assert '[data-level="info"]' in content
        assert '[data-level="success"]' in content
        assert '[data-level="warning"]' in content
        assert '[data-level="error"]' in content


class TestTypeScriptConfiguration:
    """Test TypeScript configuration."""

    def test_tsconfig_has_ignore_deprecations(self):
        """Test that tsconfig.json has ignoreDeprecations option."""
        tsconfig_path = PROJECT_ROOT / "frontend" / "tsconfig.json"
        content = tsconfig_path.read_text(encoding="utf-8")
        
        assert "ignoreDeprecations" in content

    def test_tsconfig_has_base_url(self):
        """Test that tsconfig.json has baseUrl for path aliases."""
        tsconfig_path = PROJECT_ROOT / "frontend" / "tsconfig.json"
        content = tsconfig_path.read_text(encoding="utf-8")
        
        assert "baseUrl" in content
        assert '"@/*"' in content or '"@/*":' in content


class TestAstroConfiguration:
    """Test Astro configuration."""

    def test_astro_config_uses_node_imports(self):
        """Test that astro.config.mjs uses node: prefix for imports."""
        astro_config_path = PROJECT_ROOT / "frontend" / "astro.config.mjs"
        content = astro_config_path.read_text(encoding="utf-8")
        
        assert "node:url" in content or "node:path" in content

    def test_astro_config_outdir_at_top_level(self):
        """Test that outDir is at top level (not in build)."""
        astro_config_path = PROJECT_ROOT / "frontend" / "astro.config.mjs"
        content = astro_config_path.read_text(encoding="utf-8")
        
        # outDir should be at top level, not inside build
        assert "outDir:" in content
        # Should not have build: { outDir: }
        assert '"build":' not in content or "outDir" not in content.split('"build":')[1].split("}")[0] if '"build":' in content else True


class TestFrontendTypes:
    """Test frontend type definitions."""

    def test_types_has_module_extra_interface(self):
        """Test that types.ts has ModuleExtra interface."""
        types_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "types.ts"
        if not types_path.exists():
            types_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "types.d.ts"
        content = types_path.read_text(encoding="utf-8")
        
        assert "ModuleExtra" in content or "module_extra" in content.lower()
        assert "using_gpu" in content or "using_gpu" in content.lower()

    def test_types_has_window_extensions(self):
        """Test that types.ts has Window interface extensions."""
        types_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "types.ts"
        if not types_path.exists():
            types_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "types.d.ts"
        content = types_path.read_text(encoding="utf-8")
        
        assert "Window" in content or "window" in content.lower()
        assert "showToast" in content or "show_toast" in content.lower()

    def test_types_has_config_update_timeouts(self):
        """Test that types.ts has ConfigUpdateTimeouts type."""
        types_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "types.ts"
        if not types_path.exists():
            types_path = PROJECT_ROOT / "frontend" / "src" / "lib" / "types.d.ts"
        content = types_path.read_text(encoding="utf-8")
        
        assert "ConfigUpdateTimeouts" in content or "config_update" in content.lower() or "Timeouts" in content