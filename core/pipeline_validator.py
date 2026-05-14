"""
Pipeline Validator - Validación de calidad en cada etapa del pipeline de SRT.

Cada validador recibe el PipelineData de la etapa anterior y verifica
que cumpla con umbrales de calidad configurables. Si no pasa, el orquestador
decide si reintentar, degradar o detener el pipeline.
"""

import logging
import os
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any, Optional

import numpy as np

from core.module_base import PipelineData
from core.config_schema import PipelineValidationConfig

logger = logging.getLogger("srt2web.pipeline_validator")


@dataclass
class ValidationResult:
    """Resultado de una validación de etapa."""

    stage: str
    passed: bool
    score: float = 1.0  # 0.0 - 1.0
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    is_critical: bool = False  # Si true, fallo = pipeline stop

    @property
    def emoji(self) -> str:
        return "✅" if self.passed else "❌" if self.is_critical else "⚠️"


class AudioValidator:
    """Valida la salida de AudioExtractor."""

    def validate(self, data: PipelineData, config: Optional[dict[str, Any]] = None) -> ValidationResult:
        cfg: dict[str, Any] = config or {}
        min_sr = cfg.get("min_sample_rate", 8000)
        max_dur_ratio = cfg.get("max_duration_ratio", 1.5)

        audio_path = data.audio_chunk_path or data.dubbed_audio_path
        if not audio_path or not os.path.exists(audio_path):
            return ValidationResult(stage="audio_extractor", passed=True,
                                    message="No audio path to validate (passthrough mode)")

        size = os.path.getsize(audio_path)
        details = {"path": audio_path, "size_bytes": size}

        if size < 44:  # WAV header minimum
            return ValidationResult(stage="audio_extractor", passed=False, score=0.0,
                                    message="Audio file too small (may be corrupt)", details=details)

        if data.duration and data.duration > 0:
            expected = config.get("expected_duration", data.duration) if config else data.duration
            ratio = data.duration / max(expected, 0.001)
            details["duration_ratio"] = round(ratio, 2)
            if ratio > max_dur_ratio or ratio < 0.1:
                return ValidationResult(stage="audio_extractor", passed=False, score=0.3,
                                        message=f"Duration ratio {ratio:.2f} outside expected range",
                                        details=details)

        return ValidationResult(stage="audio_extractor", passed=True, score=1.0,
                                message="Audio OK", details=details)


class TranscriptValidator:
    """Valida la salida de Transcriber (Whisper)."""

    def validate(self, data: PipelineData, config: Optional[dict[str, Any]] = None) -> ValidationResult:
        cfg: dict[str, Any] = config or {}
        min_conf = cfg.get("min_confidence", 0.3)
        min_segs = cfg.get("min_segments", 1)

        segments = data.transcript_segments or []
        text = (data.transcript or "").strip()
        details = {"segments": len(segments), "text_length": len(text)}

        if not text and not segments:
            return ValidationResult(stage="transcriber", passed=False, score=0.0,
                                    message="No transcript generated (empty)", details=details,
                                    is_critical=False)

        if segments:
            confidences = [s.get("confidence", 1.0) for s in segments if "confidence" in s]
            if confidences:
                avg_conf = sum(confidences) / len(confidences)
                details["avg_confidence"] = round(avg_conf, 3)
                if avg_conf < min_conf:
                    return ValidationResult(stage="transcriber", passed=False, score=avg_conf,
                                            message=f"Low confidence: {avg_conf:.2f} < {min_conf}",
                                            details=details)

        return ValidationResult(stage="transcriber", passed=True, score=1.0,
                                message=f"Transcription OK ({len(segments)} segments)", details=details)


class TranslationValidator:
    """Valida la salida de Translator."""

    def validate(self, data: PipelineData, config: Optional[dict[str, Any]] = None) -> ValidationResult:
        cfg: dict[str, Any] = config or {}
        max_empty_ratio = cfg.get("max_empty_ratio", 0.9)
        min_length_change = cfg.get("min_length_change", 0.0)

        translated = (data.translated_text or "").strip()
        original = (data.transcript or "").strip()
        details = {"original_length": len(original), "translated_length": len(translated)}

        if not translated:
            return ValidationResult(stage="translator", passed=False, score=0.0,
                                    message="No translation generated", details=details,
                                    is_critical=False)

        if original and len(translated) < len(original) * (1 - max_empty_ratio):
            return ValidationResult(stage="translator", passed=False, score=0.3,
                                    message="Translation too short relative to original",
                                    details=details)

        return ValidationResult(stage="translator", passed=True, score=1.0,
                                message=f"Translation OK ({len(translated)} chars)", details=details)


