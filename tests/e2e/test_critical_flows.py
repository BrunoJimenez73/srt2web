"""
End-to-end tests for critical user flows.
Tests pipeline lifecycle, config persistence, preset apply,
module toggle, and output management with a full app context.
"""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from core.config_manager import ConfigManager
from core.module_base import ModuleState
from core.pipeline import Pipeline
from server.app import create_app


class DummyModule:
    """Dummy module for testing pipeline flows."""

    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.state = ModuleState.IDLE
        self._processed_chunks = 0
        self._last_process_time_ms = 0.0
        self._error_message: str | None = None

    def configure(self, config: dict) -> None:
        self.enabled = config.get("enabled", True)

    def get_status(self):
        from core.module_base import ModuleStatus

        return ModuleStatus(
            name=self.name,
            state=self.state,
            enabled=self.enabled,
            error_message=self._error_message,
            processed_chunks=self._processed_chunks,
            last_process_time_ms=self._last_process_time_ms,
        )

    def start(self) -> None:
        self.state = ModuleState.RUNNING

    def stop(self) -> None:
        self.state = ModuleState.IDLE


class TestPipelineLifecycle:
    """Pipeline start/stop/restart flow."""

    MODULES = ("audio_extractor", "transcriber", "translator", "subtitle_generator")

    @pytest.fixture
    def ctx(self):
        config = ConfigManager()
        pipeline = Pipeline()
        for mod_name in self.MODULES:
            pipeline.register_module(DummyModule(mod_name))
        srt_ingest = Mock()
        srt_ingest.is_receiving.return_value = False
        srt_ingest.get_connection_info.return_value = {
            "url": "srt://127.0.0.1:9000",
            "host": "127.0.0.1",
            "port": 9000,
            "mode": "listener",
            "receiving": False,
        }
        return {
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": srt_ingest,
            "log_broadcast": Mock(),
        }

    @pytest.fixture
    def client(self, ctx):
        app = create_app(ctx)
        return TestClient(app)

    def test_pipeline_start_stop(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        assert resp.json()["state"] == "idle"

        resp = client.post("/api/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "started"

        resp = client.get("/api/status")
        assert resp.status_code == 200
        assert resp.json()["state"] == "running"

        resp = client.post("/api/start")
        assert resp.status_code == 400

        resp = client.post("/api/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"

        resp = client.get("/api/status")
        assert resp.status_code == 200
        assert resp.json()["state"] == "idle"

    def test_pipeline_restart(self, client):
        client.post("/api/start")
        resp = client.post("/api/restart")
        assert resp.status_code == 200
        assert resp.json()["status"] == "restarted"

        resp = client.get("/api/status")
        assert resp.status_code == 200

    def test_pipeline_module_list(self, client):
        resp = client.get("/api/modules")
        assert resp.status_code == 200
        modules = resp.json()["modules"]
        names = [m["name"] for m in modules]
        for expected in self.MODULES:
            assert expected in names

    def test_module_debug(self, client):
        resp = client.get("/api/modules/transcriber/debug")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "transcriber"
        assert "enabled" in data
        assert "state" in data

    def test_module_toggle(self, client):
        resp = client.put("/api/modules/transcriber/toggle", json={"enabled": False})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

        resp = client.get("/api/modules/transcriber/debug")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

        resp = client.put("/api/modules/transcriber/toggle", json={"enabled": True})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True


class TestConfigPersistence:
    """Config save -> verify -> revert flow."""

    @pytest.fixture
    def client(self):
        config = ConfigManager()
        pipeline = Pipeline()
        pipeline.register_module(DummyModule("audio_extractor"))
        pipeline.register_module(DummyModule("transcriber"))
        pipeline.register_module(DummyModule("translator"))
        app = create_app(
            {
                "config": config,
                "pipeline": pipeline,
                "srt_ingest": None,
                "log_broadcast": Mock(),
            }
        )
        return TestClient(app)

    def test_config_read_write_verify(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        original = resp.json()
        original_port = original.get("server", {}).get("port", 9999)

        new_port = 8888 if original_port != 8888 else 7777
        resp = client.put("/api/config", json={"config": {"server": {"port": new_port}}})
        assert resp.status_code == 200

        resp = client.get("/api/config")
        assert resp.json()["server"]["port"] == new_port

        resp = client.put("/api/config", json={"config": {"server": {"port": original_port}}})
        assert resp.status_code == 200

        resp = client.get("/api/config")
        assert resp.json()["server"]["port"] == original_port

    def test_preset_save_and_apply(self, client):
        resp = client.post("/api/presets", json={"name": "e2e_test_preset", "description": "e2e"})
        assert resp.status_code == 200

        resp = client.post("/api/presets/e2e_test_preset/apply")
        assert resp.status_code == 200
        assert resp.json()["status"] == "applied"

        resp = client.delete("/api/presets/e2e_test_preset")
        assert resp.status_code == 200


class TestOutputManagement:
    """Output management flow with a pipeline that has a composite sink."""

    @pytest.fixture
    def ctx(self):
        config = ConfigManager()
        pipeline = Pipeline()
        pipeline.register_module(DummyModule("audio_extractor"))
        pipeline.register_module(DummyModule("transcriber"))

        from modules.outputs.composite_output import CompositeOutput

        composite = CompositeOutput({})
        from core.io_factory import OutputFactory

        srt_out = OutputFactory.create("srt", {"port": 9002})
        srt_out.name = "srt_1"
        composite.add_output("srt_1", srt_out)

        pipeline.set_output_sink(composite)

        srt_ingest = Mock()
        srt_ingest.is_receiving.return_value = False
        srt_ingest.get_connection_info.return_value = {
            "url": "srt://127.0.0.1:9000",
            "host": "127.0.0.1",
            "port": 9000,
            "mode": "listener",
            "receiving": False,
        }
        return {
            "config": config,
            "pipeline": pipeline,
            "srt_ingest": srt_ingest,
            "log_broadcast": Mock(),
        }

    @pytest.fixture
    def client(self, ctx):
        app = create_app(ctx)
        return TestClient(app)

    def test_list_outputs(self, client):
        resp = client.get("/api/outputs")
        assert resp.status_code == 200
        data = resp.json()
        assert "outputs" in data
        assert len(data["outputs"]) >= 1

    def test_add_and_remove_output(self, client):
        resp = client.get("/api/outputs")
        initial_count = len(resp.json()["outputs"])

        resp = client.post(
            "/api/outputs",
            json={
                "type": "srt",
                "name": "test_output_e2e",
                "config": {"port": 9995},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "added"

        resp = client.get("/api/outputs")
        assert len(resp.json()["outputs"]) == initial_count + 1

        resp = client.delete("/api/outputs/test_output_e2e")
        assert resp.status_code == 200
        assert resp.json()["status"] == "removed"

        resp = client.get("/api/outputs")
        assert len(resp.json()["outputs"]) == initial_count

    def test_toggle_output(self, client):
        resp = client.post("/api/outputs/srt_1/toggle")
        assert resp.status_code == 200
        assert "enabled" in resp.json()

        resp = client.post("/api/outputs/srt_1/toggle", json={"enabled": True})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_update_output(self, client):
        resp = client.put("/api/outputs/srt_1", json={"enabled": False})
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

        resp = client.put("/api/outputs/srt_1", json={"enabled": True})
        assert resp.status_code == 200

    def test_delete_last_output_forbidden(self, client):
        resp = client.get("/api/outputs")
        count = len(resp.json()["outputs"])
        if count == 1:
            resp = client.delete("/api/outputs/srt_1")
            assert resp.status_code == 400
            assert "Cannot remove the last output" in resp.text


class TestRecordingFlows:
    """Recording management with actual files."""

    @pytest.fixture
    def client(self, tmp_path):
        config = ConfigManager()
        pipeline = Pipeline()
        app = create_app(
            {
                "config": config,
                "pipeline": pipeline,
                "srt_ingest": None,
                "output_dir": str(tmp_path),
                "log_broadcast": Mock(),
            }
        )
        return TestClient(app)

    def test_recordings_empty(self, client):
        resp = client.get("/api/recordings")
        assert resp.status_code == 200
        assert resp.json()["recordings"] == []

    def test_recording_not_found(self, client):
        resp = client.get("/api/recordings/nonexistent/download")
        assert resp.status_code == 404

        resp = client.delete("/api/recordings/nonexistent")
        assert resp.status_code == 404

    def test_recording_list_with_files(self, client, tmp_path):
        rec_dir = tmp_path / "recordings"
        rec_dir.mkdir(exist_ok=True)
        rec_file = rec_dir / "test_video.mp4"
        rec_file.write_text("fake mp4 content")

        resp = client.get("/api/recordings")
        assert resp.status_code == 200
        recordings = resp.json()["recordings"]
        names = [r["name"] for r in recordings]
        assert "test_video.mp4" in names

    def test_recording_download(self, client, tmp_path):
        rec_dir = tmp_path / "recordings"
        rec_dir.mkdir(exist_ok=True)
        rec_file = rec_dir / "download_test.mp4"
        rec_file.write_text("download content")

        resp = client.get("/api/recordings/download_test.mp4/download")
        assert resp.status_code == 200

    def test_recording_delete(self, client, tmp_path):
        rec_dir = tmp_path / "recordings"
        rec_dir.mkdir(exist_ok=True)
        rec_file = rec_dir / "delete_test.mp4"
        rec_file.write_text("delete content")

        resp = client.delete("/api/recordings/delete_test.mp4")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        assert not rec_file.exists()
