"""
Unit tests for Translator module.
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 1. Create the mocks
mock_argos = MagicMock()
mock_package = MagicMock()
mock_translate = MagicMock()

# 2. Setup the hierarchy
mock_argos.package = mock_package
mock_argos.translate = mock_translate

# 3. Inject into sys.modules BEFORE importing Translator
sys.modules["argostranslate"] = mock_argos
sys.modules["argostranslate.package"] = mock_package
sys.modules["argostranslate.translate"] = mock_translate

from modules.translator import Translator
from core.module_base import PipelineData, ModuleState


class TestTranslator:
    """Tests for Translator class."""

    def setup_method(self):
        """Reset mocks before each test."""
        mock_argos.reset_mock()
        mock_package.reset_mock()
        mock_translate.reset_mock()
        mock_package.get_installed_packages.return_value = []
        mock_package.get_available_packages.return_value = []

    def test_init(self):
        """Test initialization and config."""
        translator = Translator({"source_lang": "es", "target_lang": "fr"})
        assert translator._source_lang == "es"
        assert translator._target_lang == "fr"

    @patch("modules.translator.Translator._load_model")
    def test_start(self, mock_load):
        """Test module startup."""
        with patch.dict(os.environ, {"ARGOS_PACKAGES_DIR": ""}):
            translator = Translator()
            translator.start()
            assert translator.state == ModuleState.RUNNING
            mock_load.assert_called_once()
            assert translator._argos_installed is True

    def test_load_language_model_already_installed(self):
        """Test loading model when already installed."""
        translator = Translator()
        translator._argos_installed = True

        mock_pkg = MagicMock()
        mock_pkg.from_code = "es"
        mock_pkg.to_code = "en"
        mock_package.get_installed_packages.return_value = [mock_pkg]

        translator._load_model("es", "en")

        mock_translate.get_translation_from_codes.assert_called_with("es", "en")
        mock_package.update_package_index.assert_not_called()

    def test_load_language_model_not_installed(self):
        """Test loading model when installation is needed."""
        translator = Translator()
        translator._argos_installed = True
        translator._model_cache = MagicMock()
        translator._model_cache.get_argos_pair.return_value = None
        mock_package.get_installed_packages.return_value = []

        mock_avail_pkg = MagicMock()
        mock_avail_pkg.from_code = "es"
        mock_avail_pkg.to_code = "en"
        mock_package.get_available_packages.return_value = [mock_avail_pkg]
        mock_translate.get_translation_from_codes.return_value = MagicMock()

        translator._load_model("es", "en")

        mock_package.update_package_index.assert_called_once()
        mock_avail_pkg.install.assert_called_once()

    def test_load_language_model_not_found(self):
        """Test behavior when no package is found."""
        translator = Translator()
        translator._argos_installed = True
        translator._model_cache = MagicMock()
        translator._model_cache.get_argos_pair.return_value = None
        mock_package.get_installed_packages.return_value = []
        mock_package.get_available_packages.return_value = []

        with pytest.raises(ValueError, match="No translation package found"):
            translator._load_model("xx", "yy")

    def test_do_process(self):
        """Test translation processing."""
        translator = Translator()
        mock_pipeline = MagicMock()
        mock_pipeline.translate.return_value = "Hello"
        translator._translation_pipeline = mock_pipeline

        data = PipelineData(
            transcript="Hola",
            transcript_segments=[{"start": 0.0, "end": 1.0, "text": "Hola"}],
        )
        result = translator._do_process(data)

        assert result.translated_text == "Hello"
        assert len(result.translated_segments) == 1
        assert result.translated_segments[0]["text"] == "Hello"
        assert result.translated_segments[0]["start"] == 0.0

    def test_do_process_no_transcript(self):
        """Test processing when no transcript is present."""
        translator = Translator()
        mock_pipeline = MagicMock()
        translator._translation_pipeline = mock_pipeline

        data = PipelineData(transcript="")
        result = translator._do_process(data)

        assert result.translated_text is None
        mock_pipeline.translate.assert_not_called()

    def test_do_process_no_pipeline(self):
        """Test processing when translation pipeline is not loaded."""
        translator = Translator()
        translator._translation_pipeline = None

        data = PipelineData(transcript="Hola")
        result = translator._do_process(data)

        # Should return data unchanged
        assert result.translated_text is None
