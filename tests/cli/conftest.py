from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from rich.console import Console


@pytest.fixture
def mock_api():
    api = MagicMock()
    api.token = None

    for method in [
        "get_status",
        "get_health",
        "start_pipeline",
        "stop_pipeline",
        "restart_pipeline",
        "get_config",
        "update_config",
        "update_chunk",
        "get_modules",
        "toggle_module",
        "get_module_debug",
        "get_outputs",
        "get_available_outputs",
        "add_output",
        "remove_output",
        "toggle_output",
        "update_output",
        "get_input_info",
        "control_input",
        "get_network_info",
        "get_available",
        "get_presets",
        "save_preset",
        "apply_preset",
        "delete_preset",
        "login",
        "get_recordings",
        "delete_recording",
        "health_check",
        "close",
    ]:
        setattr(api, method, AsyncMock())

    api.get_config.return_value = MagicMock(
        raw={"server": {"port": 9999, "host": "0.0.0.0"}, "modules": {}},
        get=lambda k: {"server.port": 9999}.get(k),
    )
    api.get_status.return_value = MagicMock(
        state="stopped",
        mode="thread_parallel",
        chunks_processed=0,
        chunks_failed=0,
        avg_processing_time_ms=0.0,
        uptime_seconds=0.0,
        max_concurrent_chunks=4,
        concurrent_chunks=0,
        buffer_size=0,
        strategy="thread_parallel",
        modules=[],
        system={},
        network={},
        sync={},
        input_receiving=False,
        input_info={},
    )
    api.get_health.return_value = MagicMock(
        status="ok",
        uptime_seconds=0,
        memory_mb=0,
        memory_percent=0,
        chunks_processed=0,
        pipeline_state="stopped",
        modules={},
        input={},
        output={},
    )
    api.get_outputs.return_value = []
    api.get_presets.return_value = {"presets": []}
    api.get_recordings.return_value = {"recordings": [], "total_count": 0, "total_size": 0}
    return api


@pytest.fixture
def mock_ws():
    ws = MagicMock()
    ws.connect = AsyncMock()
    ws.disconnect = AsyncMock()
    ws._handle_message = MagicMock()
    return ws


@pytest.fixture
def console():
    return Console(width=120, force_terminal=True, color_system=None, no_color=True)
