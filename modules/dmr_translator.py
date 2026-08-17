"""
DMR Translator Module — translates text via Docker Model Runner (Gemma 4).

Calls the OpenAI-compatible API exposed by Docker Model Runner at
http://localhost:12434/engines/v1/chat/completions using Gemma 4 E4B
with maximum context (128K tokens).

Requires Docker Desktop with Model Runner enabled and the model pulled:
    docker model pull ai/gemma4:E4B
    docker model configure --context-size 131072 ai/gemma4:E4B
"""

import hashlib
import json
import logging
import os
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from core.module_base import BaseModule, ModuleState, PipelineData

logger = logging.getLogger("srt2web.module.dmr_translator")

_TRANSLATION_CACHE_SIZE = 256

DMR_BASE_URL = os.environ.get(
    "SRT2WEB_DMR_URL",
    "http://localhost:12434/engines/v1",
)
DMR_MODEL = os.environ.get(
    "SRT2WEB_DMR_MODEL",
    "ai/gemma4:E4B",
)
DMR_TIMEOUT_S = int(os.environ.get("SRT2WEB_DMR_TIMEOUT", "60"))


def _build_system_prompt(source_lang: str, target_lang: str) -> str:
    return (
        f"You are a professional translator from {source_lang} to {target_lang}. "
        f"Translate the user's text to {target_lang}. "
        "Preserve the original meaning, tone, and formatting. "
        "Return ONLY the translated text, no explanations, no quotes, no metadata."
    )


def _call_dmr(prompt: str, system_prompt: str, max_tokens: int = 4096) -> str:
    """Call DMR OpenAI-compatible chat completions endpoint."""
    payload = json.dumps(
        {
            "model": DMR_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "top_p": 0.3,
        }
    ).encode("utf-8")

    req = Request(
        f"{DMR_BASE_URL}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=DMR_TIMEOUT_S) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        logger.error(f"DMR API call failed: {e}")
        raise ConnectionError(
            f"Cannot reach Docker Model Runner at {DMR_BASE_URL}. "
            f"Ensure Docker Desktop is running with Model Runner enabled."
        ) from e

    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError(f"DMR returned no choices: {result}")

    content: str = str(choices[0].get("message", {}).get("content", ""))
    return content.strip()


class DMRTranslator(BaseModule):
    """
    Translates text segments using Gemma 4 via Docker Model Runner.

    Falls back to passthrough (returns original text) if DMR is unreachable.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._source_lang = config.get("source_lang", "es") if config else "es"
        self._target_lang = config.get("target_lang", "en") if config else "en"
        self._dmr_available = False
        self._dmr_checked = False
        self._cache: dict[str, str] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._max_batch_chars = config.get("max_batch_chars", 2000) if config else 2000
        super().__init__("dmr_translator", config, is_critical=False)

    def configure(self, config: dict[str, Any]) -> None:
        self._source_lang = config.get("source_lang", self._source_lang)
        self._target_lang = config.get("target_lang", self._target_lang)
        self._max_batch_chars = config.get("max_batch_chars", self._max_batch_chars)

    def _check_dmr(self) -> bool:
        """Check if DMR is reachable and the model is available."""
        if self._dmr_checked:
            return self._dmr_available
        self._dmr_checked = True

        try:
            req = Request(f"{DMR_BASE_URL}/models", method="GET")
            with urlopen(req, timeout=5) as resp:
                models = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"DMR not available: {e}")
            self._dmr_available = False
            return False

        model_ids = []
        if isinstance(models, dict):
            data = models.get("data") or models.get("models") or []
            model_ids = [m.get("id", "") for m in data if isinstance(m, dict)]
        elif isinstance(models, list):
            model_ids = [m.get("id", "") for m in models if isinstance(m, dict)]

        available = DMR_MODEL in model_ids or any(DMR_MODEL in m for m in model_ids)
        if not available:
            logger.warning(
                f"Model {DMR_MODEL} not found in DMR. Available: {model_ids[:5]}. Run: docker model pull {DMR_MODEL}"
            )
        self._dmr_available = available
        return available

    def start(self) -> None:
        self._state = ModuleState.STARTING
        available = self._check_dmr()
        if available:
            self._state = ModuleState.RUNNING
            logger.info(
                f"DMRTranslator ready: {self._source_lang} -> {self._target_lang} via {DMR_MODEL} at {DMR_BASE_URL}"
            )
        else:
            self._state = ModuleState.IDLE
            logger.warning("DMRTranslator started in IDLE (DMR unreachable). Translations will passthrough.")

    def stop(self) -> None:
        self._state = ModuleState.STOPPING
        self._cache.clear()
        self._dmr_checked = False
        self._dmr_available = False
        self._state = ModuleState.IDLE

    def _translate_text(self, text: str) -> str:
        """Translate a single text chunk via DMR, with cache."""
        key = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
        if key in self._cache:
            self._cache_hits += 1
            return self._cache[key]

        self._cache_misses += 1

        if not self._dmr_available or not text.strip():
            return text

        try:
            system_prompt = _build_system_prompt(self._source_lang, self._target_lang)
            translated = _call_dmr(text, system_prompt)
        except Exception as e:
            logger.error(f"DMR translation failed: {e}")
            return text

        if len(self._cache) >= _TRANSLATION_CACHE_SIZE:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = translated
        return translated

    def _do_process(self, data: PipelineData) -> PipelineData:
        """Translate transcript using Gemma 4 via DMR."""
        if not data.transcript:
            return data

        # If a previous translator already set translated_text to something
        # different from the original transcript, preserve that work.
        if data.translated_text and data.translated_text != data.transcript:
            logger.debug("DMR: translated_text already present from upstream, skipping")
            return data

        try:
            text = data.transcript
            if len(text) > self._max_batch_chars:
                logger.info(f"Truncating translation from {len(text)} to {self._max_batch_chars} chars")
                text = text[: self._max_batch_chars]

            data.translated_text = self._translate_text(text)

            if data.transcript_segments:
                translated_segs = []
                for seg in data.transcript_segments:
                    translated_segs.append(
                        {
                            "start": seg["start"],
                            "end": seg["end"],
                            "text": self._translate_text(seg["text"]),
                        }
                    )
                data.translated_segments = translated_segs

            logger.info(f"DMR translated ({len(data.translated_text)} chars)")
            hit_rate = round(self._cache_hits / max(1, self._cache_hits + self._cache_misses) * 100, 1)
            logger.debug(
                f"DMR translation cache hit rate: {hit_rate}% ({self._cache_hits} hits / {self._cache_misses} misses)"
            )

        except Exception as e:
            logger.error(f"DMR translation error: {e}")

        return data
