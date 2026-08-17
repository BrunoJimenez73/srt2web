"""Tests for CLI tool and HTTP API endpoints."""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


def _collect_paths(routes: list) -> list[str]:
    """Collect route paths, handling FastAPI's nested _IncludedRouter entries.

    Newer FastAPI versions wrap routers included via ``include_router`` in
    ``_IncludedRouter`` objects inside ``router.routes``; those have no
    ``path`` attribute but expose their own nested ``routes`` list.
    """
    paths: list[str] = []
    for route in routes:
        if hasattr(route, "path"):
            paths.append(route.path)
        nested = getattr(route, "routes", None)
        if nested:
            paths.extend(_collect_paths(nested))
    return paths


class TestCLIEndpoints:
    """Test CLI can access API via HTTP."""

    @pytest.mark.asyncio
    async def test_api_router_class_exists(self):
        """Test API router class exists."""
        from server.api_routes import create_api_router

        assert callable(create_api_router)

    def test_api_router_has_start_endpoint(self) -> None:
        """Test router has start endpoint."""
        from server.api_routes import create_api_router

        router = create_api_router()
        paths = _collect_paths(router.routes)
        assert "/start" in paths or "/api/start" in paths

    def test_api_router_has_stop_endpoint(self) -> None:
        """Test router has stop endpoint."""
        from server.api_routes import create_api_router

        router = create_api_router()
        paths = _collect_paths(router.routes)
        assert "/stop" in paths or "/api/stop" in paths

    def test_api_router_has_status_endpoint(self) -> None:
        """Test router has status endpoint."""
        from server.api_routes import create_api_router

        router = create_api_router()
        paths = _collect_paths(router.routes)
        assert "/status" in paths or "/api/status" in paths

    def test_api_router_has_config_endpoint(self) -> None:
        """Test router has config endpoints."""
        from server.api_routes import create_api_router

        router = create_api_router()
        paths = _collect_paths(router.routes)
        assert "/config" in paths or "/api/config" in paths

    def test_api_router_has_health_endpoint(self) -> None:
        """Test router has health endpoint."""
        from server.api_routes import create_api_router

        router = create_api_router()
        paths = _collect_paths(router.routes)
        assert "/health" in paths or "/api/health" in paths


class TestCLIModuleNames:
    """Test CLI uses correct module names."""

    def test_valid_module_names_list(self) -> None:
        """Test valid module names are defined."""
        from server.validators import VALID_MODULE_NAMES

        assert isinstance(VALID_MODULE_NAMES, (list, tuple, frozenset))
        assert len(VALID_MODULE_NAMES) > 0
        assert "transcriber" in VALID_MODULE_NAMES


class TestCLIConfigUpdate:
    """Test CLI config update structures."""

    def test_config_update_model_exists(self) -> None:
        """Test ConfigUpdate model exists."""
        from server.validators import ConfigUpdate

        assert ConfigUpdate is not None

    def test_module_toggle_model_exists(self) -> None:
        """Test ModuleToggle model exists."""
        from server.validators import ModuleToggle

        assert ModuleToggle is not None


class TestCLIServerInfo:
    """Test CLI server info."""

    def test_api_router_has_network_info_route(self) -> None:
        """Test router has network info endpoint."""
        from server.api_routes import create_api_router

        router = create_api_router()
        paths = _collect_paths(router.routes)
        assert "/network/info" in paths


class TestCLIWebSocketRoutes:
    """Test CLI WebSocket routes."""

    def test_ws_routes_module_exists(self) -> None:
        """Test ws_routes module exists."""
        from server import ws_routes

        assert ws_routes is not None

    def test_ws_routes_has_create_ws_router(self) -> None:
        """Test ws_routes has create_ws_router function."""
        from server import ws_routes

        assert hasattr(ws_routes, "create_ws_router")
        assert callable(ws_routes.create_ws_router)


class TestCLIAPIFunctions:
    """Test API utility functions."""

    def test_sanitize_module_name_exists(self) -> None:
        """Test sanitize_module_name utility exists."""
        from server.validators import sanitize_module_name

        assert callable(sanitize_module_name)

    def test_validate_config_value_exists(self) -> None:
        """Test validate_config_value utility exists."""
        from server.validators import validate_config_value

        assert callable(validate_config_value)
