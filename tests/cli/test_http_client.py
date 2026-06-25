from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from cli.client.http_client import (
    APIClient,
    ConfigData,
    HealthInfo,
    ModuleInfo,
    NetworkInfo,
    OutputInfo,
    PipelineStatus,
)

# ── mock helpers ──


def _mock_response(json_data, status_code=200):
    r = MagicMock(spec=httpx.Response)
    r.status_code = status_code
    r.json.return_value = json_data
    r.raise_for_status = MagicMock()
    return r


class TestAPIClientHTTP:
    """Tests APIClient HTTP methods by mocking httpx.AsyncClient methods."""

    @pytest.fixture
    def mock_httpx(self):
        with patch("cli.client.http_client.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            mock_cls.return_value = client
            yield client

    @pytest.mark.asyncio
    async def test_get_status(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response(
            {"state": "running", "mode": "thread_parallel", "chunks_processed": 10}
        )
        api = APIClient()
        result = await api.get_status()
        assert isinstance(result, PipelineStatus)
        assert result.state == "running"
        assert result.chunks_processed == 10
        mock_httpx.get.assert_called_once_with("/api/status")

    @pytest.mark.asyncio
    async def test_get_status_empty(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response({})
        api = APIClient()
        result = await api.get_status()
        assert isinstance(result, PipelineStatus)
        assert result.state == ""

    @pytest.mark.asyncio
    async def test_get_health(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response(
            {"status": "ok", "pipeline_state": "running", "uptime_seconds": 120}
        )
        api = APIClient()
        result = await api.get_health()
        assert isinstance(result, HealthInfo)
        assert result.status == "ok"
        assert result.uptime_seconds == 120

    @pytest.mark.asyncio
    async def test_start_pipeline(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"status": "started"})
        api = APIClient()
        result = await api.start_pipeline()
        assert result["status"] == "started"
        mock_httpx.post.assert_called_once_with("/api/start", json={}, timeout=httpx.Timeout(30.0, connect=5.0))

    @pytest.mark.asyncio
    async def test_stop_pipeline(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"status": "stopped"})
        api = APIClient()
        result = await api.stop_pipeline()
        assert result["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_restart_pipeline(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"status": "restarted"})
        api = APIClient()
        result = await api.restart_pipeline()
        assert result["status"] == "restarted"

    @pytest.mark.asyncio
    async def test_get_config(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response({"server": {"port": 9999}})
        api = APIClient()
        result = await api.get_config()
        assert isinstance(result, ConfigData)
        assert result.get("server.port") == 9999

    @pytest.mark.asyncio
    async def test_update_config(self, mock_httpx):
        mock_httpx.put.return_value = _mock_response({"status": "ok"})
        api = APIClient()
        result = await api.update_config({"server": {"port": 8080}})
        assert result["status"] == "ok"
        mock_httpx.put.assert_called_once_with("/api/config", json={"config": {"server": {"port": 8080}}})

    @pytest.mark.asyncio
    async def test_update_chunk(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"status": "ok", "chunk_duration_sec": 15})
        api = APIClient()
        result = await api.update_chunk(15)
        assert result["chunk_duration_sec"] == 15

    @pytest.mark.asyncio
    async def test_get_modules(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response(
            {"modules": [{"name": "transcriber", "state": "running", "enabled": True}]}
        )
        api = APIClient()
        result = await api.get_modules()
        assert len(result) == 1
        assert isinstance(result[0], ModuleInfo)
        assert result[0].name == "transcriber"

    @pytest.mark.asyncio
    async def test_get_modules_empty(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response({"modules": []})
        api = APIClient()
        result = await api.get_modules()
        assert result == []

    @pytest.mark.asyncio
    async def test_toggle_module(self, mock_httpx):
        mock_httpx.put.return_value = _mock_response({"module": "tts_engine", "enabled": False})
        api = APIClient()
        result = await api.toggle_module("tts_engine", False)
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_get_module_debug(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response({"name": "transcriber", "state": "running"})
        api = APIClient()
        result = await api.get_module_debug("transcriber")
        assert result["state"] == "running"

    @pytest.mark.asyncio
    async def test_get_outputs(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response({"outputs": [{"name": "hls", "type": "hls", "state": "running"}]})
        api = APIClient()
        result = await api.get_outputs()
        assert len(result) == 1
        assert isinstance(result[0], OutputInfo)
        assert result[0].name == "hls"

    @pytest.mark.asyncio
    async def test_get_outputs_empty(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response({"outputs": []})
        api = APIClient()
        result = await api.get_outputs()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_available_outputs(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response({"available_types": ["hls", "rtmp", "webrtc"]})
        api = APIClient()
        result = await api.get_available_outputs()
        assert "hls" in result

    @pytest.mark.asyncio
    async def test_add_output(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"status": "ok", "name": "my_hls", "type": "hls"})
        api = APIClient()
        result = await api.add_output("hls", name="my_hls")
        assert result["name"] == "my_hls"

    @pytest.mark.asyncio
    async def test_add_output_with_config(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"status": "ok"})
        api = APIClient()
        result = await api.add_output("rtmp", config={"url": "rtmp://example.com/live"})
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_remove_output(self, mock_httpx):
        mock_httpx.delete.return_value = _mock_response({"status": "ok", "name": "hls"})
        api = APIClient()
        result = await api.remove_output("hls")
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_toggle_output(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"status": "ok", "name": "hls", "enabled": False})
        api = APIClient()
        result = await api.toggle_output("hls", enabled=False)
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_toggle_output_no_arg(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"status": "ok", "name": "hls", "enabled": True})
        api = APIClient()
        result = await api.toggle_output("hls")
        assert result["enabled"] is True

    @pytest.mark.asyncio
    async def test_get_input_info(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response({"type": "srt", "url": "srt://localhost:5000"})
        api = APIClient()
        result = await api.get_input_info()
        assert result["type"] == "srt"

    @pytest.mark.asyncio
    async def test_control_input(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"status": "playing"})
        api = APIClient()
        result = await api.control_input("play")
        assert result["status"] == "playing"

    @pytest.mark.asyncio
    async def test_control_input_seek(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"status": "seeked", "position": 30.0})
        api = APIClient()
        result = await api.control_input("seek", {"position": 30.0})
        assert result["position"] == 30.0

    @pytest.mark.asyncio
    async def test_get_network_info(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response(
            {"server_port": 9999, "local_ip": "192.168.1.5", "srt_mode": "listener"}
        )
        api = APIClient()
        result = await api.get_network_info()
        assert isinstance(result, NetworkInfo)
        assert result.local_ip == "192.168.1.5"

    @pytest.mark.asyncio
    async def test_get_available(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response({"inputs": ["srt", "file"], "outputs": ["hls"]})
        api = APIClient()
        result = await api.get_available()
        assert "inputs" in result

    @pytest.mark.asyncio
    async def test_get_presets(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response({"presets": [{"name": "low-latency"}]})
        api = APIClient()
        result = await api.get_presets()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_save_preset(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"status": "ok", "name": "my-preset"})
        api = APIClient()
        result = await api.save_preset("my-preset", "My custom preset")
        assert result["name"] == "my-preset"

    @pytest.mark.asyncio
    async def test_apply_preset(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"status": "ok", "name": "low-latency"})
        api = APIClient()
        result = await api.apply_preset("low-latency")
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_delete_preset(self, mock_httpx):
        mock_httpx.delete.return_value = _mock_response({"status": "ok", "name": "old-preset"})
        api = APIClient()
        result = await api.delete_preset("old-preset")
        assert result["name"] == "old-preset"

    @pytest.mark.asyncio
    async def test_get_recordings(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response({"recordings": [{"name": "rec1.mp4", "size_bytes": 1024}]})
        api = APIClient()
        result = await api.get_recordings()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_delete_recording(self, mock_httpx):
        mock_httpx.delete.return_value = _mock_response({"status": "ok", "name": "rec1.mp4"})
        api = APIClient()
        result = await api.delete_recording("rec1.mp4")
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_check(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response({"status": "ok"})
        api = APIClient()
        result = await api.health_check()
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_login(self, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"access_token": "jwt123", "user": {"username": "admin"}})
        api = APIClient()
        token = await api.login("admin", "secret")
        assert token == "jwt123"
        assert api.token == "jwt123"

    @pytest.mark.asyncio
    async def test_unauthorized_raises_permission_error(self, mock_httpx):
        r = MagicMock(spec=httpx.Response)
        r.status_code = 401
        r.raise_for_status.side_effect = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=r)
        mock_httpx.get.return_value = r
        api = APIClient()
        with pytest.raises(PermissionError, match="Authentication required"):
            await api.get_status()

    @pytest.mark.asyncio
    async def test_close(self, mock_httpx):
        api = APIClient()
        await api.close()
        mock_httpx.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_auth_header_included(self, mock_httpx):
        api = APIClient(token="my-secret-token")
        assert api._headers()["Authorization"] == "Bearer my-secret-token"
