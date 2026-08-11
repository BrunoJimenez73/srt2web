from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# --- Fixtures for Mocking Clients and Services ---


@pytest.fixture(scope="session")
def mock_api():
    """Provides a fully mocked APIClient instance with all expected methods."""
    from cli.client.http_client import ConfigData, PipelineStatus

    mock = MagicMock()
    # Pipeline methods
    mock.start_pipeline = AsyncMock(return_value={"status": "started"})
    mock.stop_pipeline = AsyncMock(return_value={"status": "stopped"})
    mock.get_status = AsyncMock(return_value=PipelineStatus(state="running", mode="thread_parallel"))
    # Config methods (real ConfigData object so .raw/.get/.set work)
    config = ConfigData.from_dict({"server": {"port": 9999}, "modules": {"tts": {"enabled": True}}})
    mock.get_config = AsyncMock(return_value=config)
    mock.update_config = AsyncMock(return_value={"success": True})
    # Module methods
    mock.get_modules = AsyncMock(return_value=[])
    mock.get_module_debug = AsyncMock(return_value={})
    mock.toggle_module = AsyncMock(return_value={"success": True})
    # Output methods
    mock.get_outputs = AsyncMock(return_value=[])
    mock.add_output = AsyncMock(return_value={"success": True})
    mock.remove_output = AsyncMock(return_value={"success": True})
    mock.toggle_output = AsyncMock(return_value={"success": True})
    mock.update_output = AsyncMock(return_value={"success": True})
    # Preset methods
    mock.get_presets = AsyncMock(return_value=[])
    mock.save_preset = AsyncMock(return_value={"success": True})
    mock.apply_preset = AsyncMock(return_value={"success": True})
    mock.delete_preset = AsyncMock(return_value={"success": True})
    # Input methods
    mock.get_input_info = AsyncMock(return_value={})
    mock.control_input = AsyncMock(return_value={"success": True})
    # Recording methods
    mock.get_recordings = AsyncMock(return_value=[])
    mock.delete_recording = AsyncMock(return_value={"success": True})
    mock.download_recording = AsyncMock(return_value=b"data")
    # Network methods
    mock.get_network_info = AsyncMock(return_value={})
    # Health methods
    mock.get_health = AsyncMock(return_value={"status": "healthy"})
    mock.health_check = AsyncMock(return_value={"status": "healthy"})
    # Auth
    mock.login = AsyncMock(return_value={"token": "test-token"})
    # Generic getters
    mock.get = AsyncMock(return_value={})
    mock.post = AsyncMock(return_value={"success": True})
    mock.put = AsyncMock(return_value={"success": True})
    mock.delete = AsyncMock(return_value={"success": True})

    yield mock
    mock.reset_mock()


@pytest.fixture(scope="session")
def console():
    """Provides a mocked Rich Console."""
    with patch("rich.console.Console") as MockConsole:
        yield MockConsole.return_value


@pytest.fixture(scope="session")
def mock_ws_client():
    """Provides a fully mocked WSClient instance."""
    with patch("cli.client.ws_client.WSClient") as MockWSClient:
        mock_instance = MockWSClient.return_value
        mock_instance.connect = AsyncMock()
        mock_instance.disconnect = AsyncMock()
        mock_instance.send = AsyncMock()
        mock_instance.receive = AsyncMock()
        yield mock_instance
        MockWSClient.reset_mock()


# --- Fixtures for Test Data ---


@pytest.fixture(scope="session")
def sample_config():
    """Returns a standard, valid configuration dictionary."""
    return {
        "pipeline": {
            "input": {"type": "file", "path": "/tmp/input.srt"},
            "modules": {
                "transcriber": {"enabled": True, "config": {"model": "whisper-large"}},
                "translator": {"enabled": False},
            },
            "output": {"type": "hls", "path": "/tmp/output.m3u8"},
        }
    }


@pytest.fixture(scope="session")
def sample_modules():
    """Returns a dictionary representing module status."""
    return {
        "transcriber": {"status": "running", "chunks": 10},
        "translator": {"status": "idle", "chunks": 0},
        "tts_engine": {"status": "stopped", "chunks": 0},
    }
