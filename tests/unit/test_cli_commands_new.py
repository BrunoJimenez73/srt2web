from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cli.client.http_client import APIClient


@pytest.fixture
def mock_api_client():
    """Create a mock APIClient for testing."""
    with patch("cli.client.http_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        api = APIClient("http://test.server", "test-token")
        api._client = mock_client
        yield api, mock_client


@pytest.mark.asyncio
async def test_update_output(mock_api_client):
    """Test update_output method."""
    api, mock_client = mock_api_client

    # Mock the PUT response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_client.put = AsyncMock(return_value=mock_response)

    # Test with config only
    result = await api.update_output("test-output", config={"bitrate": "5000k"})
    assert result == {"status": "ok"}
    mock_client.put.assert_called_once_with("/api/outputs/test-output", json={"config": {"bitrate": "5000k"}})

    # Reset mock
    mock_client.reset_mock()

    # Test with enabled only
    result = await api.update_output("test-output", enabled=False)
    assert result == {"status": "ok"}
    mock_client.put.assert_called_once_with("/api/outputs/test-output", json={"enabled": False})

    # Reset mock
    mock_client.reset_mock()

    # Test with both config and enabled
    result = await api.update_output("test-output", config={"fps": 30}, enabled=True)
    assert result == {"status": "ok"}
    mock_client.put.assert_called_once_with("/api/outputs/test-output", json={"config": {"fps": 30}, "enabled": True})


@pytest.mark.asyncio
async def test_download_recording(mock_api_client):
    """Test download_recording method."""
    api, mock_client = mock_api_client

    # Mock the GET response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = b"fake video data"
    mock_client.get.return_value = mock_response

    # Test download
    result = await api.download_recording("test_recording.mp4")
    assert result == b"fake video data"
    mock_client.get.assert_called_once_with("/api/recordings/test_recording.mp4/download")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
