import pytest
from unittest.mock import MagicMock, AsyncMock
from cli.commands.start import run_start
from cli.commands.stop import run_stop
from cli.commands.status import run_status


@pytest.mark.asyncio
async def test_start_command(mock_api, console):
    """Test the logic flow of starting a pipeline command."""
    mock_api.start_pipeline = AsyncMock(return_value={"success": True})
    mock_api.get_status = AsyncMock(return_value=MagicMock(state="running"))

    result = await run_start(mock_api, console)
    assert result == 0

    mock_api.start_pipeline.assert_called_once()
    mock_api.get_status.assert_called_once()


@pytest.mark.asyncio
async def test_stop_command(mock_api, console):
    """Test the logic flow of stopping a pipeline command."""
    mock_api.stop_pipeline = AsyncMock(return_value={"success": True})
    mock_api.get_status = AsyncMock(return_value=MagicMock(state="stopped"))

    result = await run_stop(mock_api, console)
    assert result == 0

    mock_api.stop_pipeline.assert_called_once()
    mock_api.get_status.assert_called_once()


@pytest.mark.asyncio
async def test_status_get_module_status(mock_api, console):
    """Test retrieving status for a specific module (e.g., transcriber)."""
    mock_module_debug = MagicMock()
    mock_module_debug.name = "transcriber"
    mock_module_debug.status = "running"
    mock_module_debug.chunks_processed = 10
    mock_module_debug.chunks_failed = 0
    mock_module_debug.avg_processing_time_ms = 1000

    mock_api.get_module_debug = AsyncMock(return_value=mock_module_debug)

    result = await run_status(mock_api, console, module_name="transcriber")
    assert result == 0

    mock_api.get_module_debug.assert_called_with("transcriber")