class TTSValidator:
    """Valida la salida de TTS Engine."""

    def validate(self, data: PipelineData, config: Optional[dict[str, Any]] = None) -> ValidationResult:
        cfg: dict[str, Any] = config or {}
        max_gen_time = cfg.get("max_generation_time", 30.0)

        tts_path = data.dubbed_audio_path
        details: dict[str, Any] = {}

        if not tts_path or not os.path.exists(tts_path):
            return ValidationResult(stage="tts_engine", passed=True, score=1.0,
                                    message="TTS disabled or no audio path", details=details)

        size = os.path.getsize(tts_path)
        details["size_bytes"] = size

        if size < 100:
            return ValidationResult(stage="tts_engine", passed=False, score=0.3,
                                    message=f"TTS audio too small: {size} bytes", details=details)

        return ValidationResult(stage="tts_engine", passed=True, score=1.0,
                                message=f"TTS OK ({size / 1024:.1f} KB)", details=details)


class MixValidator:
    """Valida la salida de AudioMixer."""

    def validate(self, data: PipelineData, config: Optional[dict[str, Any]] = None) -> ValidationResult:
        mixed_path = data.mixed_audio_path
        details: dict[str, Any] = {}

        if not mixed_path or not os.path.exists(mixed_path):
            return ValidationResult(stage="audio_mixer", passed=True, score=1.0,
                                    message="Mix disabled or no path", details=details)

        size = os.path.getsize(mixed_path)
        details["size_bytes"] = size

        if size < 100:
            return ValidationResult(stage="audio_mixer", passed=False, score=0.3,
                                    message=f"Mixed audio too small: {size} bytes", details=details)

        return ValidationResult(stage="audio_mixer", passed=True, score=1.0,
                                message=f"Mix OK ({size / 1024:.1f} KB)", details=details)


class PipelineValidator:
    """
    Orquestador de validaciones. Corre el validador adecuado según la etapa.

    Uso:
        validator = PipelineValidator()
        result = validator.validate(data, "transcriber")
        if not result.passed:
            logger.warning(f"Stage {result.stage}: {result.message}")
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self._config: dict[str, Any] = config or {}
        self._validators: dict[str, Any] = {
            "audio_extractor": AudioValidator(),
            "transcriber": TranscriptValidator(),
            "translator": TranslationValidator(),
            "tts_engine": TTSValidator(),
            "audio_mixer": MixValidator(),
        }

    def validate(self, data: PipelineData, stage: str) -> ValidationResult:
        """Run validation for a specific pipeline stage."""
        validator = self._validators.get(stage)
        if validator is None:
            return ValidationResult(stage=stage, passed=True, message=f"No validator for {stage}")
        if not hasattr(validator, "validate"):
            return ValidationResult(stage=stage, passed=True, message=f"Validator has no validate method")

        stage_config: dict[str, Any] = self._config.get(stage, {})
        fn: Callable[..., ValidationResult] = validator.validate
        result = fn(data, stage_config)

        if not result.passed and stage_config.get("enabled", True):
            logger.warning(f"[VALIDATOR] {result.emoji} {stage}: {result.message} (score={result.score:.2f})")
        else:
            logger.debug(f"[VALIDATOR] {result.emoji} {stage}: {result.message}")

        return result

    def validate_all(self, data: PipelineData, active_stages: Optional[list[str]] = None) -> list[ValidationResult]:
        """Run all applicable validators."""
        stages = active_stages or list(self._validators.keys())
        results = []
        for stage in stages:
            result = self.validate(data, stage)
            results.append(result)
        return results

    def should_continue(self, result: ValidationResult) -> bool:
        """Decide if pipeline should continue after a validation failure."""
        if result.is_critical and not result.passed:
            return False
        if not result.passed and result.score < 0.2:
            return False  # Very low score = stop even for non-critical
        return True
