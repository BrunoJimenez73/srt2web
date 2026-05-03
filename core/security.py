"""
Security utilities for SRT2Web.

Provides path sanitization, input validation, and other security helpers.
"""

import re
from pathlib import Path


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
        # Clean path components (remove .. and . components) using Path
        clean_parts: list[str] = []
        for part in path.parts:
            if part == "..":
                if clean_parts:
                    clean_parts.pop()
                # If no parts to pop, this would escape - reject
                else:
                    raise PathTraversalError(f"Path traversal attempt detected: {user_path}")
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
    filename = Path(filename).name

    # Remove or replace dangerous characters
    # Keep alphanumeric, underscore, hyphen, dot
    filename = re.sub(r"[^\w\-.]", "_", filename)

    # Limit length
    if len(filename) > 255:
        name, ext = Path(filename).stem, Path(filename).suffix
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


def cleanup_temporary_files(output_dir: str, patterns: list = None) -> None:
    """
    Clean up temporary files from output directory.

    Args:
        output_dir: Directory to clean
        patterns: List of glob patterns to match files for deletion
    """
    if patterns is None:
        patterns = [
            "output/chunks/*",
            "output/temp_audio/*",
            "output/temp_mix/*",
            "output/temp_tts/*",
            "output/hls/seg_*.ts",
            "output/hls/chunk_*.srt",
        ]

    import glob

    for pattern in patterns:
        full_pattern = str(Path(output_dir) / pattern)
        for file_path in glob.glob(full_pattern):
            try:
                p = Path(file_path)
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    import shutil

                    shutil.rmtree(file_path)
            except Exception as e:
                import logging

                logger = logging.getLogger("srt2web.cleanup")
                logger.warning(f"Could not clean {file_path}: {e}")


def validate_directory_access(directory: str, create_if_missing: bool = True) -> bool:
    """
    Validate that a directory is accessible and can be written to.

    Args:
        directory: Path to directory to validate
        create_if_missing: Whether to create the directory if it doesn't exist

    Returns:
        True if directory is accessible, False otherwise
    """
    try:
        # Convert to Path object for easier manipulation
        path = Path(directory)

        # Create directory if it doesn't exist
        if not path.exists():
            if create_if_missing:
                path.mkdir(parents=True, exist_ok=True)
            else:
                return False

        # Check if it's actually a directory
        if not path.is_dir():
            return False

        # Check if we can write to it
        test_file = path / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError):
            return False

        return True

    except (PermissionError, OSError) as e:
        import logging

        logger = logging.getLogger("srt2web.security")
        logger.error(f"Directory validation failed for {directory}: {e}")
        return False


def sanitize_module_name(name: str) -> str:
    """
    Sanitize module name to prevent injection attacks.

    Args:
        name: Module name to sanitize

    Returns:
        Sanitized module name

    Raises:
        ValueError: If module name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValueError("Module name is required and must be a string")

    # Only allow alphanumeric characters, underscores, and hyphens
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValueError("Invalid module name format")

    # List of valid modules
    valid_modules = [
        "audio_extractor",
        "transcriber",
        "translator",
        "subtitle_generator",
        "tts_engine",
        "audio_mixer",
        "video_muxer",
    ]

    if name not in valid_modules:
        raise ValueError(f"Unknown module: {name}")

    return name
