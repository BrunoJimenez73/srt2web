"""Regression tests for cross-layer contracts found by the integration audit."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.mark.unit
class TestAuthAndStaticResourceContracts:
    def test_auth_token_uses_environment_when_config_is_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from server.ctx import get_auth_token

        config = Mock()
        config.get.return_value = ""
        monkeypatch.setenv("SRT2WEB_AUTH_TOKEN", "env-contract-token")
        monkeypatch.delenv("AUTH_TOKEN", raising=False)

        assert get_auth_token(config) == "env-contract-token"

    def test_configured_token_takes_precedence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from server.ctx import get_auth_token

        config = Mock()
        config.get.return_value = "config-contract-token"
        monkeypatch.setenv("SRT2WEB_AUTH_TOKEN", "env-contract-token")

        assert get_auth_token(config) == "config-contract-token"

    def test_subtitle_resources_share_the_public_hls_contract(self) -> None:
        from server.ctx import is_public_path

        assert is_public_path("/hls/master.m3u8")
        assert is_public_path("/subtitles/subs.m3u8")
        assert is_public_path("/subtitles/subs_seg_000001.vtt")
        assert not is_public_path("/api/modules")


@pytest.mark.unit
class TestWebSocketAuthContract:
    @pytest.fixture
    def app(self, monkeypatch: pytest.MonkeyPatch):
        from core.config_manager import ConfigManager
        from core.pipeline import Pipeline
        from server.app import create_app

        monkeypatch.delenv("SRT2WEB_TESTING", raising=False)
        monkeypatch.delenv("SRT2WEB_ALLOW_INSECURE_DEFAULTS", raising=False)
        config = ConfigManager()
        config.set("server.auth_token", "ws-contract-token")
        return create_app(
            {
                "config": config,
                "pipeline": Pipeline(),
                "srt_ingest": None,
                "log_broadcast": lambda level, message: None,
            }
        )

    def test_websocket_rejects_missing_query_token(self, app) -> None:
        with (
            TestClient(app) as client,
            pytest.raises(WebSocketDisconnect) as exc_info,
            client.websocket_connect("/ws/logs"),
        ):
            pass
        assert exc_info.value.code == 4001

    def test_websocket_accepts_query_token_and_handles_ping(self, app) -> None:
        with (
            TestClient(app) as client,
            client.websocket_connect("/ws/logs?token=ws-contract-token") as websocket,
        ):
            websocket.send_text('{"type":"ping"}')
            assert websocket.receive_json() == {"type": "pong"}


@pytest.mark.unit
def test_app_context_uses_pipeline_configuration(temp_dir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from core.app_context import create_app_context
    from core.config_manager import ConfigManager

    tmp_path = Path(temp_dir)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
pipeline:
  chunk_duration_sec: 7
  mode: sequential
  max_concurrent_chunks: 3
  buffer_size: 9
  retry_attempts: 4
  retry_delay: 1.5
  lost_chunk_timeout_sec: 22
  adaptive:
    enabled: true
    min_concurrent: 1
    max_concurrent: 3
""",
        encoding="utf-8",
    )
    monkeypatch.setattr("core.app_context._register_modules", lambda *args: None)

    context = create_app_context(ConfigManager(str(config_path)), str(tmp_path / "output"))
    pipeline = context["pipeline"]

    assert pipeline.mode.value == "sequential"
    assert pipeline.max_concurrent_chunks == 3
    assert pipeline.buffer_size == 9
    assert pipeline.retry_attempts == 4
    assert pipeline.retry_delay == 1.5
    assert pipeline.lost_chunk_timeout == 22
    assert pipeline._chunk_duration == 7
    assert pipeline._default_chunk_duration == 7
    assert pipeline._adaptive_config["enabled"] is True
    assert pipeline._adaptive_config["min_concurrent"] == 1
    assert pipeline._adaptive_config["max_concurrent"] == 3


@pytest.mark.unit
def test_hls_master_exposes_one_playlist_per_explicit_abr_profile(
    temp_dir: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from modules.outputs.hls_output import HLSOutput

    tmp_path = Path(temp_dir)

    ladder = [
        {"name": "low", "bandwidth": 500_000, "width": 854, "height": 480},
        {"name": "medium", "bandwidth": 1_500_000, "width": 1280, "height": 720},
        {"name": "high", "bandwidth": 3_000_000, "width": 1920, "height": 1080},
    ]
    monkeypatch.setattr("modules.outputs.hls_output.ensure_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(
        "modules.outputs.hls_output.check_gpu_support",
        lambda path: {"nvenc": False, "qsv": False, "amf": False, "vaapi": False, "videotoolbox": False},
    )

    output = HLSOutput({"output_dir": str(tmp_path), "bitrate_ladder": ladder})
    output._output_dir = str(tmp_path)
    output.start()

    master = (tmp_path / "hls" / "master.m3u8").read_text(encoding="utf-8")
    assert master.count("#EXT-X-STREAM-INF:") == 3
    assert "low.m3u8" in master
    assert "stream.m3u8" in master
    assert "high.m3u8" in master
    assert (tmp_path / "hls" / "low.m3u8").exists()
    assert (tmp_path / "hls" / "high.m3u8").exists()


@pytest.mark.unit
def test_hls_writes_variant_segments_and_media_playlists(temp_dir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from modules.outputs.hls_output import HLSOutput

    tmp_path = Path(temp_dir)
    ladder = [
        {"name": "low", "bandwidth": 500_000, "width": 854, "height": 480},
        {"name": "medium", "bandwidth": 1_500_000, "width": 1280, "height": 720},
        {"name": "high", "bandwidth": 3_000_000, "width": 1920, "height": 1080},
    ]
    output = HLSOutput({"output_dir": str(tmp_path), "bitrate_ladder": ladder})
    output._hls_dir = str(tmp_path / "hls")
    output._ffmpeg_path = "ffmpeg"
    output._pool = MagicMock()
    output._pool.acquire.return_value = True
    output._segment_durations[0] = 5.0
    os_path = Path(output._hls_dir)
    os_path.mkdir(parents=True, exist_ok=True)
    (os_path / "seg_000000.ts").write_bytes(b"primary")

    def fake_run(command, **kwargs):
        Path(command[-1]).write_bytes(b"variant")
        return Mock(returncode=0, stderr="")

    monkeypatch.setattr("modules.outputs.hls_output.subprocess.run", fake_run)
    output._generate_abr_variants(str(os_path / "seg_000000.ts"), 0)
    output._update_manifest()

    for name in ("low", "high"):
        assert (os_path / name / "seg_000000.ts").exists()
        playlist = (os_path / f"{name}.m3u8").read_text(encoding="utf-8")
        assert f"{name}/seg_000000.ts" in playlist


@pytest.mark.unit
def test_cli_websocket_auth_uses_query_parameter() -> None:
    from cli.client.ws_client import _with_token

    assert _with_token("ws://localhost:9999/ws/logs", "token with spaces") == (
        "ws://localhost:9999/ws/logs?token=token+with+spaces"
    )
