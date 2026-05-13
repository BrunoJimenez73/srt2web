"""
Tests for Recording Manager API endpoints.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _create_mock_recording(base_dir: Path, name: str, size: int = 1024) -> Path:
    """Create a mock recording file inside the recordings subdirectory."""
    rec_dir = base_dir / "recordings"
    rec_dir.mkdir(parents=True, exist_ok=True)
    file_path = rec_dir / name
    with open(file_path, "wb") as f:
        f.write(b"x" * size)
    return file_path


@pytest.fixture
def output_dir() -> Path:
    """Create a temporary output directory (parent of recordings/)."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def mock_app(output_dir: Path):
    """Create a mock FastAPI app with recordings routes."""
    from fastapi import FastAPI
    from server.routes.recordings import router

    app = FastAPI()
    app.include_router(router, prefix="/api")

    ctx = {"output_dir": str(output_dir)}
    app.state.ctx = ctx
    return app


@pytest.fixture
def client(mock_app):
    """Create test client."""
    return TestClient(mock_app)


class TestRecordingList:
    def test_empty_list(self, client, output_dir: Path) -> None:
        """List recordings when none exist."""
        response = client.get("/api/recordings")
        assert response.status_code == 200
        data = response.json()
        assert data["recordings"] == []
        assert data["total_count"] == 0

    def test_list_with_files(self, client, output_dir: Path) -> None:
        """List recordings with existing files."""
        _create_mock_recording(output_dir, "test1.mp4", 2048)
        _create_mock_recording(output_dir, "test2.mkv", 4096)

        response = client.get("/api/recordings")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        names = [r["name"] for r in data["recordings"]]
        assert "test1.mp4" in names
        assert "test2.mkv" in names

    def test_list_ignores_non_video(self, client, output_dir: Path) -> None:
        """Non-video files should not appear in recordings list."""
        _create_mock_recording(output_dir, "test.txt", 100)
        _create_mock_recording(output_dir, "test.mp4", 2048)

        response = client.get("/api/recordings")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["recordings"][0]["name"] == "test.mp4"


class TestRecordingDownload:
    def test_download_exists(self, client, output_dir: Path) -> None:
        """Download an existing recording."""
        _create_mock_recording(output_dir, "video.mp4", 2048)

        response = client.get("/api/recordings/video.mp4/download")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"

    def test_download_not_found(self, client) -> None:
        """Download non-existent recording returns 404."""
        response = client.get("/api/recordings/nonexistent.mp4/download")
        assert response.status_code == 404


class TestRecordingDelete:
    def test_delete_exists(self, client, output_dir: Path) -> None:
        """Delete an existing recording."""
        _create_mock_recording(output_dir, "delete_me.mp4", 1024)

        response = client.delete("/api/recordings/delete_me.mp4")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        assert not (output_dir / "recordings" / "delete_me.mp4").exists()

    def test_delete_not_found(self, client) -> None:
        """Delete non-existent recording returns 404."""
        response = client.delete("/api/recordings/nonexistent.mp4")
        assert response.status_code == 404


class TestSizeFormatting:
    def test_format_bytes(self) -> None:
        from server.routes.recordings import _format_size

        assert _format_size(500) == "500 B"
        assert _format_size(2048) == "2.0 KB"
        assert _format_size(1048576) == "1.0 MB"
        assert _format_size(1073741824) == "1.00 GB"
