from unittest.mock import AsyncMock, MagicMock

import pytest
from cli.commands.start import run_start
from cli.commands.status import run_status
from cli.commands.stop import run_stop


@pytest.mark.asyncio
async def test_start_pipeline(mock_api, console):
    """Test successful start of the pipeline."""
    mock_api.start_pipeline = AsyncMock(return_value={"status": "started"})

    result = await run_start(mock_api, console)
    assert result == 0

    mock_api.start_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_start_pipeline_failure(mock_api, console):
    """Test start returning an unexpected status string."""
    mock_api.start_pipeline = AsyncMock(return_value={"status": "already_running"})

    result = await run_start(mock_api, console)
    assert result == 0  # command succeeds but prints a yellow warning

    mock_api.start_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_start_pipeline_api_error(mock_api, console):
    """Test start when the API raises."""
    mock_api.start_pipeline = AsyncMock(side_effect=Exception("API error"))

    result = await run_start(mock_api, console)
    assert result == 1


@pytest.mark.asyncio
async def test_stop_pipeline(mock_api, console):
    """Test successful stop of the pipeline."""
    mock_api.stop_pipeline = AsyncMock(return_value={"status": "stopped"})

    result = await run_stop(mock_api, console)
    assert result == 0

    mock_api.stop_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_stop_pipeline_api_error(mock_api, console):
    """Test stop when the API raises."""
    mock_api.stop_pipeline = AsyncMock(side_effect=Exception("API error"))

    result = await run_stop(mock_api, console)
    assert result == 1


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
    mock_status.concurrent_chunks = 2
    mock_status.max_concurrent_chunks = 4
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
