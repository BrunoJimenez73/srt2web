import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from cli.commands.status import run_status
from cli.commands.config import run_config_show, run_config_get


@pytest.mark.asyncio
async def test_show_config_command(mock_api, console):
    """Test the logic for showing current configuration."""
    mock_config = MagicMock()
    mock_config.raw = {"pipeline": {"mode": "thread_parallel"}}
    mock_api.get_config = AsyncMock(return_value=mock_config)

    result = await run_config_show(mock_api, console)
    assert result == 0
    mock_api.get_config.assert_called_once()


@pytest.mark.asyncio
async def test_get_config_value(mock_api, console):
    """Test getting a specific config value."""
    mock_config = MagicMock()
    mock_config.raw = {"server": {"port": 9999}}
    mock_api.get_config = AsyncMock(return_value=mock_config)

    result = await run_config_get(mock_api, console, key="server.port")
    assert result == 0
    mock_api.get_config.assert_called_once()
