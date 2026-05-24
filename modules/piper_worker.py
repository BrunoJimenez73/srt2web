"""
Piper TTS persistent worker — runs in a subprocess.

Loads a Piper model once and handles synthesis requests via stdin/stdout
JSON IPC.  Keeps the subprocess alive for multiple requests so that GPU
memory stays allocated and avoids repeated model-load overhead.

Usage::

    python -m modules.piper_worker
"""

import base64
import json
import logging
import struct
import sys
import traceback
import warnings
from typing import Any

logger = logging.getLogger("srt2web.piper_worker")


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _resample_numpy(raw_audio: bytes, speed: float) -> bytes | None:
    try:
        import numpy as np

        samples = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float64)
        new_length = max(1, int(len(samples) / speed))
        indices = np.linspace(0, len(samples) - 1, new_length)
        resampled = np.interp(indices, np.arange(len(samples)), samples)
        return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()
    except Exception as e:
        _log(f"[PERSISTENT] Numpy resample failed: {e}")
        return None


def _build_wav(raw_audio: bytes, sample_rate: int) -> bytes:
    data_size = len(raw_audio)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    return header + raw_audio


def main() -> None:
    voice: Any = None
    using_cuda = False
    sample_rate = 22050

    _log("[PERSISTENT] Piper persistent worker started")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        resp: dict[str, Any]
        try:
            cmd = json.loads(line)
        except json.JSONDecodeError:
            resp = {"status": "error", "error": f"Invalid JSON: {line[:100]}"}
            print(json.dumps(resp), flush=True)
            continue

        action = cmd.get("action", "")

        # ── LOAD ──────────────────────────────────────────────
        if action == "load":
            model_path = cmd.get("model_path", "")
            config_path = cmd.get("config_path", "")
            device = cmd.get("device", "auto")

            try:
                import onnxruntime
                from piper import PiperVoice

                _log(f"[PERSISTENT] Loading model: {model_path}")
                _log(f"[PERSISTENT] Device: {device}")
                _log(f"[PERSISTENT] ONNX providers: {onnxruntime.get_available_providers()}")

                cuda_ok = "CUDAExecutionProvider" in onnxruntime.get_available_providers()

                # Try CUDA first if requested and available
                if device in ("cuda", "auto") and cuda_ok:
                    try:
                        _log("[PERSISTENT] Attempting CUDA load...")
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            voice = PiperVoice.load(model_path, config_path, use_cuda=True)
                        using_cuda = True
                        _log("[PERSISTENT] CUDA load SUCCESS")
                    except Exception as e:
                        _log(f"[PERSISTENT] CUDA load failed: {e}")
                        voice = None

                # Fallback to CPU
                if voice is None:
                    _log("[PERSISTENT] Loading with CPU...")
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        voice = PiperVoice.load(model_path, config_path, use_cuda=False)
                    using_cuda = False
                    _log("[PERSISTENT] CPU load SUCCESS")

                sample_rate = voice.config.sample_rate
                resp = {
                    "status": "success",
                    "using_cuda": using_cuda,
                    "sample_rate": sample_rate,
                    "provider": "CUDAExecutionProvider" if using_cuda else "CPUExecutionProvider",
                }
            except Exception as e:
                resp = {"status": "error", "error": str(e)}

            print(json.dumps(resp), flush=True)

        # ── SYNTHESIZE ────────────────────────────────────────
        elif action == "synthesize":
            if voice is None:
                resp = {"status": "error", "error": "Voice not loaded"}
                print(json.dumps(resp), flush=True)
                continue

            text = cmd.get("text", "")
            speed = float(cmd.get("speed", 1.0))

            try:
                from piper.config import SynthesisConfig

                # Use Piper's native length_scale for speed adjustment
                length_scale = 1.0 / speed if speed > 0 else 1.0
                use_piper_speed = 0.5 <= length_scale <= 2.0

                syn_config = SynthesisConfig(length_scale=length_scale if use_piper_speed else 1.0)

                # Collect raw audio bytes from Piper
                audio_chunks: list[bytes] = []
                for chunk in voice.synthesize(text, syn_config=syn_config):
                    audio_chunks.append(chunk.audio_int16_bytes)

                if not audio_chunks:
                    resp = {"status": "error", "error": "Piper produced no audio"}
                    print(json.dumps(resp), flush=True)
                    continue

                raw_audio = b"".join(audio_chunks)

                # Fallback: numpy resampling for extreme speeds outside Piper range
                if not use_piper_speed and speed != 1.0:
                    resampled = _resample_numpy(raw_audio, speed)
                    if resampled is not None:
                        raw_audio = resampled

                wav_bytes = _build_wav(raw_audio, sample_rate)

                audio_b64 = base64.b64encode(wav_bytes).decode("ascii")
                resp = {
                    "status": "success",
                    "audio_base64": audio_b64,
                    "sample_rate": sample_rate,
                }
            except Exception as e:
                trace = traceback.format_exc()
                _log(f"[PERSISTENT] Error during synthesis: {trace}")
                resp = {"status": "error", "error": str(e), "traceback": trace}

            print(json.dumps(resp), flush=True)

        # ── PING (heartbeat) ──────────────────────────────────
        elif action == "ping":
            print(json.dumps({"status": "success", "action": "pong"}), flush=True)

        # ── SHUTDOWN ──────────────────────────────────────────
        elif action == "shutdown":
            _log("[PERSISTENT] Shutting down")
            print(json.dumps({"status": "success"}), flush=True)
            break

        # ── UNKNOWN ───────────────────────────────────────────
        else:
            resp = {"status": "error", "error": f"Unknown action: {action}"}
            print(json.dumps(resp), flush=True)

    _log("[PERSISTENT] Worker exited")


if __name__ == "__main__":
    main()
