"""
Piper TTS Subprocess Manager

Two modes:
1. One-shot loader: load_piper_model_subprocess() - validates model, returns result
2. Persistent worker: PiperSubprocessManager - keeps subprocess alive for synthesis

The persistent worker enables real GPU usage for TTS synthesis because the
subprocess can use CUDA without the cuDNN 8.x symbol loading issues that
crash the main Python process.
"""

import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

logger = logging.getLogger("srt2web.module.tts_engine")

# ──────────────────────────────────────────────────────────────────────
# PERSISTENT WORKER SCRIPT
# Runs in a subprocess, loads Piper with GPU, and handles synthesis
# requests via stdin/stdout JSON IPC.
# ──────────────────────────────────────────────────────────────────────
PERSISTENT_WORKER_SCRIPT = r"""
import sys
import os
import json
import io
import wave
import warnings
import base64

def main():
    voice = None
    using_cuda = False
    sample_rate = 22050

    print("[PERSISTENT] Piper persistent worker started", file=sys.stderr, flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

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
                from piper import PiperVoice
                import onnxruntime

                print(f"[PERSISTENT] Loading model: {model_path}", file=sys.stderr, flush=True)
                print(f"[PERSISTENT] Device: {device}", file=sys.stderr, flush=True)
                print(f"[PERSISTENT] ONNX providers: {onnxruntime.get_available_providers()}",
                      file=sys.stderr, flush=True)

                cuda_ok = "CUDAExecutionProvider" in onnxruntime.get_available_providers()

                # Try CUDA first if requested and available
                if device in ("cuda", "auto") and cuda_ok:
                    try:
                        print("[PERSISTENT] Attempting CUDA load...", file=sys.stderr, flush=True)
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            voice = PiperVoice.load(model_path, config_path, use_cuda=True)
                        using_cuda = True
                        print("[PERSISTENT] CUDA load SUCCESS", file=sys.stderr, flush=True)
                    except Exception as e:
                        print(f"[PERSISTENT] CUDA load failed: {e}", file=sys.stderr, flush=True)
                        voice = None

                # Fallback to CPU
                if voice is None:
                    print("[PERSISTENT] Loading with CPU...", file=sys.stderr, flush=True)
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        voice = PiperVoice.load(model_path, config_path, use_cuda=False)
                    using_cuda = False
                    print("[PERSISTENT] CPU load SUCCESS", file=sys.stderr, flush=True)

                sample_rate = voice.config.sample_rate
                resp = {
                    "status": "success",
                    "using_cuda": using_cuda,
                    "sample_rate": sample_rate,
                    "provider": "CUDAExecutionProvider" if using_cuda else "CPUExecutionProvider"
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
                import struct
                from piper.config import SynthesisConfig

                # Use Piper's native length_scale for speed adjustment
                # length_scale < 1.0 = faster, > 1.0 = slower
                # Piper supports 0.5x to 2.0x natively
                length_scale = 1.0 / speed if speed > 0 else 1.0
                use_piper_speed = 0.5 <= length_scale <= 2.0

                syn_config = SynthesisConfig(
                    length_scale=length_scale if use_piper_speed else 1.0
                )

                # Collect raw audio bytes from Piper
                audio_chunks = []
                for chunk in voice.synthesize(text, syn_config=syn_config):
                    audio_chunks.append(chunk.audio_int16_bytes)

                if not audio_chunks:
                    resp = {"status": "error", "error": "Piper produced no audio"}
                    print(json.dumps(resp), flush=True)
                    continue

                raw_audio = b"".join(audio_chunks)

                # Fallback: numpy resampling for extreme speeds outside Piper range
                if not use_piper_speed and speed != 1.0:
                    try:
                        import numpy as np
                        samples = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float64)
                        new_length = max(1, int(len(samples) / speed))
                        indices = np.linspace(0, len(samples) - 1, new_length)
                        resampled = np.interp(indices, np.arange(len(samples)), samples)
                        raw_audio = np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()
                    except Exception:
                        pass  # Keep original if numpy fails

                # Build WAV header
                data_size = len(raw_audio)
                header = struct.pack(
                    '<4sI4s4sIHHIIHH4sI',
                    b'RIFF', 36 + data_size, b'WAVE',
                    b'fmt ', 16, 1, 1, sample_rate,
                    sample_rate * 2, 2, 16,
                    b'data', data_size
                )
                wav_bytes = header + raw_audio

                audio_b64 = base64.b64encode(wav_bytes).decode("ascii")
                resp = {
                    "status": "success",
                    "audio_base64": audio_b64,
                    "sample_rate": sample_rate
                }
            except Exception as e:
                trace = traceback.format_exc()
                print(f"[PERSISTENT] Error during synthesis: {trace}", file=sys.stderr, flush=True)
                resp = {"status": "error", "error": str(e), "traceback": trace}

            print(json.dumps(resp), flush=True)

        # ── SHUTDOWN ──────────────────────────────────────────
        elif action == "shutdown":
            print("[PERSISTENT] Shutting down", file=sys.stderr, flush=True)
            print(json.dumps({"status": "success"}), flush=True)
            break

        # ── UNKNOWN ───────────────────────────────────────────
        else:
            resp = {"status": "error", "error": f"Unknown action: {action}"}
            print(json.dumps(resp), flush=True)

    print("[PERSISTENT] Worker exited", file=sys.stderr, flush=True)

if __name__ == "__main__":
    main()
"""


