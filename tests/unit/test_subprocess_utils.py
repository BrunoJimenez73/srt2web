"""
Tests for core.subprocess_utils — cross-platform subprocess helpers.

F165: Covers get_creation_flags and filter_command.
"""

import subprocess
import sys

import pytest

from core.subprocess_utils import filter_command, get_creation_flags


@pytest.mark.unit
class TestGetCreationFlags:
    def test_returns_int(self):
        result = get_creation_flags()
        assert isinstance(result, int)

    def test_windows_returns_create_no_window(self):
        if sys.platform == "win32":
            assert get_creation_flags() == subprocess.CREATE_NO_WINDOW
        else:
            assert get_creation_flags() == 0

    def test_non_windows_returns_zero(self):
        if sys.platform != "win32":
            assert get_creation_flags() == 0


@pytest.mark.unit
class TestFilterCommand:
    def test_removes_none(self):
        result = filter_command(["ffmpeg", None, "-i", None, "test.ts"])
        assert result == ["ffmpeg", "-i", "test.ts"]

    def test_empty_list(self):
        assert filter_command([]) == []

    def test_no_nones(self):
        assert filter_command(["a", "b", "c"]) == ["a", "b", "c"]

    def test_all_nones(self):
        assert filter_command([None, None]) == []
