"""
Integration tests for API routes.
Extends test_server.py coverage with auth, presets, config validation,
health detail, and error paths not covered in the basic tests.
"""

from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from core.auth_db import auth_db
from core.config_manager import ConfigManager
from core.pipeline import Pipeline
from server.app import create_app


def _make_client(
    *,
    pipeline_running: bool = False,
    pipeline_chunks: int = 0,
    output_dir: str | None = None,
) -> TestClient:
    """Create a TestClient with optional pipeline state.

    F109: Added ``pipeline_running``, ``pipeline_chunks`` and ``output_dir`` so
    tests can assert readiness probe behavior and use isolated filesystem
    paths (e.g. ``tmp_path``) instead of touching the real ``./output/``.

    When ``pipeline_running=True`` we swap the real ``Pipeline`` for a ``Mock``
    because ``is_running`` and ``chunks_processed`` are read-only properties on
    ``UnifiedPipeline``. Tests that exercise the live pipeline can still pass
    ``pipeline_running=False`` (default) and use a real ``Pipeline()``.
    """
    if pipeline_running:
        pipeline = Mock(spec=Pipeline)
        pipeline.is_running = True
        pipeline.state = "running"
        pipeline.get_status.return_value = {"state": "running"}
        pipeline.chunks_processed = pipeline_chunks
    else:
        pipeline = Pipeline()
    ctx: dict[str, Any] = {
        "config": ConfigManager(),
        "pipeline": pipeline,
        "srt_ingest": None,
        "log_broadcast": Mock(),
    }
    if output_dir is not None:
        ctx["output_dir"] = output_dir
    app = create_app(ctx)
    return TestClient(app)


def _ensure_admin() -> tuple[str, str]:
    auth_db.create_user("admin", "admin", "admin")
    return "admin", "admin"


def _login(client: TestClient, username: str = "admin", password: str = "admin") -> str:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["token"]


