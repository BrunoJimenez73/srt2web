import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from cli.commands.start import run_start
from cli.commands.stop import run_stop
from cli.commands.status import run_status


@pytest.mark.asyncio
async def test_start_pipeline(mock_api, console):
    """Test successful start of the pipeline."""
    mock_api.start_pipeline = AsyncMock(return_value={"success": True})
    mock_api.get_status = AsyncMock(return_value=MagicMock(state="running"))

    result = await run_start(mock_api, console)
    assert result == 0

    mock_api.start_pipeline.assert_called_once()
    mock_api.get_status.assert_called_once()


@pytest.mark.asyncio
async def test_stop_pipeline(mock_api, console):
    """Test successful stop of the pipeline."""
    mock_api.stop_pipeline = AsyncMock(return_value={"success": True})
    mock_api.get_status = AsyncMock(return_value=MagicMock(state="stopped"))

    result = await run_stop(mock_api, console)
    assert result == 0

    mock_api.stop_pipeline.assert_called_once()
    mock_api.get_status.assert_called_once()


@pytest.mark.asyncio
async def test_status_success(mock_api, console):
    """Test getting pipeline status."""
    mock_status = MagicMock()
    mock_status.state = "running"
    mock_status.mode = "thread_parallel"
    mock_status.chunks_processed = 10
    mock_status.chunks_failed = 0
    mock_status.avg_processing_time_ms = 1000
    mock_status.uptime_seconds = 3600
    mock_status.strategy = "thread_parallel"
    mock_status.modules = []
    mock_status.system = {"cpu_percent": 50.0, "memory_percent": 60.0, "memory_mb": 4096}
    mock_api.get_status = AsyncMock(return_value=mock_status)

    result = await run_status(mock_api, console)
    assert result == 0
    mock_api.get_status.assert_called_once()


@pytest.mark.asyncio
async def test_status_failure(mock_api, console):
    """Test status command failure handling."""
    mock_api.get_status = AsyncMock(side_effect=Exception("API error"))

    result = await run_status(mock_api, console)
    assert result == 1
