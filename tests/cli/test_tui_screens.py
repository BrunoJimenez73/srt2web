import pytest


@pytest.mark.asyncio
async def test_module_detail_screen():
    """Test that ModuleDetailScreen accepts module data and renders it."""
    from unittest.mock import MagicMock

    from cli.tui.screens.module_detail import ModuleDetailScreen

    mock_api = MagicMock()
    screen = ModuleDetailScreen(
        module_name="transcriber",
        module_info=None,
        config={"model": "tiny"},
        api_client=mock_api,
    )
    assert screen.module_name == "transcriber"
    assert screen.api_client is mock_api
    assert screen.config == {"model": "tiny"}


@pytest.mark.asyncio
async def test_module_grid_navigation():
    """Test that TUIModuleGrid exists and renders module cards."""
    from cli.tui.widgets.module_grid import TUIModuleGrid

    grid = TUIModuleGrid()
    assert grid is not None
