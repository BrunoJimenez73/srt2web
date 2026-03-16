"""
Translator Module — translates transcribed text.

Uses argostranslate for completely offline, free machine translation.
"""

import os
import logging
from typing import Optional

from core.module_base import BaseModule, PipelineData, ModuleState

logger = logging.getLogger("srt2web.module.translator")


class Translator(BaseModule):
    """
    Translates text segments using offline Argos Translate models.
    Downloads required language packages on first use.
    """

    def __init__(self, config: Optional[dict] = None):
        self._source_lang = "es"
        self._target_lang = "en"
        self._translation_pipeline = None
        self._argos_installed = False
        super().__init__("translator", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._source_lang = config.get("source_lang", self._source_lang)
        self._target_lang = config.get("target_lang", self._target_lang)
        
        # If language changed while running, reload pipeline
        if self.state == ModuleState.RUNNING and self._argos_installed:
            self._load_language_model()

    def start(self) -> None:
        """Initialize the translation engine and models."""
        self._state = ModuleState.STARTING
        
        try:
            import argostranslate.package
            import argostranslate.translate
            self._argos_installed = True
            
            # Setup Argos packages cache dir if needed
            os.environ["ARGOS_PACKAGES_DIR"] = os.path.abspath(os.path.join(".", "models", "argos"))
            
            self._load_language_model()
            
            self._state = ModuleState.RUNNING
            logger.info(f"Translator ready: {self._source_lang} -> {self._target_lang}")
            
        except ImportError:
            self._state = ModuleState.ERROR
            self._error_message = "argostranslate package not installed"
            logger.error(self._error_message)
            self.enabled = False
        except Exception as e:
            self._state = ModuleState.ERROR
            self._error_message = f"Failed to init translator: {e}"
            logger.error(self._error_message)
            self.enabled = False

    def _load_language_model(self):
        """Install package if missing and create translation pipeline."""
        import argostranslate.package
        import argostranslate.translate

        # Check if installed
        installed = argostranslate.package.get_installed_packages()
        package_found = False
        
        for pkg in installed:
            if pkg.from_code == self._source_lang and pkg.to_code == self._target_lang:
                package_found = True
                break

        if not package_found:
            msg = f"Downloading translation model for {self._source_lang} -> {self._target_lang}... This may take a minute."
            logger.info(msg)
            self.logger.info(msg) # Broadcast to web UI
            
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            
            target_pkg = next(
                (pkg for pkg in available_packages 
                 if pkg.from_code == self._source_lang and pkg.to_code == self._target_lang),
                None
            )
            
            if target_pkg:
                target_pkg.install()
                success_msg = f"Translation model {self._source_lang}->{self._target_lang} installed successfully!"
                logger.info(success_msg)
                self.logger.info(success_msg) # Broadcast to web UI
            else:
                raise ValueError(f"No translation package found from '{self._source_lang}' to '{self._target_lang}'")

        # Get the actual translation function
        self._translation_pipeline = argostranslate.translate.get_translation_from_codes(
            self._source_lang, 
            self._target_lang
        )

    def stop(self) -> None:
        """Cleanup."""
        self._state = ModuleState.STOPPING
        self._translation_pipeline = None
        self._state = ModuleState.IDLE

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Translate the transcript.
        """
        if not self._translation_pipeline or not data.transcript:
            return data

        try:
            # Override source language if detected language is valid and differs
            # Note: For simplicity we stick to configured source_lang here, 
            # dynamic reloading per chunk would be too slow
            
            # Translate full text
            data.translated_text = self._translation_pipeline.translate(data.transcript)
            
            # Translate individual segments (useful for precise subtitles)
            if data.transcript_segments:
                translated_segs = []
                for seg in data.transcript_segments:
                    translated_segs.append({
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": self._translation_pipeline.translate(seg["text"])
                    })
                data.translated_segments = translated_segs
            
            logger.info(f"Translated: {data.translated_text}")

        except Exception as e:
            logger.error(f"Translation error: {e}")

        return data
