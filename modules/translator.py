"""
Translator Module — translates transcribed text.

Uses argostranslate for completely offline, free machine translation.
"""

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Any

from core.model_cache import ModelCache
from core.module_base import BaseModule, ModuleState, PipelineData

logger = logging.getLogger("srt2web.module.translator")

_TRANSLATION_CACHE_SIZE = 256  # entradas FIFO máximas por pipeline


class Translator(BaseModule):
    """
    Translates text segments using offline Argos Translate models.
    Downloads required language packages on first use.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._source_lang = config.get("source_lang", "es") if config else "es"
        self._target_lang = config.get("target_lang", "en") if config else "en"
        self._translation_pipeline = None
        self._argos_installed = False
        self._waiting_for_language = self._source_lang == "auto"
        self._current_source_lang = None
        self._model_cache = ModelCache()
        # Cache LRU: evita retraducciones de texto ya procesado
        self._cache: dict[str, str] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        super().__init__("translator", config, is_critical=False)

    def configure(self, config: dict[str, Any]) -> None:
        """
        Update translator configuration and reload translation model if language settings changed.
        Called during pipeline reconfiguration (hot-reload).
        """
        new_source_lang = config.get("source_lang", self._source_lang)
        new_target_lang = config.get("target_lang", self._target_lang)

        # Determine if we should wait for language detection
        new_waiting_for_language = new_source_lang == "auto"

        # Check if we need to reload the translation model
        model_needs_reload = False

        # Case 1: We're not waiting for language and source/target changed
        # Case 2: We were waiting for language but now have a fixed source language
        if (
            not new_waiting_for_language
            and (new_source_lang != self._source_lang or new_target_lang != self._target_lang)
        ) or (self._waiting_for_language and not new_waiting_for_language and new_source_lang != "auto"):
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
            t0 = time.perf_counter()
            import argostranslate.package

            t1 = time.perf_counter()
            logger.info(f"[TIMING] import argostranslate.package: {t1-t0:.3f}s")

            import argostranslate.translate  # noqa: F401

            t2 = time.perf_counter()
            logger.info(f"[TIMING] import argostranslate.translate: {t2-t1:.3f}s")

            self._argos_installed = True

            # Setup Argos packages cache dir if needed
            os.environ["ARGOS_PACKAGES_DIR"] = str((Path(".") / "models" / "argos").resolve())

            # Only load model if not waiting for language (i.e., source_lang is not auto)
            if not self._waiting_for_language:
                t3 = time.perf_counter()
                self._load_model(self._source_lang, self._target_lang)
                t4 = time.perf_counter()
                logger.info(f"[TIMING] _load_model(): {t4-t3:.3f}s")

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

    def _load_model(self, source_lang: str, target_lang: str) -> None:
        """Install package if missing and create translation pipeline using ModelCache."""
        t0 = time.perf_counter()
        import argostranslate.package

        t1 = time.perf_counter()
        logger.info(f"[TIMING] _load_model: re-import package: {t1-t0:.3f}s")
        import argostranslate.translate

        t2 = time.perf_counter()
        logger.info(f"[TIMING] _load_model: re-import translate: {t2-t1:.3f}s")

        # Try to get from cache first
        t3 = time.perf_counter()
        cached_pair = self._model_cache.get_argos_pair(source_lang, target_lang)
        t4 = time.perf_counter()
        logger.info(f"[TIMING] _load_model: get_argos_pair(): {t4-t3:.3f}s")
        if cached_pair:
            self._translation_pipeline = cached_pair
            logger.info(f"Using cached Argos pair: {source_lang}->{target_lang}")
            return

        # Check if installed
        t5 = time.perf_counter()
        installed = argostranslate.package.get_installed_packages()
        t6 = time.perf_counter()
        logger.info(f"[TIMING] _load_model: get_installed_packages(): {t6-t5:.3f}s")
        package_found = False

        for pkg in installed:
            if pkg.from_code == source_lang and pkg.to_code == target_lang:
                package_found = True
                break

        if not package_found:
            msg = f"Downloading translation model for {source_lang} -> {target_lang}... This may take a minute."
            logger.info(msg)
            self.logger.info(msg)  # Broadcast to web UI

            t7 = time.perf_counter()
            argostranslate.package.update_package_index()
            t8 = time.perf_counter()
            logger.info(f"[TIMING] _load_model: update_package_index(): {t8-t7:.3f}s")

            available_packages = argostranslate.package.get_available_packages()
            t9 = time.perf_counter()
            logger.info(f"[TIMING] _load_model: get_available_packages(): {t9-t8:.3f}s")

            target_pkg = next(
                (pkg for pkg in available_packages if pkg.from_code == source_lang and pkg.to_code == target_lang),
                None,
            )

            if target_pkg:
                t10 = time.perf_counter()
                target_pkg.install()
                t11 = time.perf_counter()
                logger.info(f"[TIMING] _load_model: pkg.install(): {t11-t10:.3f}s")
                success_msg = f"Translation model {source_lang}->{target_lang} installed successfully!"
                logger.info(success_msg)
                self.logger.info(success_msg)  # Broadcast to web UI
            else:
                raise ValueError(f"No translation package found from '{source_lang}' to '{target_lang}'")

        # Get the actual translation function
        t12 = time.perf_counter()
        self._translation_pipeline = argostranslate.translate.get_translation_from_codes(source_lang, target_lang)
        t13 = time.perf_counter()
        logger.info(f"[TIMING] _load_model: get_translation_from_codes(): {t13-t12:.3f}s")

    def stop(self) -> None:
        """Cleanup."""
        self._state = ModuleState.STOPPING
        self._translation_pipeline = None
        self._cache.clear()
        self._state = ModuleState.IDLE

    def _translate_cached(self, text: str) -> str:
        """Traduce texto usando cache FIFO para evitar trabajo redundante."""
        key = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
        if key in self._cache:
            self._cache_hits += 1
            return self._cache[key]

        if self._translation_pipeline is None:
            return text
        result = self._translation_pipeline.translate(text)
        self._cache_misses += 1

        # Mantener el cache acotado a _TRANSLATION_CACHE_SIZE entradas (FIFO simple)
        if len(self._cache) >= _TRANSLATION_CACHE_SIZE:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        translated = str(result)
        self._cache[key] = translated
        return translated

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
                    logger.info(f"Translator switched to {self._source_lang} -> {self._target_lang}")

            # Translate full text
            data.translated_text = self._translate_cached(data.transcript)

            # Translate individual segments (useful for precise subtitles)
            if data.transcript_segments:
                translated_segs = []
                for seg in data.transcript_segments:
                    translated_segs.append(
                        {
                            "start": seg["start"],
                            "end": seg["end"],
                            "text": self._translate_cached(seg["text"]),
                        }
                    )
                data.translated_segments = translated_segs

            logger.info(f"Translated: {data.translated_text}")
            hit_rate = round(self._cache_hits / max(1, self._cache_hits + self._cache_misses) * 100, 1)
            logger.debug(
                f"Translation cache hit rate: {hit_rate}% ({self._cache_hits} hits / {self._cache_misses} misses)"
            )

        except Exception as e:
            logger.error(f"Translation error: {e}")

        return data
