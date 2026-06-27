"""
Recording management routes for SRT2Web API.

Provides endpoints to list, download, and delete recordings.
"""

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from core.security import sanitize_filename

logger = logging.getLogger("srt2web.api.recordings")

router = APIRouter(tags=["recordings"])

from server.ctx import get_ctx as _ctx  # noqa: E402


def _get_recordings_dir(request: Request) -> Path:
    """Get the recordings output directory."""
    ctx = _ctx(request)
    output_dir = ctx.get("output_dir", "./output")
    recordings_dir = Path(output_dir) / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    return recordings_dir


def _resolve_safe_path(recordings_dir: Path, name: str) -> Path:
    """Resolve a safe file path within recordings_dir, preventing path traversal."""
    safe_name = sanitize_filename(name)
    file_path = (recordings_dir / safe_name).resolve()
    try:
        file_path.relative_to(recordings_dir.resolve())
    except ValueError:
        raise HTTPException(400, f"Invalid recording name: '{name}'") from None
    return file_path


def _scan_recordings(recordings_dir: Path) -> list[dict[str, Any]]:
    """Scan for recording files and return metadata."""
    results: list[dict[str, Any]] = []
    if not recordings_dir.exists():
        return results

    video_extensions = {".mp4", ".mkv", ".webm", ".ts", ".avi", ".mov"}

    for f in sorted(recordings_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_file() and f.suffix.lower() in video_extensions:
            stat = f.stat()
            results.append(
                {
                    "name": f.name,
                    "size_bytes": stat.st_size,
                    "size_formatted": _format_size(stat.st_size),
                    "modified": stat.st_mtime,
                    "format": f.suffix.lower().lstrip("."),
                }
            )
    return results


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _get_total_size(recordings: list[dict[str, Any]]) -> str:
    """Calculate total size of all recordings."""
    total = sum(r["size_bytes"] for r in recordings)
    return _format_size(total)


@router.get("/recordings")
async def list_recordings(request: Request) -> dict[str, Any]:
    """List all recordings with metadata."""
    recordings_dir = _get_recordings_dir(request)
    recordings = _scan_recordings(recordings_dir)
    return {
        "recordings": recordings,
        "total_count": len(recordings),
        "total_size": _get_total_size(recordings),
        "directory": str(recordings_dir),
    }


@router.get("/recordings/{name}/download")
async def download_recording(request: Request, name: str) -> FileResponse:
    """Download a recording file."""
    recordings_dir = _get_recordings_dir(request)
    file_path = _resolve_safe_path(recordings_dir, name)

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, f"Recording '{file_path.name}' not found")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@router.delete("/recordings/{name}")
async def delete_recording(request: Request, name: str) -> dict[str, Any]:
    """Delete a recording file."""
    recordings_dir = _get_recordings_dir(request)
    file_path = _resolve_safe_path(recordings_dir, name)

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, f"Recording '{file_path.name}' not found")

    try:
        os.remove(str(file_path))
        logger.info(f"Recording deleted: {file_path.name}")
        return {"status": "deleted", "name": file_path.name}
    except OSError as e:
        logger.error("Failed to delete recording %s: %s", file_path.name, e)
        # F161: Return generic message to avoid leaking internal details
        raise HTTPException(500, "Failed to delete recording") from e
