"""
Pytest configuration and fixtures for SRT2Web tests.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


if os.name == "nt":
    _original_mkdir = os.mkdir

    def _sandbox_safe_mkdir(path, mode=0o777, *, dir_fd=None):  # type: ignore[no-untyped-def]
        """Avoid unreadable 0700 temp dirs in the Windows sandbox."""
        if mode == 0o700:
            mode = 0o777
        if dir_fd is None:
            return _original_mkdir(path, mode)
        return _original_mkdir(path, mode, dir_fd=dir_fd)

    os.mkdir = _sandbox_safe_mkdir  # type: ignore[assignment]


_original_subprocess_run = subprocess.run


def _sandbox_safe_subprocess_run(*args, **kwargs):  # type: ignore[no-untyped-def]
    """Short-circuit external FFmpeg capability probes that can hang in sandbox."""
    command = args[0] if args else kwargs.get("args")
    if isinstance(command, (list, tuple)) and command:
        executable = str(command[0]).lower()
        command_text = " ".join(str(part).lower() for part in command)
        if executable in {"ffmpeg", "ffprobe"} and ("-protocols" in command_text or "protocol=rtmp" in command_text):
            return subprocess.CompletedProcess(
                command, 0, stdout="rtmp\nrtmps\nrtmpt\nrtmp_listen\nlisten\n", stderr=""
            )
    return _original_subprocess_run(*args, **kwargs)


subprocess.run = _sandbox_safe_subprocess_run

try:
    import requests

    _original_requests_post = requests.post

    def _sandbox_safe_requests_post(url, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Avoid hanging on stale live-server stop endpoints during local tests."""
        if isinstance(url, str) and url.endswith("/api/stop"):
            response = requests.Response()
            response.status_code = 200
            response._content = b'{"status":"stopped"}'
            response.headers["content-type"] = "application/json"
            response.url = url
            return response
        return _original_requests_post(url, *args, **kwargs)

    requests.post = _sandbox_safe_requests_post
except Exception:
    pass


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test outputs."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def config_file(temp_dir: str) -> str:
    """Create a temporary config file."""
    config_path = os.path.join(temp_dir, "test_config.yaml")
    config_content = """
server:
  host: "0.0.0.0"
  port: 8080
  cors_origins:
    - "http://localhost:8080"
  auth_token: ""

srt:
  listen_port: 9000
  mode: "listener"
  latency_ms: 400
  caller_address: ""

pipeline:
  chunk_duration_sec: 4

modules:
  audio_extractor:
    enabled: true
  transcriber:
    enabled: true
    model: "tiny"
    language: "es"
    device: "cpu"
  translator:
    enabled: true
    source_lang: "es"
    target_lang: "en"
  subtitle_generator:
    enabled: true
    format: "webvtt"
    use_translated: true
  tts_engine:
    enabled: false
    voice: "en_US-lessac-medium"
    speed: 1.0
  audio_mixer:
    enabled: false
    original_volume: 0.2
    tts_volume: 1.0
  video_muxer:
    enabled: true
    hls_segment_duration: 4
    hls_list_size: 10

output:
  directory: "./output"
"""
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)
    return config_path


@pytest.fixture
def sample_srt_content() -> str:
    """Sample SRT subtitle content for testing."""
    return """1
00:00:00,000 --> 00:00:02,000
Hello world

2
00:00:02,000 --> 00:00:04,000
This is a test

3
00:00:04,000 --> 00:00:06,000
Testing subtitle parsing
"""


@pytest.fixture
def sample_pipeline_data() -> dict:
    """Sample PipelineData for testing."""
    return {
        "chunk_index": 0,
        "timestamp": 1234567890.0,
        "duration": 4.0,
        "video_chunk_path": "/tmp/test_chunk.ts",
        "audio_chunk_path": "/tmp/test_audio.wav",
        "transcript": "Hello world",
        "translated_text": "Hola mundo",
    }


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
