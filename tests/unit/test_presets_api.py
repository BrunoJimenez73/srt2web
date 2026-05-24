"""
Unit tests for Preset API endpoints (F19).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient


@pytest.fixture
def client_with_presets():
    """Create a test client with patched rate limiter and preset methods."""
    from core.pipeline import Pipeline
    from server.security import RateLimiter

    # Patch RateLimiter.is_allowed to always allow
    original_is_allowed = RateLimiter.is_allowed

    def mock_is_allowed(self, key):
        return True, 999

    with patch.object(RateLimiter, "is_allowed", mock_is_allowed):
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "server.auth_token": "",
            "server.port": 9999,
        }.get(key, default)

        config.to_dict.return_value = {
            "server": {"port": 9999, "host": "127.0.0.1"},
            "pipeline": {
                "chunk_duration_sec": 5,
                "mode": "sequential",
                "max_concurrent_chunks": 4,
                "buffer_size": 10,
                "retry_attempts": 3,
                "retry_delay": 1.0,
            },
            "output_dir": {"directory": "./output"},
            "modules": {
                "audio_extractor": {"enabled": True},
                "transcriber": {"enabled": False, "model": "tiny", "language": "en", "device": "auto", "beam_size": 2},
                "translator": {"enabled": True, "source_lang": "fr", "target_lang": "es"},
                "subtitle_generator": {"enabled": True, "format": "srt", "use_translated": True, "chunk_duration": 5},
                "tts_engine": {
                    "enabled": True,
                    "engine": "piper",
                    "device": "auto",
                    "voice": "es_ES-davefx-medium",
                    "speed": 1.2,
                },
                "audio_mixer": {"enabled": True, "original_volume": 0.6, "tts_volume": 1.0, "dubbed_volume": 1.0},
                "video_muxer": {"enabled": True, "engine": "hls"},
            },
        }
        config.list_presets.return_value = []
        config.built_in_presets.return_value = {
            "low_latency": {
                "config": config.to_dict(),
                "description": "Low latency mode",
            },
            "high_quality": {
                "config": config.to_dict(),
                "description": "High quality mode",
            },
        }
        config.save_preset = MagicMock()
        config.load_preset.return_value = config.to_dict()
        config.delete_preset = MagicMock()

        app_context = {
            "config": config,
            "pipeline": Pipeline(),
            "srt_ingest": None,
            "log_broadcast": lambda level, msg: None,
        }

        from server.app import create_app

        app = create_app(app_context)
        client = TestClient(app, raise_server_exceptions=True)
        yield client, config


@pytest.mark.unit
class TestListPresets:
    def test_lists_built_in_presets(self, client_with_presets):
        client, _ = client_with_presets
        response = client.get("/api/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        names = [p["name"] for p in data["presets"]]
        assert "low_latency" in names
        assert "high_quality" in names

    def test_built_in_preset_has_flag(self, client_with_presets):
        client, _ = client_with_presets
        response = client.get("/api/presets")
        assert response.status_code == 200
        built_ins = [p for p in response.json()["presets"] if p.get("built_in")]
        assert len(built_ins) > 0
        assert built_ins[0]["built_in"] is True

    def test_saved_presets_included(self, client_with_presets):
        client, config = client_with_presets
        config.list_presets.return_value = [{"name": "my_preset", "description": "Test", "config_keys": ["pipeline"]}]
        response = client.get("/api/presets")
        assert response.status_code == 200
        names = [p["name"] for p in response.json()["presets"]]
        assert "my_preset" in names
        assert len(names) == 3


@pytest.mark.unit
class TestSavePreset:
    def test_saves_preset_with_valid_name(self, client_with_presets):
        client, config = client_with_presets
        response = client.post("/api/presets", json={"name": "my_preset", "description": "Test"})
        assert response.status_code == 200
        assert response.json()["status"] == "saved"
        assert response.json()["name"] == "my_preset"
        config.save_preset.assert_called_once_with("my_preset", "Test")

    def test_rejects_empty_name(self, client_with_presets):
        client, _ = client_with_presets
        response = client.post("/api/presets", json={"name": ""})
        assert response.status_code in (400, 422)

    def test_rejects_reserved_name(self, client_with_presets):
        client, _ = client_with_presets
        response = client.post("/api/presets", json={"name": "_internal"})
        assert response.status_code == 400


@pytest.mark.unit
class TestApplyPreset:
    def test_applies_built_in_preset(self, client_with_presets):
        client, config = client_with_presets
        response = client.post("/api/presets/low_latency/apply")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "applied"
        assert data["name"] == "low_latency"

    def test_applies_saved_preset(self, client_with_presets):
        client, _ = client_with_presets
        response = client.post("/api/presets/my_preset/apply")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "applied"
        assert data["name"] == "my_preset"

    def test_rejects_not_found_preset(self, client_with_presets):
        client, config = client_with_presets
        config.load_preset.side_effect = KeyError("Preset not found")
        response = client.post("/api/presets/nonexistent/apply")
        assert response.status_code == 404


@pytest.mark.unit
class TestDeletePreset:
    def test_deletes_saved_preset(self, client_with_presets):
        client, config = client_with_presets
        response = client.delete("/api/presets/my_preset")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        config.delete_preset.assert_called_once_with("my_preset")

    def test_rejects_deleting_built_in(self, client_with_presets):
        client, _ = client_with_presets
        response = client.delete("/api/presets/low_latency")
        assert response.status_code == 400

    def test_rejects_deleting_not_found(self, client_with_presets):
        client, config = client_with_presets
        config.delete_preset.side_effect = KeyError("Not found")
        response = client.delete("/api/presets/nonexistent")
        assert response.status_code == 404
