from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from cli.client.http_client import APIClient


@pytest.fixture
def api_client():
    """Fixture to provide a fresh, mocked APIClient instance."""
    with patch("cli.client.http_client.httpx.AsyncClient") as mock_httpx:
        mock_client = MagicMock()
        mock_httpx.return_value = mock_client
        yield APIClient(base_url="http://localhost:9999", token="test")


@pytest.mark.asyncio
async def test_api_client_get_modules(api_client):
    """Test GET /api/modules endpoint."""
    # NOTE: httpx Response.json() is synchronous (no await), so MagicMock, not AsyncMock
    expected_payload = {"modules": [{"name": "transcriber", "state": "running"}]}
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value=expected_payload)
    mock_response.raise_for_status = MagicMock()
    api_client._client.get = AsyncMock(return_value=mock_response)

    result = await api_client.get_modules()
    assert len(result) == 1
    assert result[0].name == "transcriber"
    assert result[0].state == "running"
    api_client._client.get.assert_called_with("/api/modules")


@pytest.mark.asyncio
async def test_api_client_update_output(api_client):
    """Test PUT /api/outputs/{name} endpoint for updating output configuration."""
    mock_response = MagicMock()
    mock_response.json = AsyncMock(return_value={"success": True})
    mock_response.raise_for_status = MagicMock()
    api_client._client.put = AsyncMock(return_value=mock_response)

    await api_client.update_output("hls", config={"bitrate": 3000000})
    api_client._client.put.assert_called_with("/api/outputs/hls", json={"config": {"bitrate": 3000000}})


@pytest.mark.asyncio
async def test_api_client_handle_404(api_client):
    """Test API client error handling for 404 Not Found."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("Not Found", request=MagicMock(), response=MagicMock(status_code=404))
    )
    api_client._client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(httpx.HTTPStatusError):
        await api_client.get_modules()
