"""
Security utilities for SRT2Web.

Provides path sanitization, input validation, and other security helpers.
"""

import re
import unicodedata
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
            except ValueError as exc:
                raise PathTraversalError(f"Path escapes base directory: {user_path}") from exc
            return str(resolved)
        except Exception as e:
            raise PathTraversalError(f"Invalid path: {user_path}") from e

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
        result = base_path / Path(*clean_parts) if clean_parts else base_path

        # Double-check it's within base_dir
        try:
            result.resolve().relative_to(base_path)
        except ValueError as exc:
            raise PathTraversalError(f"Path escapes base directory: {user_path}") from exc

        return str(result.resolve())

    except PathTraversalError:
        raise
    except Exception as e:
        raise PathTraversalError(f"Invalid path: {user_path}") from e


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


def cleanup_temporary_files(output_dir: str, patterns: list[str] | None = None) -> None:
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


# ── Input sanitization for user-supplied strings (F126) ──

_HTML_TAG_RE = re.compile(r"<[^>]*>", re.UNICODE)
_CONTROL_CHARS_RE = re.compile(
    "["
    "\x00-\x08"  # Null, etc.
    "\x0b\x0c"  # VT, FF
    "\x0e-\x1f"  # More controls
    "\x7f"  # DEL
    "]",
    re.UNICODE,
)


def sanitize_string(
    value: str,
    *,
    max_length: int = 1024,
    strip_html: bool = True,
    strip_control: bool = True,
    normalize_unicode: bool = True,
) -> str:
    """Sanitize a user-supplied string for safe storage/display.

    Args:
        value: Input string to sanitize.
        max_length: Maximum allowed length (truncated). Default 1024.
        strip_html: Remove HTML/XML tags. Default True.
        strip_control: Remove ASCII control characters (except \\n, \\r, \\t). Default True.
        normalize_unicode: NFC-normalize unicode. Default True.

    Returns:
        Sanitized string.
    """
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")

    if normalize_unicode:
        value = unicodedata.normalize("NFC", value)

    if strip_html:
        value = _HTML_TAG_RE.sub("", value)

    if strip_control:
        value = _CONTROL_CHARS_RE.sub("", value)
        # Remove null bytes explicitly
        value = value.replace("\x00", "")

    if max_length and len(value) > max_length:
        value = value[:max_length]

    return value


def sanitize_username(
    value: str,
    *,
    max_length: int = 64,
) -> str:
    """Sanitize a username with stricter rules.

    - Must be at least 1 character after sanitization.
    - Only alphanumeric, underscore, hyphen, dot allowed.
    - No whitespace, no control chars, no HTML.
    - Lowercased.
    - Truncated to max_length.

    Raises ValueError if the result is empty.
    """
    value = sanitize_string(value, max_length=max_length)
    # Remove chars that are not alphanumeric, underscore, hyphen, dot
    value = re.sub(r"[^a-zA-Z0-9_.\-]", "", value)
    # No leading/trailing dots or hyphens
    value = value.strip(".-")
    # Lowercase
    value = value.lower()
    if not value:
        raise ValueError("Username is empty after sanitization")
    return value[:max_length]


def sanitize_display_name(
    value: str,
    *,
    max_length: int = 128,
) -> str:
    """Sanitize a display name / comment field.

    Allows broader characters than username but strips HTML
    and control chars. Truncated to max_length.
    """
    return sanitize_string(value, max_length=max_length)
