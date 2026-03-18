"""
Security module tests.
"""

import os
import pytest
from pathlib import Path
from core.security import (
    PathTraversalError,
    sanitize_path,
    sanitize_filename,
    validate_port,
    validate_latency,
    escape_ffmpeg_path,
)


class TestPathSanitization:
    """Test path sanitization functions."""

    def test_sanitize_path_basic(self):
        """Test basic path sanitization."""
        # Relative path should work
        result = sanitize_path("subdir/file.txt", "base")
        # The function returns an absolute path, so we need to check the relative part
        # Normalize both paths and check that the result ends with our expected relative path
        assert os.path.normpath(result).endswith(
            os.path.normpath("base/subdir/file.txt")
        )

    def test_sanitize_path_traversal_attempt(self):
        """Test that path traversal attempts are blocked."""
        with pytest.raises(PathTraversalError):
            sanitize_path("../../../etc/passwd", "/base")

        with pytest.raises(PathTraversalError):
            sanitize_path("subdir/../../../etc/passwd", "/base")

        with pytest.raises(PathTraversalError):
            sanitize_path("..", "/base")

    def test_sanitize_path_absolute_not_allowed(self):
        """Test that absolute paths are rejected when not allowed."""
        with pytest.raises(PathTraversalError):
            sanitize_path("/etc/passwd", "/base")

    def test_sanitize_path_absolute_allowed_within_base(self):
        """Test that absolute paths are allowed when within base_dir."""
        # Create a temporary directory structure for testing
        base_temp = Path("./temp_test_base").resolve()
        base_temp.mkdir(exist_ok=True)
        subdir = base_temp / "subdir"
        subdir.mkdir(exist_ok=True)
        test_file = subdir / "test.txt"
        test_file.touch()

        try:
            # This should work since the absolute path is within base_dir
            result = sanitize_path(str(test_file), str(base_temp), allow_absolute=True)
            # The function returns an absolute path, check that it equals the resolved test file path
            assert os.path.normpath(result) == os.path.normpath(str(test_file))
        finally:
            # Cleanup
            import shutil

            shutil.rmtree(base_temp, ignore_errors=True)

    def test_sanitize_path_absolute_allowed_outside_base(self):
        """Test that absolute paths outside base_dir are rejected even when allowed."""
        with pytest.raises(PathTraversalError):
            sanitize_path("/etc/passwd", "/base", allow_absolute=True)

    def test_sanitize_path_empty(self):
        """Test that empty paths raise an error."""
        with pytest.raises(PathTraversalError):
            sanitize_path("", "/base")

    def test_sanitize_path_null_bytes(self):
        """Test that null bytes are removed."""
        result = sanitize_path("subdir\0file.txt", "base")
        # The function returns an absolute path, check that it ends with our expected path
        assert os.path.normpath(result).endswith(
            os.path.normpath("base/subdirfile.txt")
        )

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        result = sanitize_filename("normal_file.txt")
        assert result == "normal_file.txt"

    def test_sanitize_filename_dangerous_chars(self):
        """Test that dangerous characters are replaced."""
        # Test with a simple filename that doesn't contain path separators
        # to avoid platform-specific basename behavior
        result = sanitize_filename('file<>:|"*.txt')
        # The regex [^\w\-.] keeps alphanumeric, underscore, hyphen, dot
        # So < > : | " * become underscores (6 characters)
        assert result == "file______.txt"

    def test_sanitize_filename_empty(self):
        """Test that empty filenames raise an error."""
        with pytest.raises(ValueError):
            sanitize_filename("")

    def test_sanitize_filename_null_bytes(self):
        """Test that null bytes are removed from filenames."""
        result = sanitize_filename("file\0name.txt")
        assert result == "filename.txt"

    def test_sanitize_filename_length_limit(self):
        """Test that long filenames are truncated."""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".txt")


class TestValidation:
    """Test validation functions."""

    def test_validate_port_valid(self):
        """Test valid port numbers."""
        assert validate_port(1) == 1
        assert validate_port(80) == 80
        assert validate_port(65535) == 65535

    def test_validate_port_invalid(self):
        """Test invalid port numbers."""
        with pytest.raises(ValueError):
            validate_port(0)
        with pytest.raises(ValueError):
            validate_port(65536)
        with pytest.raises(ValueError):
            validate_port(-1)
        # Test wrong type - this should raise ValueError because isinstance(port, int) fails
        with pytest.raises(ValueError):
            # Pass a string instead of int to trigger the type check failure
            validate_port("80")  # type: ignore

    def test_validate_latency_valid(self):
        """Test valid latency values."""
        assert validate_latency(0) == 0
        assert validate_latency(100) == 100
        assert validate_latency(8000) == 8000

    def test_validate_latency_invalid(self):
        """Test invalid latency values."""
        with pytest.raises(ValueError):
            validate_latency(-1)
        with pytest.raises(ValueError):
            validate_latency(8001)
        # Test wrong type - this should raise ValueError because isinstance(latency, int) fails
        with pytest.raises(ValueError):
            # Pass a string instead of int to trigger the type check failure
            validate_latency("100")  # type: ignore


class TestFFmpegPathEscaping:
    """Test FFmpeg path escaping."""

    def test_escape_ffmpeg_path_basic(self):
        """Test basic path escaping."""
        result = escape_ffmpeg_path("normal_path.txt")
        assert result == "normal_path.txt"

    def test_escape_ffmpeg_path_backslashes(self):
        """Test that backslashes are escaped."""
        result = escape_ffmpeg_path("path\\to\\file.txt")
        assert result == "path\\\\to\\\\file.txt"

    def test_escape_ffmpeg_path_colons(self):
        """Test that colons are escaped."""
        result = escape_ffmpeg_path("path:to:file.txt")
        assert result == "path\\:to\\:file.txt"

    def test_escape_ffmpeg_path_single_quotes(self):
        """Test that single quotes are escaped."""
        result = escape_ffmpeg_path("path'to'file.txt")
        assert result == "path'\\''to'\\''file.txt"

    def test_escape_ffmpeg_path_complex(self):
        """Test complex path with multiple escape characters."""
        # Test with a simple string containing characters that need escaping
        test_input = "hello'world:test.txt"
        result = escape_ffmpeg_path(test_input)
        # Step by step what should happen:
        # 1. Backslashes: none in input, so unchanged
        # 2. Colons: : becomes \:
        # 3. Single quotes: ' becomes '\''
        # Expected: hello'\\''world\:test.txt
        expected = "hello'\\''world\\:test.txt"
        assert result == expected