# ──────────────────────────────────────────────────────────────────────
# PERSISTENT SUBPROCESS MANAGER
# ──────────────────────────────────────────────────────────────────────
class PiperSubprocessManager:
    """
    Manages a persistent Piper subprocess with GPU support.

    The subprocess stays alive and handles multiple synthesis requests
    via stdin/stdout JSON IPC. This enables real GPU usage because the
    subprocess doesn't have the cuDNN 8.x symbol loading issues that
    affect the main Python process.
    """

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._script_path: str | None = None
        self._lock = threading.Lock()
        self._using_cuda = False
        self._sample_rate = 22050
        self._model_loaded = False

    @property
    def using_cuda(self) -> bool:
        return self._using_cuda

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, model_path: str, config_path: str, device: str = "auto") -> dict:
        """
        Start the persistent subprocess and load the model.

        Returns:
            dict with status, using_cuda, sample_rate, provider
        """
        with self._lock:
            self._ensure_stopped()

            # Write worker script to temp file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(PERSISTENT_WORKER_SCRIPT)
                self._script_path = f.name

            # Build environment with CUDA paths and FFmpeg
            env = os.environ.copy()
            import site

            cuda_paths = []
            for sp in site.getsitepackages():
                for subdir in ("nvidia/cudnn/bin", "nvidia/cublas_cu11/bin"):
                    p = Path(sp) / subdir
                    if p.exists():
                        cuda_paths.append(str(p))
            if cuda_paths:
                # os.pathsep is the path separator (e.g., ';' on Windows, ':' on Linux)
                env["PATH"] = os.pathsep.join(cuda_paths) + os.pathsep + env.get("PATH", "")

            # Pass FFmpeg path for speed adjustment
            try:
                from core.ffmpeg_utils import ensure_ffmpeg

                ffmpeg_path = ensure_ffmpeg()
                env["FFMPEG_PATH"] = ffmpeg_path
            except Exception:
                pass

            logger.info("[PiperManager] Starting persistent subprocess...")

            # Start the subprocess
            self._proc = subprocess.Popen(
                [sys.executable, self._script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                env=env,
                creationflags=(subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0),
            )

            # Start stderr reader thread (prevents deadlock)
            self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True, name="piper-stderr")
            self._stderr_thread.start()

            # Send load command
            load_cmd = {
                "action": "load",
                "model_path": model_path,
                "config_path": config_path,
                "device": device,
            }

            logger.info(f"[PiperManager] Loading model: {os.path.basename(model_path)}")
            resp = self._send_command(load_cmd, timeout=90)

            if resp.get("status") == "success":
                self._using_cuda = resp.get("using_cuda", False)
                self._sample_rate = resp.get("sample_rate", 22050)
                self._model_loaded = True
                provider = resp.get("provider", "unknown")
                logger.info(
                    f"[PiperManager] Model loaded: CUDA={self._using_cuda}, "
                    f"sample_rate={self._sample_rate}, provider={provider}"
                )
            else:
                self._model_loaded = False
                logger.error(f"[PiperManager] Load failed: {resp.get('error', 'unknown')}")

            return resp

    def synthesize(self, text: str, speed: float = 1.0, timeout: float = 30.0) -> bytes | None:
        """
        Synthesize text to audio WAV bytes.

        Returns:
            WAV bytes, or None if synthesis failed
        """
        if not self._model_loaded or not self.is_alive:
            logger.error("[PiperManager] Cannot synthesize: model not loaded or subprocess dead")
            return None

        cmd = {
            "action": "synthesize",
            "text": text,
            "speed": speed,
        }

        resp = self._send_command(cmd, timeout=timeout)

        if resp.get("status") == "success":
            audio_b64 = resp.get("audio_base64", "")
            if audio_b64:
                return base64.b64decode(audio_b64)
        else:
            logger.error(f"[PiperManager] Synthesis failed: {resp.get('error', 'unknown')}")

        return None

    def stop(self):
        """Stop the persistent subprocess."""
        with self._lock:
            self._ensure_stopped()

    def _send_command(self, cmd: dict, timeout: float = 30.0) -> dict:
        """Send a command and wait for response."""
        if not self._proc or not self._proc.stdin or not self._proc.stdout:
            return {"status": "error", "error": "Subprocess not running"}

        try:
            # Send command
            cmd_json = json.dumps(cmd) + "\n"
            self._proc.stdin.write(cmd_json)
            self._proc.stdin.flush()

            # Read response with timeout
            import select

            if sys.platform == "win32":
                # Windows: use threading timer
                response_line = [None]
                read_error = [None]

                def read_line():
                    try:
                        response_line[0] = self._proc.stdout.readline()
                    except Exception as e:
                        read_error[0] = e

                t = threading.Thread(target=read_line)
                t.start()
                t.join(timeout=timeout)

                if t.is_alive():
                    logger.error(f"[PiperManager] Command timed out after {timeout}s")
                    return {"status": "error", "error": f"Timeout after {timeout}s"}

                if read_error[0]:
                    return {"status": "error", "error": str(read_error[0])}

                line = response_line[0]
            else:
                # Unix: use select
                ready, _, _ = select.select([self._proc.stdout], [], [], timeout)
                if not ready:
                    return {"status": "error", "error": f"Timeout after {timeout}s"}
                line = self._proc.stdout.readline()

            if not line or not line.strip():
                return {"status": "error", "error": "Empty response from subprocess"}

            return json.loads(line.strip())

        except json.JSONDecodeError as e:
            return {"status": "error", "error": f"Invalid JSON response: {e}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _read_stderr(self):
        """Read stderr in background thread to prevent deadlock."""
        if not self._proc or not self._proc.stderr:
            return
        try:
            for line in self._proc.stderr:
                line = line.strip()
                if line:
                    logger.info(f"[PiperGPU] {line}")
        except Exception:
            pass

    def _ensure_stopped(self):
        """Stop subprocess if running (must be called with lock held).

        The persistent Piper worker communicates via a JSON line protocol on
        ``stdin``/``stdout``.  When we request a graceful shutdown we must also
        consume the JSON response that the worker writes before it exits.  If we
        ignore that response the worker can block on a full stdout pipe, leaving
        the subprocess alive and causing the test suite to hang.
        """
        if self._proc:
            try:
                # Try graceful shutdown: send the ``shutdown`` command and read the response.
                if self._proc.stdin:
                    try:
                        shutdown_cmd = json.dumps({"action": "shutdown"}) + "\n"
                        self._proc.stdin.write(shutdown_cmd)
                        self._proc.stdin.flush()
                        # Read the JSON response (if any) to unblock the worker.
                        if self._proc.stdout:
                            # Use a short timeout to avoid hanging indefinitely.
                            try:
                                # ``select`` works on Unix; on Windows we fall back to a thread read.
                                if sys.platform != "win32":
                                    import select

                                    ready, _, _ = select.select([self._proc.stdout], [], [], 3)
                                    if ready:
                                        self._proc.stdout.readline()
                                else:
                                    # Windows: read in a separate thread with timeout.
                                    response_line = [None]

                                    def _read():
                                        try:
                                            response_line[0] = self._proc.stdout.readline()
                                        except Exception:
                                            pass

                                    t = threading.Thread(target=_read)
                                    t.start()
                                    t.join(3)
                            except Exception:
                                # If reading fails we still attempt to wait for termination.
                                pass
                        # Wait for the process to exit gracefully.
                        self._proc.wait(timeout=3)
                    except Exception:
                        # If anything goes wrong we fall back to force‑kill.
                        pass

                # Force kill if still running after graceful attempt.
                if self._proc.poll() is None:
                    if sys.platform == "win32":
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(self._proc.pid)],
                            capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                    else:
                        self._proc.kill()
                    # Ensure the process is reaped.
                    self._proc.wait(timeout=5)
            except Exception as e:
                logger.debug(f"[PiperManager] Cleanup: {e}")
            finally:
                # Close any open pipes to avoid resource leaks.
                try:
                    if self._proc.stdin:
                        self._proc.stdin.close()
                except Exception:
                    pass
                try:
                    if self._proc.stdout:
                        self._proc.stdout.close()
                except Exception:
                    pass
                try:
                    if self._proc.stderr:
                        self._proc.stderr.close()
                except Exception:
                    pass
                self._proc = None

        # Clean up the temporary worker script file.
        if self._script_path:
            try:
                os.unlink(self._script_path)
            except OSError:
                pass
            self._script_path = None

        # Reset internal state flags.
        self._model_loaded = False
        self._using_cuda = False


