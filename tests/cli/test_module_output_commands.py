import pytest
from unittest.mock import MagicMock, AsyncMock
from cli.commands.module import run_module_list
from cli.commands.output import run_output_add
from cli.commands.preset import run_preset_list


@pytest.mark.asyncio
async def test_list_modules(mock_api):
    """Test the new 'module list' command."""
    expected_response = [{"name": "transcriber", "status": "running"}, {"name": "tts_engine", "status": "idle"}]
    mock_api.get_modules = AsyncMock(return_value=expected_response)

    result = await run_module_list(mock_api, json_output=False)
    assert result == 0
    mock_api.get_modules.assert_called_once()


@pytest.mark.asyncio
async def test_add_output(mock_api):
    """Test adding a new output type."""
    mock_api.add_output = AsyncMock(return_value={"success": True})

    result = await run_output_add(
        mock_api, output_type="rtmp", name=None, config='{"bitrate": 1500000}', json_output=False
    )
    assert result == 0
    mock_api.add_output.assert_called_once()


@pytest.mark.asyncio
async def test_list_presets(mock_api):
    """Test listing saved presets."""
    expected_response = [{"name": "default", "description": "Initial setup"}]
    mock_api.get_presets = AsyncMock(return_value=expected_response)

    result = await run_preset_list(mock_api, json_output=False)
    assert result == 0
    mock_api.get_presets.assert_called_once()
