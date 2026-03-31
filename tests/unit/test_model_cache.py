"""
Tests for Model Cache implementation.
"""

import pytest
import threading
from unittest.mock import MagicMock, patch


class TestModelCache:
    """Test suite for ModelCache singleton."""

    def test_singleton(self):
        """Test that ModelCache is a singleton."""
        from core.model_cache import ModelCache

        mc1 = ModelCache()
        mc2 = ModelCache()

        assert mc1 is mc2

    def test_initialization(self):
        """Test ModelCache initialization."""
        from core.model_cache import ModelCache

        mc = ModelCache()

        assert mc._initialized is True
        assert len(mc._whisper_models) == 0
        assert len(mc._argos_indexes) == 0
        assert mc._models_loaded is False

    def test_cache_directories(self):
        """Test cache directory properties."""
        from core.model_cache import ModelCache

        mc = ModelCache()

        assert "whisper" in str(mc.whisper_cache_dir)
        assert "argos" in str(mc.argos_cache_dir)
        assert mc.whisper_cache_dir.exists()

    def test_get_whisper_model_caches(self):
        """Test that Whisper models are cached."""
        from core.model_cache import ModelCache

        mc = ModelCache()
        mc._whisper_models.clear()

        mock_model = MagicMock()

        with patch("faster_whisper.WhisperModel", return_value=mock_model) as mock:
            model1 = mc.get_whisper_model("tiny", "cpu", "int8")
            model2 = mc.get_whisper_model("tiny", "cpu", "int8")

            assert model1 is model2
            assert mock.call_count == 1

    def test_get_whisper_model_different_keys(self):
        """Test that different model configs create different models."""
        from core.model_cache import ModelCache

        mc = ModelCache()
        mc._whisper_models.clear()

        mock_model = MagicMock()

        with patch("faster_whisper.WhisperModel", return_value=mock_model) as mock:
            mc.get_whisper_model("tiny", "cpu", "int8")
            mc.get_whisper_model("small", "cpu", "int8")

            assert mock.call_count == 2

    def test_preload_whisper(self):
        """Test background preload of Whisper model."""
        from core.model_cache import ModelCache

        mc = ModelCache()
        mc._whisper_models.clear()
        mc._models_loaded = False
        mc._preload_done = threading.Event()

        mock_model = MagicMock()

        with patch("faster_whisper.WhisperModel", return_value=mock_model):
            mc.preload_whisper("tiny", "cpu", "int8")
            mc.wait_for_preload(timeout=5)

        assert mc._models_loaded is True

    def test_wait_for_preload_timeout(self):
        """Test timeout on preload wait."""
        from core.model_cache import ModelCache

        mc = ModelCache()
        mc._preload_done = threading.Event()

        result = mc.wait_for_preload(timeout=0.1)

        assert result is False

    def test_clear_cache(self):
        """Test clearing the cache."""
        from core.model_cache import ModelCache

        mc = ModelCache()
        mc._whisper_models["test"] = MagicMock()
        mc._argos_indexes["test"] = MagicMock()
        mc._models_loaded = True
        mc._preload_done.set()

        mc.clear_cache()

        assert len(mc._whisper_models) == 0
        assert len(mc._argos_indexes) == 0
        assert mc._models_loaded is False
        assert mc._preload_done.is_set() is False

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        from core.model_cache import ModelCache

        mc = ModelCache()
        mc._whisper_models["test1"] = MagicMock()
        mc._argos_indexes["test2"] = MagicMock()

        mock_process = MagicMock()
        mock_process.memory_info.return_value.rss = 1024 * 1024 * 1024

        with patch("psutil.Process", return_value=mock_process):
            stats = mc.get_cache_stats()

        assert stats["whisper_models_loaded"] == 1
        assert stats["argos_pairs_loaded"] == 1
        assert stats["models_loaded"] is False
        assert "cache_dir" in stats


class TestModelCacheArgos:
    """Test suite for Argos translation caching."""

    def test_get_argos_pair_returns_none_when_not_available(self):
        """Test that missing language pair returns None."""
        from core.model_cache import ModelCache

        mc = ModelCache()
        mc._argos_indexes.clear()

        with patch.dict("sys.modules", {"argostranslate": None}):
            pair = mc.get_argos_pair("en", "invalid_lang")
            assert pair is None

    def test_get_argos_pair_import_error(self):
        """Test handling when argostranslate is not installed."""
        from core.model_cache import ModelCache

        mc = ModelCache()

        with patch.dict("sys.modules", {"argostranslate": None}):
            pair = mc.get_argos_pair("en", "es")
            assert pair is None


class TestModelCacheWarmUp:
    """Test suite for model warm-up functionality."""

    def test_warm_up_cpu(self):
        """Test warm-up with CPU device."""
        from core.model_cache import ModelCache

        mc = ModelCache()

        config = {
            "modules": {
                "transcriber": {"model": "tiny", "device": "cpu"},
                "translator": {"source_lang": "en", "target_lang": "es"},
            }
        }

        mock_model = MagicMock()

        with patch("faster_whisper.WhisperModel", return_value=mock_model):
            with patch("psutil.Process", MagicMock()):
                with patch.dict("sys.modules", {"argostranslate": None}):
                    mc.warm_up(config)

    @pytest.mark.skip(reason="Skipping due to pydantic/torch environment issue")
    def test_warm_up_auto_detects_cuda(self):
        """Test warm-up with auto device detection."""
        from core.model_cache import ModelCache

        mc = ModelCache()

        config = {
            "modules": {
                "transcriber": {"model": "tiny", "device": "auto"},
                "translator": {"source_lang": "en", "target_lang": "es"},
            }
        }

        mock_model = MagicMock()

        with patch("faster_whisper.WhisperModel", return_value=mock_model):
            with patch(
                "argostranslate.translate.get_available_languages", return_value=[]
            ):
                with patch(
                    "argostranslate.translate.translate_pair", return_value=MagicMock()
                ):
                    with patch("torch.cuda.is_available", return_value=False):
                        mc.warm_up(config)
