"""
Tests for config migration of legacy values.

Verifies that old config values are automatically migrated to new formats.
"""

import os

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_schema import SRT2WebConfig  # noqa: E402


class TestVideoCodecMigration:
    """Test video codec migration."""

    @pytest.mark.parametrize(
        "old_codec,expected",
        [
            ("libx264", "h264"),
            ("x264", "h264"),
            ("h264_nvenc", "h264"),
            ("libx265", "h265"),
            ("hevc_nvenc", "h265"),
            ("libvpx", "vp8"),
            ("libvpx-vp9", "vp9"),
        ],
    )
    def test_rtmp_codec_migration(self, old_codec, expected):
        """Old RTMP codecs should be migrated."""
        data = {"output": {"rtmp": {"video_codec": old_codec}}}
        config = SRT2WebConfig.from_dict(data)
        assert config.output.rtmp.video_codec.value == expected

    @pytest.mark.parametrize(
        "old_codec,expected",
        [
            ("libx264", "h264"),
            ("x265", "h265"),
            ("hevc_amf", "h265"),
        ],
    )
    def test_srt_codec_migration(self, old_codec, expected):
        """Old SRT codecs should be migrated."""
        data = {"output": {"srt": {"video_codec": old_codec}}}
        config = SRT2WebConfig.from_dict(data)
        assert config.output.srt.video_codec.value == expected


class TestDeviceMigration:
    """Test device migration."""

    def test_gpu_to_cuda(self):
        """'gpu' should migrate to 'cuda'."""
        data = {"modules": {"transcriber": {"device": "gpu"}}}
        config = SRT2WebConfig.from_dict(data)
        assert config.modules.transcriber.device.value == "cuda"

    def test_metal_to_mps(self):
        """'metal' should migrate to 'mps'."""
        data = {"modules": {"transcriber": {"device": "metal"}}}
        config = SRT2WebConfig.from_dict(data)
        assert config.modules.transcriber.device.value == "mps"

    def test_nvidia_to_cuda(self):
        """'nvidia' should migrate to 'cuda'."""
        data = {"modules": {"transcriber": {"device": "nvidia"}}}
        config = SRT2WebConfig.from_dict(data)
        assert config.modules.transcriber.device.value == "cuda"

    def test_tts_device_migration(self):
        """TTS device should also migrate."""
        data = {"modules": {"tts_engine": {"device": "gpu"}}}
        config = SRT2WebConfig.from_dict(data)
        assert config.modules.tts_engine.device.value == "cuda"

    def test_valid_device_not_migrated(self):
        """Valid devices should NOT be changed."""
        data = {"modules": {"transcriber": {"device": "cuda"}}}
        config = SRT2WebConfig.from_dict(data)
        assert config.modules.transcriber.device.value == "cuda"


class TestWhisperModelMigration:
    """Test Whisper model name migration."""

    @pytest.mark.parametrize(
        "old_model,expected",
        [
            ("tiny.en", "tiny"),
            ("base.en", "base"),
            ("small.en", "small"),
            ("medium.en", "medium"),
            ("large-v1", "large"),
        ],
    )
    def test_model_migration(self, old_model, expected):
        """Old model names should be migrated."""
        data = {"modules": {"transcriber": {"model": old_model}}}
        config = SRT2WebConfig.from_dict(data)
        assert config.modules.transcriber.model.value == expected

    def test_valid_model_not_migrated(self):
        """Valid model names should NOT be changed."""
        data = {"modules": {"transcriber": {"model": "small"}}}
        config = SRT2WebConfig.from_dict(data)
        assert config.modules.transcriber.model.value == "small"


class TestMultipleMigrations:
    """Test that multiple migrations work together."""

    def test_combined_migration(self):
        """Multiple legacy values should all be migrated."""
        data = {
            "modules": {
                "transcriber": {
                    "model": "tiny.en",
                    "device": "gpu",
                },
                "tts_engine": {
                    "device": "metal",
                },
            },
            "output": {
                "rtmp": {"video_codec": "libx264"},
            },
        }
        config = SRT2WebConfig.from_dict(data)

        assert config.modules.transcriber.model.value == "tiny"
        assert config.modules.transcriber.device.value == "cuda"
        assert config.modules.tts_engine.device.value == "mps"
        assert config.output.rtmp.video_codec.value == "h264"