# ──────────────────────────────────────────────────────────────────────
# ONE-SHOT LOADER (existing functionality, kept for compatibility)
# ──────────────────────────────────────────────────────────────────────
LOADER_SCRIPT = '''
import sys
import os
import json
import warnings

def main():
    """Load Piper model and report results."""
    try:
        voice_name = sys.argv[1]
        model_path = sys.argv[2]
        config_path = sys.argv[3]
        device = sys.argv[4]

        from piper import PiperVoice
        import onnxruntime

        print(f"[PIPER_DEBUG] Python: {sys.version}", file=sys.stderr)
        print(f"[PIPER_DEBUG] ONNX Runtime: {onnxruntime.__version__}", file=sys.stderr)
        print(f"[PIPER_DEBUG] Available providers: {onnxruntime.get_available_providers()}", file=sys.stderr)
        print(f"[PIPER_DEBUG] Model path: {model_path}", file=sys.stderr)
        print(f"[PIPER_DEBUG] Config path: {config_path}", file=sys.stderr)
        print(f"[PIPER_DEBUG] Device requested: {device}", file=sys.stderr)

        cuda_available = "CUDAExecutionProvider" in onnxruntime.get_available_providers()
        print(f"[PIPER_DEBUG] CUDA available: {cuda_available}", file=sys.stderr)

        use_cuda = False
        voice = None

        if device == "cuda" or (device == "auto" and cuda_available):
            if cuda_available:
                try:
                    print(f"[PIPER_DEBUG] Attempting to load with CUDA...", file=sys.stderr)
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        voice = PiperVoice.load(model_path, config_path, use_cuda=True)
                    use_cuda = True
                    print(f"[PIPER_DEBUG] Successfully loaded with CUDA", file=sys.stderr)
                except Exception as e:
                    print(f"[PIPER_DEBUG] CUDA load failed: {e}", file=sys.stderr)
                    voice = None
            else:
                print(f"[PIPER_DEBUG] CUDA requested but not available", file=sys.stderr)

        if voice is None:
            print(f"[PIPER_DEBUG] Loading with CPU...", file=sys.stderr)
            voice = PiperVoice.load(model_path, config_path, use_cuda=False)
            use_cuda = False
            print(f"[PIPER_DEBUG] Successfully loaded with CPU", file=sys.stderr)

        print(f"[PIPER_DEBUG] Sample rate: {voice.config.sample_rate}", file=sys.stderr)

        result = {
            "status": "success",
            "using_cuda": use_cuda,
            "sample_rate": voice.config.sample_rate,
            "provider": "CUDAExecutionProvider" if use_cuda else "CPUExecutionProvider"
        }
        print(json.dumps(result))

    except ImportError as e:
        result = {"status": "error", "error": f"Import error: {e}"}
        print(json.dumps(result))
        sys.exit(1)
    except Exception as e:
        result = {"status": "error", "error": str(e)}
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
'''


