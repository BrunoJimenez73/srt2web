"""
Security utilities for SRT2Web.

Provides path sanitization, input validation, and other security helpers.
"""

import os
import re
from pathlib import Path
from typing import Optional


class PathTraversalError(Exception):
    """Raised when a path traversal attempt is detected."""

    pass


def sanitize_path(user_path: str, base_dir: str, allow_absolute: bool = False) -> str:
    """
    Sanitize a user-provided path to prevent path traversal attacks.

    Args:
        user_path: The path provided by user/input
        base_dir: The base directory to restrict access to
        allow_absolute: Whether to allow absolute paths

    Returns:
        Sanitized path relative to base_dir

    Raises:
        PathTraversalError: If the path attempts to escape base_dir
    """
    if not user_path:
        raise PathTraversalError("Empty path provided")

    # Remove null bytes
    user_path = user_path.replace("\0", "")

    # Convert to Path object
    path = Path(user_path)

    # Reject absolute paths unless explicitly allowed
    if path.is_absolute() and not allow_absolute:
        raise PathTraversalError(f"Absolute paths not allowed: {user_path}")

    # If absolute and allowed, resolve and check it's within base_dir
    if path.is_absolute() and allow_absolute:
        try:
            resolved = path.resolve()
            base_resolved = Path(base_dir).resolve()
            # Ensure resolved path is within base_dir
            try:
                resolved.relative_to(base_resolved)
            except ValueError:
                raise PathTraversalError(f"Path escapes base directory: {user_path}")
            return str(resolved)
        except Exception as e:
            raise PathTraversalError(f"Invalid path: {user_path}")

    # For relative paths, resolve them relative to base_dir
    try:
        base_path = Path(base_dir).resolve()
        # Clean the path (remove .. and . components)
        # Use os.path.normpath but be careful
        clean_parts = []
        for part in path.parts:
            if part == "..":
                if clean_parts:
                    clean_parts.pop()
                # If no parts to pop, this would escape - reject
                else:
                    raise PathTraversalError(
                        f"Path traversal attempt detected: {user_path}"
                    )
            elif part != ".":
                clean_parts.append(part)

        # Reconstruct path
        if clean_parts:
            result = base_path / Path(*clean_parts)
        else:
            result = base_path

        # Double-check it's within base_dir
        try:
            result.resolve().relative_to(base_path)
        except ValueError:
            raise PathTraversalError(f"Path escapes base directory: {user_path}")

        return str(result.resolve())

    except PathTraversalError:
        raise
    except Exception as e:
        raise PathTraversalError(f"Invalid path: {user_path}")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent injection attacks.

    Args:
        filename: The filename provided by user

    Returns:
        Sanitized filename
    """
    if not filename:
        raise ValueError("Empty filename")

    # Remove null bytes
    filename = filename.replace("\0", "")

    # Get just the basename (no directory components)
    filename = os.path.basename(filename)

    # Remove or replace dangerous characters
    # Keep alphanumeric, underscore, hyphen, dot
    filename = re.sub(r"[^\w\-.]", "_", filename)

    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[: 255 - len(ext)] + ext

    return filename


def validate_port(port: int) -> int:
    """Validate port number is in valid range."""
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ValueError(f"Invalid port: {port}")
    return port


def validate_latency(latency: int) -> int:
    """Validate latency value in milliseconds."""
    if not isinstance(latency, int) or latency < 0:
        raise ValueError(f"Invalid latency: {latency}")
    if latency > 8000:  # Max 8 seconds
        raise ValueError(f"Latency too high: {latency}ms (max 8000ms)")
    return latency


def escape_ffmpeg_path(path: str) -> str:
    """
    Escape a file path for use in FFmpeg commands.

    This helps prevent command injection through file paths.
    """
    # Escape backslashes first (Windows)
    escaped = path.replace("\\", "\\\\")
    # Escape colons (path separators on Windows, but also used in FFmpeg filter syntax)
    escaped = escaped.replace(":", "\\:")
    # Escape single quotes
    escaped = escaped.replace("'", "'\\''")
    return escaped
