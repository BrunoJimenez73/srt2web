"""
Tests for SRT input chunk processing.
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.module_base import PipelineData


@pytest.fixture
def srt_input():
    """Create SRTInput with mocked heavy dependencies."""
    with patch("modules.inputs.srt_input.SRTInput._ensure_stopped") as mock_ensure:
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput({})
        inp._ffmpeg_proc = None
        inp._clock = MagicMock()
        inp._clock.record_mtime.return_value = 10.0
        inp._chunks_dir = Path(tempfile.mkdtemp())
        inp._watchdog = MagicMock()
        yield inp

        if inp._chunks_dir is not None:
            shutil.rmtree(inp._chunks_dir, ignore_errors=True)


class TestGetNextChunk:
    def test_no_chunks_dir_returns_none(self, srt_input):
        srt_input._chunks_dir = None
        assert srt_input.get_next_chunk() is None

    def test_no_chunk_files_returns_none(self, srt_input):
        assert srt_input.get_next_chunk() is None

    def test_single_chunk_too_new_returns_none(self, srt_input):
        chunk_file = srt_input._chunks_dir / "chunk_00000001.ts"
        chunk_file.write_text("data")
        now = time.time()
        os.utime(chunk_file, (now, now))

        srt_input._chunk_duration = 10
        result = srt_input.get_next_chunk()
        assert result is None

    def test_single_chunk_old_enough_returns_chunk(self, srt_input):
        chunk_file = srt_input._chunks_dir / "chunk_00000001.ts"
        chunk_file.write_text("data")
        old_time = time.time() - 20
        os.utime(chunk_file, (old_time, old_time))

        srt_input._chunk_duration = 10
        result = srt_input.get_next_chunk()
        assert result is not None
        assert isinstance(result, PipelineData)
        assert result.video_chunk_path == str(chunk_file)
        assert result.chunk_index == 1
        assert result.duration == 10
        assert result.metadata.get("source") == "srt"

    def test_two_chunks_excludes_latest(self, srt_input):
        chunk1 = srt_input._chunks_dir / "chunk_00000001.ts"
        chunk1.write_text("data1")
        chunk2 = srt_input._chunks_dir / "chunk_00000002.ts"
        chunk2.write_text("data2")

        result = srt_input.get_next_chunk()
        assert result is not None
        assert result.chunk_index == 1

    def test_already_processed_chunk_skipped(self, srt_input):
        chunk1 = srt_input._chunks_dir / "chunk_00000001.ts"
        chunk1.write_text("data1")
        chunk2 = srt_input._chunks_dir / "chunk_00000002.ts"
        chunk2.write_text("data2")

        srt_input._last_chunk_index = 1
        # Only chunk1 is processable (chunk2 excluded as latest),
        # but chunk1 index is not > 1, so nothing is returned.
        result = srt_input.get_next_chunk()
        assert result is None

    def test_all_chunks_processed_returns_none(self, srt_input):
        chunk1 = srt_input._chunks_dir / "chunk_00000001.ts"
        chunk1.write_text("data1")
        # Single chunk old enough
        old_time = time.time() - 20
        os.utime(chunk1, (old_time, old_time))

        srt_input._last_chunk_index = 1
        assert srt_input.get_next_chunk() is None

    def test_processable_sorted_by_index(self, srt_input):
        chunk2 = srt_input._chunks_dir / "chunk_00000002.ts"
        chunk2.write_text("data2")
        chunk1 = srt_input._chunks_dir / "chunk_00000001.ts"
        chunk1.write_text("data1")

        result = srt_input.get_next_chunk()
        assert result is not None
        assert result.chunk_index == 1

    def test_updates_last_chunk_index(self, srt_input):
        chunk1 = srt_input._chunks_dir / "chunk_00000001.ts"
        chunk1.write_text("data1")
        chunk2 = srt_input._chunks_dir / "chunk_00000002.ts"
        chunk2.write_text("data2")

        srt_input.get_next_chunk()
        assert srt_input._last_chunk_index == 1

    def test_records_mtime_via_clock(self, srt_input):
        chunk1 = srt_input._chunks_dir / "chunk_00000001.ts"
        chunk1.write_text("data1")
        chunk2 = srt_input._chunks_dir / "chunk_00000002.ts"
        chunk2.write_text("data2")

        result = srt_input.get_next_chunk()
        assert result is not None
        srt_input._clock.record_mtime.assert_called_once()
        assert result.cumulative_duration == 10.0

    def test_notifies_watchdog(self, srt_input):
        chunk1 = srt_input._chunks_dir / "chunk_00000001.ts"
        chunk1.write_text("data1")
        chunk2 = srt_input._chunks_dir / "chunk_00000002.ts"
        chunk2.write_text("data2")

        srt_input.get_next_chunk()
        srt_input._watchdog.notify_activity.assert_called_once()

    def test_consecutive_calls(self, srt_input):
        chunk1 = srt_input._chunks_dir / "chunk_00000001.ts"
        chunk1.write_text("data1")
        chunk2 = srt_input._chunks_dir / "chunk_00000002.ts"
        chunk2.write_text("data2")

        r1 = srt_input.get_next_chunk()
        assert r1 is not None and r1.chunk_index == 1

        # Add a third chunk so chunk2 is no longer the latest
        chunk3 = srt_input._chunks_dir / "chunk_00000003.ts"
        chunk3.write_text("data3")
        time.sleep(0.01)

        r2 = srt_input.get_next_chunk()
        assert r2 is not None and r2.chunk_index == 2

    def test_chunks_with_gaps_ignores_missing_indices(self, srt_input):
        chunk1 = srt_input._chunks_dir / "chunk_00000001.ts"
        chunk1.write_text("data1")
        chunk3 = srt_input._chunks_dir / "chunk_00000003.ts"
        chunk3.write_text("data3")

        result = srt_input.get_next_chunk()
        assert result is not None
        assert result.chunk_index == 1
