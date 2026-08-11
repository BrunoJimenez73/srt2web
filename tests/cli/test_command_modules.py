from unittest.mock import AsyncMock

import pytest
from cli.commands.module import run_module_debug
from cli.commands.start import run_start
from cli.commands.stop import run_stop


@pytest.mark.asyncio
async def test_start_command(mock_api, console):
    """Test the logic flow of starting a pipeline command."""
    mock_api.start_pipeline = AsyncMock(return_value={"status": "started"})

    result = await run_start(mock_api, console)
    assert result == 0

    mock_api.start_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_stop_command(mock_api, console):
    """Test the logic flow of stopping a pipeline command."""
    mock_api.stop_pipeline = AsyncMock(return_value={"status": "stopped"})

    result = await run_stop(mock_api, console)
    assert result == 0

    mock_api.stop_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_module_debug_command(mock_api, console):
    """Test retrieving debug info for a specific module (e.g., transcriber)."""
    mock_api.get_module_debug = AsyncMock(
        return_value={
            "name": "transcriber",
            "state": "running",
            "chunks_processed": 10,
            "chunks_failed": 0,
            "avg_processing_time_ms": 1000,
            "device": "cpu",
        }
    )

    result = await run_module_debug(mock_api, "transcriber", json_output=False)
    assert result == 0

    mock_api.get_module_debug.assert_called_with("transcriber")


@pytest.mark.asyncio
async def test_module_debug_api_error(mock_api, console):
    """Test module debug when the API raises."""
    mock_api.get_module_debug = AsyncMock(side_effect=Exception("API error"))

    result = await run_module_debug(mock_api, "transcriber", json_output=False)
    assert result == 1
