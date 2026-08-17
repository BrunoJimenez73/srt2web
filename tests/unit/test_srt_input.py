"""
Unit tests for SRT Input module.
"""

from core.module_base import PipelineData


class TestSRTInputInit:
    """Tests for SRTInput initialization."""

    def test_init_default_config(self):
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput({})
        assert inp.name == "srt"
        assert inp._srt_port == 9000
        assert inp._srt_mode == "listener"
        assert inp._chunk_duration == 10
        assert inp._last_chunk_index == -1

    def test_init_custom_config(self):
        from modules.inputs.srt_input import SRTInput

        config = {
            "listen_port": 8000,
            "mode": "caller",
            "latency_ms": 500,
            "chunk_duration_sec": 15,
            "caller_address": "192.168.1.1",
        }
        inp = SRTInput(config)
        assert inp._srt_port == 8000
        assert inp._srt_mode == "caller"
        assert inp._srt_latency_ms == 500
        assert inp._chunk_duration == 15
        assert inp._srt_caller_address == "192.168.1.1"

    def test_init_sets_gpu_info(self):
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput({})
        assert "nvenc" in inp._gpu_info
        assert "qsv" in inp._gpu_info

    def test_init_watchdog_enabled_by_default(self):
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput({})
        assert inp._watchdog_enabled is True
        assert inp._watchdog_check_interval == 5.0


class TestSRTInputConfigure:
    """Tests for SRTInput configure."""

    def test_configure_updates_port(self):
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput({})
        inp.configure({"listen_port": 7000})
        assert inp._srt_port == 7000

    def test_configure_preserves_unchanged(self):
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput({"listen_port": 9000})
        inp.configure({"latency_ms": 2000})
        assert inp._srt_port == 9000
        assert inp._srt_latency_ms == 2000


class TestSRTInputGetConnectionInfo:
    """Tests for SRTInput get_connection_info."""

    def test_listener_connection_info(self):
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput({"listen_port": 9000, "mode": "listener"})
        info = inp.get_connection_info()
        assert info["type"] == "srt"
        assert info["mode"] == "listener"
        assert info["port"] == 9000
        assert "0.0.0.0" in info["url"]

    def test_caller_connection_info(self):
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput(
            {
                "listen_port": 9000,
                "mode": "caller",
                "caller_address": "10.0.0.1",
            }
        )
        info = inp.get_connection_info()
        assert info["mode"] == "caller"
        assert "10.0.0.1" in info["url"]


class TestSRTInputGetNextChunk:
    """Tests for SRTInput get_next_chunk."""

    def test_returns_none_when_no_chunks_dir(self):
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput({})
        result = inp.get_next_chunk()
        assert result is None

    def test_returns_none_when_empty_chunks_dir(self, tmp_path):
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput({})
        inp._chunks_dir = str(tmp_path)
        result = inp.get_next_chunk()
        assert result is None

    def test_single_fresh_chunk_returns_none(self, tmp_path):
        from modules.inputs.srt_input import SRTInput

        chunk_path = tmp_path / "chunk_000001.ts"
        chunk_path.write_text("fake video data")

        inp = SRTInput({})
        inp._chunk_duration = 10
        inp._chunks_dir = str(tmp_path)

        result = inp.get_next_chunk()
        assert result is None

    def test_get_next_chunk_returns_data(self, tmp_path):
        from modules.inputs.srt_input import SRTInput

        chunk_path = tmp_path / "chunk_000001.ts"
        chunk_path.write_text("fake video data")

        second_path = tmp_path / "chunk_000002.ts"
        second_path.write_text("more fake video")

        inp = SRTInput({})
        inp._chunk_duration = 10
        inp._chunks_dir = str(tmp_path)

        result = inp.get_next_chunk()
        assert result is not None
        assert isinstance(result, PipelineData)
        assert result.chunk_index == 1
        assert result.video_chunk_path is not None
        assert "chunk_000001" in result.video_chunk_path
        assert result.duration == 10
        assert result.metadata.get("source") == "srt"

    def test_tracks_last_chunk_index(self, tmp_path):
        from modules.inputs.srt_input import SRTInput

        for i in range(1, 4):
            (tmp_path / f"chunk_{i:06d}.ts").write_text(f"data{i}")

        inp = SRTInput({})
        inp._chunk_duration = 10
        inp._chunks_dir = str(tmp_path)

        c1 = inp.get_next_chunk()
        assert c1 is not None
        assert inp._last_chunk_index == 1

        c2 = inp.get_next_chunk()
        assert c2 is not None
        assert inp._last_chunk_index == 2

    def test_skips_processed_chunks(self, tmp_path):
        from modules.inputs.srt_input import SRTInput

        for i in range(1, 5):
            (tmp_path / f"chunk_{i:06d}.ts").write_text(f"data{i}")

        inp = SRTInput({})
        inp._chunk_duration = 10
        inp._chunks_dir = str(tmp_path)
        inp._last_chunk_index = 2

        result = inp.get_next_chunk()
        assert result is not None
        assert result.chunk_index == 3


class TestSRTInputState:
    """Tests for SRTInput state queries."""

    def test_is_receiving_false_by_default(self):
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput({})
        assert inp.is_receiving() is False

    def test_is_healthy_no_watchdog(self):
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput({})
        inp._watchdog_enabled = False
        assert inp.is_healthy() is False

    def test_get_status_idle(self):
        from modules.inputs.srt_input import SRTInput

        inp = SRTInput({})
        status = inp.get_status()
        assert status.name == "input"
        assert status.processed_chunks == 0
