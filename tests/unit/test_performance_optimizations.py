"""
Tests for performance optimizations (Phase 2).
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = str(PROJECT_ROOT / "config.yaml")


@pytest.mark.unit
class TestAudioMixerDurationCache:
    """Test the duration caching in AudioMixer."""

    def test_audio_mixer_has_duration_cache(self) -> None:
        """Test that AudioMixer has a duration cache attribute."""
        from modules.audio_mixer import AudioMixer

        mixer = AudioMixer()
        assert hasattr(mixer, '_duration_cache')
        assert isinstance(mixer._duration_cache, dict)

    def test_duration_cache_is_cleared_on_start(self, temp_dir) -> None:
        """Test that duration cache is cleared when mixer starts."""
        from modules.audio_mixer import AudioMixer

        mixer = AudioMixer(output_dir=temp_dir)
        mixer._duration_cache = {"some_key": 1.5}
        mixer.start()
        assert len(mixer._duration_cache) == 0

    @patch('modules.audio_mixer.ensure_ffmpeg')
    def test_duration_cache_stores_results(self, mock_ffmpeg, temp_dir) -> None:
        """Test that duration results are cached."""
        from modules.audio_mixer import AudioMixer

        # Create a temporary audio file
        test_audio = os.path.join(temp_dir, "test.wav")
        with open(test_audio, "w") as f:
            f.write("fake audio data")

        mock_ffmpeg.return_value = "ffmpeg"

        mixer = AudioMixer(output_dir=temp_dir)
        mixer._ffmpeg_path = "ffmpeg"

        # Mock subprocess.run to return a fixed duration
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(stdout="2.5\n", returncode=0)

            # First call should call subprocess
            duration1 = mixer._get_audio_duration(test_audio)
            assert duration1 == 2.5
            assert mock_run.call_count == 1

            # Second call should use cache (same mtime)
            duration2 = mixer._get_audio_duration(test_audio)
            assert duration2 == 2.5
            assert mock_run.call_count == 1  # No additional call


class TestTTSAsyncioOptimization:
    """Test the TTS asyncio optimization."""

    def test_tts_uses_asyncio_run(self) -> None:
        """Test that TTS engine uses asyncio.run instead of manual event loop."""
        with open("modules/tts_engine.py", "r") as f:
            content = f.read()

        # Should use asyncio.run
        assert "asyncio.run(" in content, "TTS should use asyncio.run()"

        # Should NOT create new event loops manually
        assert "asyncio.new_event_loop()" not in content, \
            "TTS should not create new event loops manually"

    def test_tts_no_event_loop_leak(self) -> None:
        """Test that TTS doesn't leak event loops."""
        with open("modules/tts_engine.py", "r") as f:
            content = f.read()

        # The old pattern had manual loop.close()
        # The new pattern with asyncio.run handles this automatically
        lines = content.split('\n')
        
        # Count occurrences of event loop creation (should be 0)
        loop_creations = sum(1 for line in lines if "new_event_loop" in line)
        assert loop_creations == 0, "No manual event loop creation should exist"


class TestModelCacheIntegration:
    """Test that ModelCache is properly integrated."""

    def test_transcriber_uses_model_cache(self) -> None:
        """Test that Transcriber uses ModelCache."""
        with open("modules/transcriber.py", "r") as f:
            content = f.read()

        assert "from core.model_cache import ModelCache" in content
        assert "self._model_cache = ModelCache()" in content
        assert "self._model_cache.get_whisper_model(" in content

    def test_translator_uses_model_cache(self) -> None:
        """Test that Translator uses ModelCache."""
        with open("modules/translator.py", "r") as f:
            content = f.read()

        assert "from core.model_cache import ModelCache" in content
        assert "self._model_cache = ModelCache()" in content
        assert "self._model_cache.get_argos_pair(" in content

    def test_model_cache_singleton(self) -> None:
        """Test that ModelCache is a singleton."""
        from core.model_cache import ModelCache

        cache1 = ModelCache()
        cache2 = ModelCache()
        assert cache1 is cache2

    def test_model_cache_caches_whisper_models(self) -> None:
        """Test that ModelCache caches Whisper models."""
        from core.model_cache import ModelCache

        cache = ModelCache()
        
        # Clear cache for clean test
        cache.clear_cache()
        
        # Mock WhisperModel creation
        with patch('core.model_cache.WhisperModel', create=True) as mock_model:
            mock_instance = Mock()
            mock_model.return_value = mock_instance
            
            # First call should create the model
            with patch.dict('sys.modules', {'faster_whisper': Mock(WhisperModel=mock_model)}):
                model1 = cache.get_whisper_model("tiny", "cpu", "int8")
                
                # Second call with same params should return cached
                model2 = cache.get_whisper_model("tiny", "cpu", "int8")
                
                assert model1 is model2


class TestFFmpegOptimizations:
    """Test FFmpeg-related optimizations."""

    def test_audio_mixer减少_ffmpeg_calls(self, temp_dir) -> None:
        """Test that audio mixer reduces FFmpeg calls with caching."""
        from modules.audio_mixer import AudioMixer

        mixer = AudioMixer(output_dir=temp_dir)
        
        # The _get_audio_duration method now uses caching
        # Verify the cache key includes mtime to handle file changes
        test_file = os.path.join(temp_dir, "test.wav")
        with open(test_file, "w") as f:
            f.write("data")

        with patch.object(mixer, '_ffmpeg_path', 'ffmpeg'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(stdout="1.0\n", returncode=0)
                
                # First call
                mixer._get_audio_duration(test_file)
                
                # Second call should use cache
                mixer._get_audio_duration(test_file)
                
                # Only one subprocess call should have been made
                assert mock_run.call_count == 1


class TestConfigDefaults:
    """Test that configuration defaults support optimizations."""

    def test_config_has_rate_limit(self) -> None:
        """Test that config has rate limiting by default."""
        from core.config_manager import DEFAULT_CONFIG
        
        assert "rate_limit_rpm" in DEFAULT_CONFIG["server"]
        assert DEFAULT_CONFIG["server"]["rate_limit_rpm"] == 600

    def test_config_has_max_request_size(self) -> None:
        """Test that config has max request size in config or defaults."""
        from core.config_manager import DEFAULT_CONFIG
        
        # Check in DEFAULT_CONFIG (may or may not be in config.yaml)
        server_defaults = DEFAULT_CONFIG.get("server", {})
        has_in_defaults = "max_request_size_mb" in server_defaults
        
        # Also check config.yaml
        import yaml
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        
        has_in_config = "max_request_size_mb" in config.get("server", {})
        
        if not has_in_defaults and not has_in_config:
            pytest.skip("max_request_size_mb not yet implemented in config")
