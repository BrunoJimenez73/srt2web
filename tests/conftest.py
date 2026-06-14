"""
Pytest configuration and fixtures for SRT2Web tests.
"""

import os
import shutil
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# F118: Signal to AuthMiddleware that we're in test mode — skip auth checks entirely
os.environ.setdefault("SRT2WEB_TESTING", "1")


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test outputs."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_srt_content() -> str:
    """Sample SRT subtitle content for testing."""
    return """1
00:00:01,000 --> 00:00:04,000
Hello world

2
00:00:05,000 --> 00:00:08,000
This is a test

3
00:00:09,000 --> 00:00:12,000
Subtitle example
"""


@pytest.fixture
def small_audio_chunk() -> dict:
    """Small audio chunk for testing."""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(b"\x00\x00\x00\x00")  # Minimal WAV header
        path = f.name
    return {
        "path": path,
        "duration": 2.0,
        "sample_rate": 16000,
        "channels": 1,
    }


@pytest.fixture
def mock_whisper_model():
    """Mock Whisper model for testing."""
    model = MagicMock()
    model.transcribe.return_value = {
        "segments": [
            {"start": 0.0, "end": 2.0, "text": "Hello"},
            {"start": 2.0, "end": 4.0, "text": "world"},
        ]
    }
    return model


@pytest.fixture
def config_factory():
    """Factory for creating test configurations."""
    from core.config_manager import ConfigManager

    cm = ConfigManager()

    def _factory(**overrides):
        config = cm.get()
        for key, value in overrides.items():
            if "." in key:
                section, field = key.split(".", 1)
                setattr(getattr(config, section), field, value)
            else:
                setattr(config, key, value)
        return config

    return _factory


@pytest.fixture
def chunk_factory():
    """Factory for creating PipelineData chunks."""
    from core.pipeline.base import PipelineData

    def _factory(**overrides):
        defaults = {
            "chunk_index": 0,
            "timestamp": 1234567890.0,
            "duration": 4.0,
            "video_chunk_path": "/tmp/test_chunk.ts",
            "audio_chunk_path": "/tmp/test_audio.wav",
            "transcript": "Hello world",
            "translated_text": "Hola mundo",
        }
        defaults.update(overrides)
        return PipelineData(**defaults)

    return _factory


@pytest.fixture
def mock_app_context():  # type: ignore
    """Create a mock app context for testing."""
    from core.config_manager import ConfigManager
    from core.pipeline import Pipeline

    config = ConfigManager()
    pipeline = Pipeline()

    return {
        "config": config,
        "pipeline": pipeline,
        "srt_ingest": None,
        "log_broadcast": lambda level, msg: None,
    }


@pytest.fixture
def client(mock_app_context):  # type: ignore
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient

    from server.app import create_app

    app = create_app(mock_app_context)
    return TestClient(app)
