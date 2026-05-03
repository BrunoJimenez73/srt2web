"""
Model Cache - Persistent caching for ML models.

Provides centralized model management for:
- faster-whisper models
- argostranslate language pairs

Models are cached in memory and can be preloaded on startup
to reduce first-chunk latency.
"""

import logging
import os
import threading
from pathlib import Path
from typing import Any, Optional

from core.paths import get_project_root

logger = logging.getLogger("srt2web.model_cache")


class ModelCache:
    """
    Singleton cache for ML models.

    Provides:
    - Model instance caching
    - Preloading on startup
    - Memory management
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._whisper_models: dict[str, Any] = {}
        self._argos_indexes: dict[str, Any] = {}
        self._models_loaded = False
        self._preload_thread: Optional[threading.Thread] = None
        self._preload_done = threading.Event()

        self._cache_dir = self._get_cache_dir()
        logger.info(f"ModelCache initialized (cache_dir: {self._cache_dir})")

    def _get_cache_dir(self) -> Path:
        """Get the cache directory for models."""
        explicit_cache_dir = os.environ.get("SRT2WEB_CACHE_DIR")
        if explicit_cache_dir:
            cache_dir = Path(explicit_cache_dir).expanduser()
            cache_dir.mkdir(parents=True, exist_ok=True)
            return cache_dir

        bases = []
        if os.name == "nt":
            bases.append(Path(os.environ.get("LOCALAPPDATA", Path.home())))
        else:
            bases.append(Path.home())
        bases.append(get_project_root())

        for base in bases:
            cache_dir = base / ".cache" / "srt2web"
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
                return cache_dir
            except OSError as exc:
                logger.warning("Could not use model cache directory %s: %s", cache_dir, exc)

        raise RuntimeError("Could not create a writable model cache directory")

    @property
    def whisper_cache_dir(self) -> Path:
        """Get Whisper model cache directory."""
        d = self._cache_dir / "whisper"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def argos_cache_dir(self) -> Path:
        """Get Argos Translate cache directory."""
        d = self._cache_dir / "argos"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_whisper_model(
        self,
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> Any:
        """
        Get or create a Whisper model instance.

        Args:
            model_size: Model size (tiny, small, medium, large-v2, etc.)
            device: Device to use (cpu, cuda)
            compute_type: Compute type (int8, float16, etc.)

        Returns:
            WhisperModel instance
        """
        cache_key = f"{model_size}_{device}_{compute_type}"

        if cache_key in self._whisper_models:
            logger.debug(f"Using cached Whisper model: {cache_key}")
            return self._whisper_models[cache_key]

        logger.info(f"Loading Whisper model: {cache_key}")

        from faster_whisper import WhisperModel

        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=4,
            download_root=str(self.whisper_cache_dir),
            local_files_only=False,
        )

        self._whisper_models[cache_key] = model
        logger.info(f"Whisper model loaded: {cache_key}")

        return model

    def preload_whisper(
        self,
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        """
        Preload Whisper model in background thread.

        Args:
            model_size: Model to preload
            device: Device to use
            compute_type: Compute type
        """
        if self._models_loaded:
            return

        def _preload():
            try:
                logger.info(f"Preloading Whisper model: {model_size}")
                self.get_whisper_model(model_size, device, compute_type)
                self._models_loaded = True
                self._preload_done.set()
                logger.info("Model preload complete")
            except Exception as e:
                logger.error(f"Model preload failed: {e}")

        self._preload_thread = threading.Thread(
            target=_preload,
            daemon=True,
            name="model-preload",
        )
        self._preload_thread.start()

    def wait_for_preload(self, timeout: float = 60.0) -> bool:
        """
        Wait for model preload to complete.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if preload completed, False if timeout
        """
        return self._preload_done.wait(timeout=timeout)

    def get_argos_pair(
        self,
        source_lang: str,
        target_lang: str,
    ) -> Optional[Any]:
        """
        Get or create Argos Translate translation pair.

        Args:
            source_lang: Source language code (en, es, fr, etc.)
            target_lang: Target language code

        Returns:
            Translation pair instance or None if not available
        """
        cache_key = f"{source_lang}_{target_lang}"

        if cache_key in self._argos_indexes:
            logger.debug(f"Using cached Argos pair: {cache_key}")
            return self._argos_indexes[cache_key]

        logger.info(f"Loading Argos translation pair: {cache_key}")

        try:
            import argostranslate.translate

            # Use the correct API for newer argostranslate versions
            try:
                # Try new API first
                installed_languages = argostranslate.translate.get_installed_languages()
                source = None
                target = None

                for lang in installed_languages:
                    if lang.code == source_lang:
                        source = lang
                    if lang.code == target_lang:
                        target = lang

                    if source and target:
                        break

                if source and target:
                    # Get translation between languages
                    pair = source.get_translation(target)
                    if pair:
                        self._argos_indexes[cache_key] = pair
                        logger.info(f"Argos pair loaded: {cache_key}")
                        return pair

            except Exception as e:
                logger.debug(f"New API failed, trying fallback: {e}")

            # Fallback: use get_translation_from_codes directly
            pair = argostranslate.translate.get_translation_from_codes(source_lang, target_lang)
            if pair:
                self._argos_indexes[cache_key] = pair
                logger.info(f"Argos pair loaded via fallback: {cache_key}")

            return pair

        except ImportError:
            logger.warning("argostranslate not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to load Argos pair {cache_key}: {e}")
            return None

    def preload_argos(self, pairs: list = None) -> None:
        """
        Preload Argos translation pairs.

        Args:
            pairs: List of (source_lang, target_lang) tuples
        """
        if pairs is None:
            pairs = [
                ("en", "es"),
                ("es", "en"),
                ("en", "fr"),
                ("fr", "en"),
            ]

        def _preload():
            for source, target in pairs:
                try:
                    self.get_argos_pair(source, target)
                except Exception as e:
                    logger.error(f"Preload failed for {source}->{target}: {e}")

        thread = threading.Thread(
            target=_preload,
            daemon=True,
            name="argos-preload",
        )
        thread.start()

    def preload_all(
        self,
        whisper_model: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
        argos_pairs: list = None,
    ) -> None:
        """
        Preload all models in background threads.

        Args:
            whisper_model: Whisper model to preload
            device: Device for Whisper
            compute_type: Compute type for Whisper
            argos_pairs: List of (source, target) language pairs
        """
        self.preload_whisper(whisper_model, device, compute_type)
        self.preload_argos(argos_pairs)
        logger.info("All model preload started")

    def clear_cache(self) -> None:
        """Clear all cached models."""
        logger.info("Clearing model cache...")

        self._whisper_models.clear()
        self._argos_indexes.clear()
        self._models_loaded = False
        self._preload_done.clear()

        logger.info("Model cache cleared")

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        total_memory = 0
        try:
            import psutil

            process = psutil.Process()
            total_memory = process.memory_info().rss / 1024 / 1024
        except ImportError:
            pass

        return {
            "whisper_models_loaded": len(self._whisper_models),
            "argos_pairs_loaded": len(self._argos_indexes),
            "models_loaded": self._models_loaded,
            "preload_done": self._preload_done.is_set(),
            "total_memory_mb": round(total_memory, 1),
            "cache_dir": str(self._cache_dir),
        }

    def warm_up(self, config: dict) -> None:
        """
        Warm up models based on configuration.

        This should be called on startup to load models
        before the first chunk arrives.

        Args:
            config: Configuration dict with model settings
        """
        whisper_config = config.get("modules", {}).get("transcriber", {})
        whisper_model = whisper_config.get("model", "tiny")
        device = whisper_config.get("device", "auto")
        compute_type = "int16" if device == "cuda" else "int8"

        if device == "auto":
            try:
                import torch

                if torch.cuda.is_available():
                    device = "cuda"
                    compute_type = "float16"
                else:
                    device = "cpu"
            except ImportError:
                device = "cpu"

        translator_config = config.get("modules", {}).get("translator", {})
        source_lang = translator_config.get("source_lang", "en")
        target_lang = translator_config.get("target_lang", "es")

        self.preload_all(
            whisper_model=whisper_model,
            device=device,
            compute_type=compute_type,
            argos_pairs=[(source_lang, target_lang)],
        )


model_cache = ModelCache()