class TestAuthRoutes:
    """Authentication endpoint tests."""

    @pytest.fixture(autouse=True)
    def setup_users(self):
        _ensure_admin()
        for name in ["testuser_auth"]:
            auth_db.delete_user(name)
        yield
        for name in ["testuser_auth", "testuser_register"]:
            auth_db.delete_user(name)

    def test_login_success(self):
        client = _make_client()
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"

    def test_login_invalid_credentials(self):
        client = _make_client()
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
        assert resp.status_code == 401

    def test_login_validation_empty(self):
        client = _make_client()
        resp = client.post("/api/auth/login", json={"username": "", "password": ""})
        assert resp.status_code == 422

    def test_logout(self):
        client = _make_client()
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["status"] == "logged_out"

    def test_me_with_valid_token(self):
        client = _make_client()
        token = _login(client)
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_me_without_token(self):
        client = _make_client()
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self):
        client = _make_client()
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken123"})
        assert resp.status_code == 401

    def test_register_user(self):
        client = _make_client()
        token = _login(client)
        resp = client.post(
            "/api/auth/register",
            json={"username": "testuser_register", "password": "test1234", "role": "viewer"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "created"

    def test_register_duplicate(self):
        client = _make_client()
        token = _login(client)
        resp = client.post(
            "/api/auth/register",
            json={"username": "admin", "password": "test1234", "role": "viewer"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    def test_list_users(self):
        client = _make_client()
        token = _login(client)
        resp = client.get("/api/auth/users", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        users = resp.json()["users"]
        roles = [u["role"] for u in users]
        assert "admin" in roles

    def test_list_users_unauthorized(self):
        client = _make_client()
        resp = client.get("/api/auth/users")
        assert resp.status_code == 401

    def test_delete_user(self):
        client = _make_client()
        token = _login(client)
        auth_db.create_user("testuser_auth", "del1234", "viewer")
        resp = client.delete(
            "/api/auth/users/testuser_auth",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_delete_admin_forbidden(self):
        client = _make_client()
        token = _login(client)
        resp = client.delete(
            "/api/auth/users/admin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_update_role(self):
        client = _make_client()
        token = _login(client)
        auth_db.create_user("testuser_auth", "role1234", "viewer")
        resp = client.put(
            "/api/auth/users/testuser_auth/role",
            json={"role": "operator"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "operator"
        auth_db.delete_user("testuser_auth")


class TestHealthEndpoints:
    """Health, ready, live endpoint tests."""

    def test_simple_health(self):
        client = _make_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_ready_endpoint(self):
        # F109: /ready returns 200 only when pipeline is running with state=running.
        # F102 diseñó el endpoint como readiness probe real (503 si no está listo).
        client = _make_client(pipeline_running=True, pipeline_chunks=5)
        resp = client.get("/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["chunks_processed"] == 5

    def test_ready_endpoint_not_running_returns_503(self):
        # F109: verify el comportamiento 503 cuando pipeline está idle (added en F102).
        client = _make_client()
        resp = client.get("/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "not_ready"

    def test_live_endpoint(self):
        client = _make_client()
        resp = client.get("/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    def test_api_health_format(self):
        client = _make_client()
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data  # healthy/degraded/unhealthy
        assert "uptime_seconds" in data
        assert "memory_mb" in data
        assert "chunks_processed" in data
        assert "pipeline_state" in data
        assert "modules" in data
        assert "input" in data
        assert "output" in data


class TestConfigEndpoints:
    """Configuration endpoint tests."""

    def test_get_config(self):
        client = _make_client()
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "server" in data
        assert "modules" in data

    def test_update_config_dependency_error(self):
        """Enable subtitle_generator but disable translator -> dependency error."""
        client = _make_client()
        resp = client.put(
            "/api/config",
            json={
                "config": {
                    "modules": {
                        "translator": {"enabled": False},
                        "subtitle_generator": {"enabled": True},
                    }
                }
            },
        )
        assert resp.status_code == 400
        assert "subtitle_generator requires translator to be enabled" in resp.text

    def test_update_config_valid(self):
        client = _make_client()
        resp = client.put("/api/config", json={"config": {"server": {"port": 9999}}})
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

    def test_video_muxer_endpoint(self):
        client = _make_client()
        resp = client.put(
            "/api/config/video_muxer",
            json={
                "encoder_mode": "gpu_nvenc",
                "video_crf": 23,
                "video_preset": "fast",
                "gpu_preset": "p4",
                "audio_bitrate": "128k",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

    def test_video_muxer_no_keys(self):
        client = _make_client()
        resp = client.put("/api/config/video_muxer", json={"unknown_key": "value"})
        assert resp.status_code == 400

    def test_chunk_duration_valid(self):
        client = _make_client()
        resp = client.post("/api/config/chunk", json={"chunk_duration_sec": 4})
        assert resp.status_code == 200
        data = resp.json()
        assert data["chunk_duration_sec"] == 4
        assert "list_size" in data
        assert "buffer_sec" in data

    def test_chunk_duration_too_low(self):
        client = _make_client()
        resp = client.post("/api/config/chunk", json={"chunk_duration_sec": 0})
        assert resp.status_code == 422

    def test_chunk_duration_too_high(self):
        client = _make_client()
        resp = client.post("/api/config/chunk", json={"chunk_duration_sec": 100})
        assert resp.status_code == 422

    def test_chunk_duration_clamped_high(self):
        """Server enforces 2-30 range, but Pydantic accepts 1-60."""
        client = _make_client()
        resp = client.post("/api/config/chunk", json={"chunk_duration_sec": 30})
        assert resp.status_code == 200


class TestPresetEndpoints:
    """Preset lifecycle tests."""

    @pytest.fixture(autouse=True)
    def cleanup_presets(self):
        yield
        cm = ConfigManager()
        for name in ["low_latency", "test_preset_e2e", "test_apply_preset"]:
            try:
                cm.delete_preset(name)
            except (KeyError, Exception):
                pass

    def test_list_presets(self):
        client = _make_client()
        resp = client.get("/api/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert "presets" in data
        names = [p["name"] for p in data["presets"]]
        assert "low_latency" in names  # built-in

    def test_save_and_delete_preset(self):
        client = _make_client()
        resp = client.post("/api/presets", json={"name": "test_preset_e2e", "description": "test preset"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "saved"

        resp = client.get("/api/presets")
        names = [p["name"] for p in resp.json()["presets"]]
        assert "test_preset_e2e" in names

        resp = client.delete("/api/presets/test_preset_e2e")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_apply_custom_preset(self):
        client = _make_client()
        resp = client.post("/api/presets", json={"name": "test_apply_preset", "description": "safe preset"})
        assert resp.status_code == 200

        resp = client.post("/api/presets/test_apply_preset/apply")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "applied"
        assert "config" in data

    def test_apply_nonexistent_preset(self):
        client = _make_client()
        resp = client.post("/api/presets/nonexistent_preset/apply")
        assert resp.status_code == 404

    def test_save_preset_empty_name(self):
        client = _make_client()
        resp = client.post("/api/presets", json={"name": "", "description": ""})
        assert resp.status_code == 400

    def test_save_preset_reserved_name(self):
        client = _make_client()
        resp = client.post("/api/presets", json={"name": "_internal", "description": ""})
        assert resp.status_code == 400

    def test_delete_builtin_preset(self):
        client = _make_client()
        resp = client.delete("/api/presets/low_latency")
        assert resp.status_code == 400

    def test_delete_nonexistent_preset(self):
        client = _make_client()
        resp = client.delete("/api/presets/nonexistent")
        assert resp.status_code == 404


class TestModuleEndpoints:
    """Module management endpoint tests."""

    def test_list_modules_empty(self):
        client = _make_client()
        resp = client.get("/api/modules")
        assert resp.status_code == 200
        assert resp.json()["modules"] == []

    def test_module_debug_not_found(self):
        client = _make_client()
        resp = client.get("/api/modules/transcriber/debug")
        assert resp.status_code == 404

    def test_module_toggle_not_found(self):
        client = _make_client()
        resp = client.put("/api/modules/transcriber/toggle", json={"enabled": False})
        assert resp.status_code == 404

    def test_module_toggle_invalid_name(self):
        client = _make_client()
        resp = client.put("/api/modules/--invalid--/toggle", json={"enabled": False})
        assert resp.status_code == 400


class TestInfoEndpoints:
    """Information endpoints."""

    def test_available_types(self):
        client = _make_client()
        resp = client.get("/api/available")
        assert resp.status_code == 200
        data = resp.json()
        assert "inputs" in data
        assert "outputs" in data

    def test_network_info(self):
        client = _make_client()
        resp = client.get("/api/network/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "local_ip" in data
        assert "srt_url_listener" in data or "srt_url" in data
        assert "server_url" in data or "player_url" in data

    def test_srt_info_legacy(self):
        client = _make_client()
        resp = client.get("/api/srt-info")
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data or "srt_url" in data

    def test_status_format(self):
        client = _make_client()
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "state" in data
        assert "modules" in data
        assert "network" in data
        assert "sync" in data


class TestErrorPaths:
    """Error handling for various endpoints."""

    def test_outputs_no_sink(self):
        client = _make_client()
        resp = client.get("/api/outputs")
        assert resp.status_code == 500

    def test_recording_list_empty(self, tmp_path):
        # F109: usa tmp_path para no contaminar el output/ real. Antes
        # dependía de que output/recordings/ estuviera vacío, pero debris
        # de tests anteriores (test_recording.mp4) lo dejaba no vacío.
        client = _make_client(output_dir=str(tmp_path))
        resp = client.get("/api/recordings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 0
        assert data["recordings"] == []

    def test_input_play_no_source(self):
        client = _make_client()
        resp = client.post("/api/input/control/play")
        assert resp.status_code == 400

    def test_input_pause_no_source(self):
        client = _make_client()
        resp = client.post("/api/input/control/pause")
        assert resp.status_code == 400

    def test_input_seek_no_source(self):
        client = _make_client()
        resp = client.post("/api/input/control/seek", json={"position": 10.0})
        assert resp.status_code == 400

    def test_input_info_no_source(self):
        client = _make_client()
        resp = client.get("/api/input-info")
        assert resp.status_code == 404

    def test_output_info_no_sink(self):
        client = _make_client()
        resp = client.get("/api/output-info")
        assert resp.status_code in (404, 500)
