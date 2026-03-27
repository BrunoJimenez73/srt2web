"""
Translator Module — translates transcribed text.

Uses argostranslate for completely offline, free machine translation.
"""

import os
import logging
from typing import Optional

from core.module_base import BaseModule, PipelineData, ModuleState
from core.model_cache import ModelCache

logger = logging.getLogger("srt2web.module.translator")


class Translator(BaseModule):
    """
    Translates text segments using offline Argos Translate models.
    Downloads required language packages on first use.
    """

    def __init__(self, config: Optional[dict] = None):
        self._source_lang = config.get("source_lang", "es") if config else "es"
        self._target_lang = config.get("target_lang", "en") if config else "en"
        self._translation_pipeline = None
        self._argos_installed = False
        self._waiting_for_language = self._source_lang == "auto"
        self._current_source_lang = None
        self._model_cache = ModelCache()
        super().__init__("translator", config)

    def configure(self, config: dict) -> None:
        """
        Update translator configuration and reload translation model if language settings changed.
        Called during pipeline reconfiguration (hot-reload).
        """
        # Apply pydantic patch BEFORE any argostranslate operations
        self._patch_pydantic_for_argos()
        
        new_source_lang = config.get("source_lang", self._source_lang)
        new_target_lang = config.get("target_lang", self._target_lang)

        # Determine if we should wait for language detection
        new_waiting_for_language = new_source_lang == "auto"

        # Check if we need to reload the translation model
        model_needs_reload = False

        # Case 1: We're not waiting for language and source/target changed
        if not new_waiting_for_language and (
            new_source_lang != self._source_lang or new_target_lang != self._target_lang
        ):
            model_needs_reload = True

        # Case 2: We were waiting for language but now have a fixed source language
        elif (
            self._waiting_for_language
            and not new_waiting_for_language
            and new_source_lang != "auto"
        ):
            model_needs_reload = True

        # Reload model if needed
        if model_needs_reload:
            self._load_model(new_source_lang, new_target_lang)
            self._current_source_lang = new_source_lang

        # Update internal state
        self._source_lang = new_source_lang
        self._target_lang = new_target_lang
        self._waiting_for_language = new_waiting_for_language

    def start(self) -> None:
        """Initialize the translation engine and models."""
        self._state = ModuleState.STARTING

        try:
            # Patch pydantic v1 before importing argostranslate to avoid Python 3.14 issues
            self._patch_pydantic_for_argos()
            
            import argostranslate.package
            import argostranslate.translate

            self._argos_installed = True

            # Setup Argos packages cache dir if needed
            os.environ["ARGOS_PACKAGES_DIR"] = os.path.abspath(
                os.path.join(".", "models", "argos")
            )

            # Only load model if not waiting for language (i.e., source_lang is not auto)
            if not self._waiting_for_language:
                self._load_model(self._source_lang, self._target_lang)

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

    def _patch_pydantic_for_argos(self):
        """Patch pydantic v1 for Python 3.14 compatibility before importing argostranslate."""
        import sys
        import warnings
        
        # Suppress pydantic v1 warnings
        warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality.*")
        
        try:
            from pydantic.v1 import fields as pydantic_v1_fields
            from pydantic.v1 import errors as pydantic_v1_errors
            
            if hasattr(pydantic_v1_fields.ModelField, '_patched_for_314'):
                return  # Already patched
            
            original_init = pydantic_v1_fields.ModelField.__init__
            original_prepare = pydantic_v1_fields.ModelField.prepare
            
            def patched_init(self, *args, **kwargs):
                try:
                    original_init(self, *args, **kwargs)
                except pydantic_v1_errors.ConfigError as e:
                    if "unable to infer type" in str(e):
                        self.type_ = str
                        self.outer_type_ = str
                        self.required = False
                        self.field_info.extra.pop("regex", None)
                    else:
                        raise
            
            def patched_prepare(self):
                try:
                    original_prepare(self)
                except Exception as e:
                    if "regex" in str(e).lower() or "unenforced" in str(e).lower():
                        self.field_info.extra.pop("regex", None)
                        if hasattr(self.field_info, 'regex'):
                            self.field_info.regex = None
                        try:
                            original_prepare(self)
                        except:
                            pass
                    else:
                        raise
            
            pydantic_v1_fields.ModelField.__init__ = patched_init
            pydantic_v1_fields.ModelField.prepare = patched_prepare
            pydantic_v1_fields.ModelField._patched_for_314 = True
            
            logger.debug("pydantic.v1 patched for Python 3.14")
            
        except Exception as e:
            logger.debug(f"pydantic patch failed (may not be needed): {e}")

    def _load_model(self, source_lang: str, target_lang: str):
        """Install package if missing and create translation pipeline using ModelCache."""
        import argostranslate.package
        import argostranslate.translate

        # Try to get from cache first
        cached_pair = self._model_cache.get_argos_pair(source_lang, target_lang)
        if cached_pair:
            self._translation_pipeline = cached_pair
            logger.info(f"Using cached Argos pair: {source_lang}->{target_lang}")
            return

        # Check if installed
        installed = argostranslate.package.get_installed_packages()
        package_found = False

        for pkg in installed:
            if pkg.from_code == source_lang and pkg.to_code == target_lang:
                package_found = True
                break

        if not package_found:
            msg = f"Downloading translation model for {source_lang} -> {target_lang}... This may take a minute."
            logger.info(msg)
            self.logger.info(msg)  # Broadcast to web UI

            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()

            target_pkg = next(
                (
                    pkg
                    for pkg in available_packages
                    if pkg.from_code == source_lang and pkg.to_code == target_lang
                ),
                None,
            )

            if target_pkg:
                target_pkg.install()
                success_msg = f"Translation model {source_lang}->{target_lang} installed successfully!"
                logger.info(success_msg)
                self.logger.info(success_msg)  # Broadcast to web UI
            else:
                raise ValueError(
                    f"No translation package found from '{source_lang}' to '{target_lang}'"
                )

        # Get the actual translation function
        self._translation_pipeline = (
            argostranslate.translate.get_translation_from_codes(
                source_lang, target_lang
            )
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
            # Determine source language to use
            source_lang = self._source_lang
            if self._waiting_for_language and data.detected_language:
                # Use detected language from transcriber if available
                source_lang = data.detected_language
                # If we need to reload the model for this language pair, do it
                if self._current_source_lang != source_lang:
                    self._load_model(source_lang, self._target_lang)
                    self._current_source_lang = source_lang
                    self._waiting_for_language = False
                    logger.info(
                        f"Translator switched to {self._source_lang} -> {self._target_lang}"
                    )

            # Translate full text
            data.translated_text = self._translation_pipeline.translate(data.transcript)

            # Translate individual segments (useful for precise subtitles)
            if data.transcript_segments:
                translated_segs = []
                for seg in data.transcript_segments:
                    translated_segs.append(
                        {
                            "start": seg["start"],
                            "end": seg["end"],
                            "text": self._translation_pipeline.translate(seg["text"]),
                        }
                    )
                data.translated_segments = translated_segs

            logger.info(f"Translated: {data.translated_text}")

        except Exception as e:
            logger.error(f"Translation error: {e}")

        return data
