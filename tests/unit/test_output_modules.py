"""
Unit tests for output modules: File, RTMP, SRT, WebRTC.
"""

import os
from unittest.mock import MagicMock, patch

from core.module_base import PipelineData

# ─── FileOutput ───────────────────────────────────────────────────────────────


class TestFileOutput:
    """Tests for FileOutput."""

    def test_init_default(self):
        from modules.outputs.file_output import FileOutput

        out = FileOutput({})
        assert out.name == "file"
        assert out._counter == 0
        assert out._save_video is True

    def test_configure(self):
        from modules.outputs.file_output import FileOutput

        out = FileOutput({})
        out.configure({"save_video": False, "save_audio": False})
        assert out._save_video is False
        assert out._save_audio is False

    def test_start_creates_dirs(self, tmp_path):
        from modules.outputs.file_output import FileOutput

        out = FileOutput({})
        out.set_output_dir(str(tmp_path))
        out.start()

        assert os.path.isdir(os.path.join(str(tmp_path), "video"))
        assert os.path.isdir(os.path.join(str(tmp_path), "audio"))
        assert os.path.isdir(os.path.join(str(tmp_path), "subtitles"))

    def test_stop_logs_counter(self):
        from modules.outputs.file_output import FileOutput

        out = FileOutput({})
        out._counter = 5
        out.stop()

    def test_write_copies_video(self, tmp_path):
        from modules.outputs.file_output import FileOutput

        video_src = os.path.join(str(tmp_path), "source.ts")
        with open(video_src, "wb") as f:
            f.write(b"fake video data")

        out = FileOutput({})
        out.set_output_dir(str(tmp_path))
        out.start()

        data = PipelineData(chunk_index=1, video_chunk_path=video_src)
        out.write(data)

        expected = os.path.join(str(tmp_path), "video", "chunk_000001.mp4")
        assert os.path.exists(expected)
        assert out._counter == 1

    def test_write_skips_missing_video(self, tmp_path):
        from modules.outputs.file_output import FileOutput

        out = FileOutput({})
        out.set_output_dir(str(tmp_path))
        out.start()

        data = PipelineData(chunk_index=1, video_chunk_path="/nonexistent.ts")
        out.write(data)
        assert out._counter == 1

    def test_get_stream_info(self):
        from modules.outputs.file_output import FileOutput

        out = FileOutput({})
        info = out.get_stream_info()
        assert info["type"] == "file"
        assert info["chunks_saved"] == 0


# ─── RTMPOutput ──────────────────────────────────────────────────────────────


class TestRTMPOutput:
    """Tests for RTMPOutput."""

    def test_init_default(self):
        from modules.outputs.rtmp_output import RTMPOutput

        out = RTMPOutput({})
        assert out._url == ""
        assert out._video_bitrate == "2500k"
        assert out._streaming is False

    def test_init_with_config(self):
        from modules.outputs.rtmp_output import RTMPOutput

        config = {"url": "rtmp://example.com/live", "video_bitrate": "5000k"}
        out = RTMPOutput(config)
        assert out._url == "rtmp://example.com/live"
        assert out._video_bitrate == "5000k"

    def test_configure(self):
        from modules.outputs.rtmp_output import RTMPOutput

        out = RTMPOutput({})
        out.configure({"url": "rtmp://new.url/stream", "video_bitrate": "1000k"})
        assert out._url == "rtmp://new.url/stream"
        assert out._video_bitrate == "1000k"

    def test_is_streaming_false_by_default(self):
        from modules.outputs.rtmp_output import RTMPOutput

        out = RTMPOutput({})
        assert out.is_streaming() is False

    def test_get_stream_info(self):
        from modules.outputs.rtmp_output import RTMPOutput

        out = RTMPOutput({"url": "rtmp://test/stream"})
        info = out.get_stream_info()
        assert info["type"] == "rtmp"
        assert info["url"] == "rtmp://test/stream"
        assert info["streaming"] is False

    def test_write_does_nothing_when_not_streaming(self):
        from modules.outputs.rtmp_output import RTMPOutput

        out = RTMPOutput({})
        data = PipelineData(chunk_index=0, video_chunk_path="/tmp/test.ts")
        out.write(data)


# ─── SRTOutput ───────────────────────────────────────────────────────────────


class TestSRTOutput:
    """Tests for SRTOutput."""

    def test_init_default(self):
        from modules.outputs.srt_output import SRTOutput

        out = SRTOutput({})
        assert out.name == "srt"
        assert out._url == "srt://localhost:9001"
        assert out._mode == "caller"
        assert out._streaming is False

    def test_init_with_config(self):
        from modules.outputs.srt_output import SRTOutput

        out = SRTOutput({"url": "srt://example.com:5000", "mode": "listener"})
        assert out._url == "srt://example.com:5000"
        assert out._mode == "listener"

    def test_configure(self):
        from modules.outputs.srt_output import SRTOutput

        out = SRTOutput({})
        out.configure({"mode": "rendezvous", "latency_ms": 500})
        assert out._mode == "rendezvous"
        assert out._latency_ms == 500

    def test_is_streaming_false_by_default(self):
        from modules.outputs.srt_output import SRTOutput

        out = SRTOutput({})
        assert out.is_streaming() is False

    def test_get_stream_info(self):
        from modules.outputs.srt_output import SRTOutput

        out = SRTOutput({"url": "srt://test/stream"})
        info = out.get_stream_info()
        assert info["type"] == "srt"
        assert info["url"] == "srt://test/stream"
        assert info["streaming"] is False


# ─── WebRTCOutput ────────────────────────────────────────────────────────────


class TestWebRTCOutput:
    """Tests for WebRTCOutput."""

    def test_init(self):
        with patch("modules.webrtc_engine.WebRTCEngine") as MockEngine:
            from modules.outputs.webrtc_output import WebRTCOutput

            out = WebRTCOutput({})
            assert out.name == "webrtc"
            MockEngine.assert_called_once()

    def test_start_stop(self):
        mock_engine = MagicMock()
        with patch("modules.webrtc_engine.WebRTCEngine", return_value=mock_engine):
            from modules.outputs.webrtc_output import WebRTCOutput

            out = WebRTCOutput({})
            out.start()
            assert out._running is True
            mock_engine.set_output_dir.assert_called_once()
            mock_engine.start.assert_called_once()

            out.stop()
            assert out._running is False
            mock_engine.stop.assert_called_once()

    def test_get_stream_info(self):
        with patch("modules.webrtc_engine.WebRTCEngine"):
            from modules.outputs.webrtc_output import WebRTCOutput

            out = WebRTCOutput({})
            info = out.get_stream_info()
            assert info["type"] == "webrtc"
            assert info["status"] == "stopped"

    def test_write_does_nothing(self):
        mock_engine = MagicMock()
        mock_engine.running = True
        with patch("modules.webrtc_engine.WebRTCEngine", return_value=mock_engine):
            from modules.outputs.webrtc_output import WebRTCOutput

            out = WebRTCOutput({})
            data = PipelineData(chunk_index=0)
            out.write(data)