def load_piper_model_subprocess(
    voice_name: str, model_path: str, config_path: str, device: str = "auto", timeout: int = 90
) -> dict:
    """
    Load Piper model in a one-shot subprocess (validates model works).

    Returns:
        dict with keys: status, using_cuda, sample_rate, provider, error
    """
    start_time = time.time()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(LOADER_SCRIPT)
        script_path = f.name

    try:
        logger.info(f"[PIPER_DEBUG] Starting subprocess loader for {voice_name}")
        logger.info(f"[PIPER_DEBUG] Timeout: {timeout}s, Device: {device}")

        import site

        env = os.environ.copy()
        cuda_paths = []

        for sp in site.getsitepackages():
            cudnn_bin = os.path.join(sp, "nvidia", "cudnn", "bin")
            if os.path.exists(cudnn_bin):
                cuda_paths.append(cudnn_bin)
            cublas_bin = os.path.join(sp, "nvidia", "cublas_cu11", "bin")
            if os.path.exists(cublas_bin):
                cuda_paths.append(cublas_bin)

        if cuda_paths:
            env["PATH"] = os.pathsep.join(cuda_paths) + os.pathsep + env.get("PATH", "")
            logger.info(f"[PIPER_DEBUG] CUDA paths set to: {cuda_paths}")

        result = subprocess.run(
            [sys.executable, script_path, voice_name, model_path, config_path, device],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )

        elapsed = time.time() - start_time
        logger.info(f"[PIPER_DEBUG] Subprocess finished after {elapsed:.1f}s")

        stderr_lines = []
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                if line.strip():
                    stderr_lines.append(line.strip())
                    logger.info(f"[PIPER_DEBUG] {line.strip()}")

        cuda_error_detected = False
        for line in stderr_lines:
            if "cublas" in line.lower() or "cudnn" in line.lower():
                cuda_error_detected = True

        if result.returncode != 0:
            logger.error(f"[PIPER_DEBUG] Subprocess failed with code {result.returncode}")
            error_msg = f"Process exited with code {result.returncode}"
            if cuda_error_detected:
                error_msg += " (CUDA dependencies missing)"
            return {"status": "error", "error": error_msg}

        try:
            stdout = result.stdout.strip()
            json_start = stdout.find("{")
            if json_start >= 0:
                data = json.loads(stdout[json_start:])
            else:
                data = json.loads(stdout)
            logger.info(f"[PIPER_DEBUG] Load result: {data}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"[PIPER_DEBUG] Failed to parse JSON: {e}")
            return {"status": "error", "error": f"Failed to parse result: {e}"}

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        logger.error(f"[PIPER_DEBUG] Subprocess timed out after {elapsed:.1f}s")
        return {"status": "error", "error": f"Loading timed out after {timeout} seconds"}
    except Exception as e:
        logger.error(f"[PIPER_DEBUG] Unexpected error: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


def check_piper_environment() -> dict:
    """Check if piper and onnxruntime are available, report versions."""
    result = {
        "piper_available": False,
        "onnxruntime_available": False,
        "onnx_version": None,
        "providers": [],
        "cuda_available": False,
        "python_path": sys.executable,
        "python_version": sys.version,
    }

    try:
        import piper

        result["piper_available"] = True
    except ImportError as e:
        result["piper_error"] = str(e)

    try:
        import onnxruntime as ort

        result["onnxruntime_available"] = True
        result["onnx_version"] = ort.__version__
        result["providers"] = ort.get_available_providers()
        result["cuda_available"] = "CUDAExecutionProvider" in result["providers"]
    except ImportError as e:
        result["onnx_error"] = str(e)

    return result
