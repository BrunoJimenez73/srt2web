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
import contextlib
import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from core.subprocess_utils import get_creation_flags

logger = logging.getLogger("srt2web.module.tts_engine")

# Path to the external worker scripts
_MODULES_DIR = Path(__file__).parent
_PERSISTENT_WORKER_PATH = _MODULES_DIR / "piper_worker.py"
_LOADER_SCRIPT_PATH = _MODULES_DIR / "piper_loader_script.py"

_PERSISTENT_WORKER_SCRIPT_CACHE: str | None = None


def PERSISTENT_WORKER_SCRIPT() -> str:
    """Lazy-load the worker script content.

    Avoids crash at import time if the file is missing.  Backward-compatible
    callable — tests access this via ``from modules.piper_loader import
    PERSISTENT_WORKER_SCRIPT`` and then call it.
    """
    global _PERSISTENT_WORKER_SCRIPT_CACHE
    if _PERSISTENT_WORKER_SCRIPT_CACHE is None:
        try:
            _PERSISTENT_WORKER_SCRIPT_CACHE = _PERSISTENT_WORKER_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("Piper worker script not found at %s", _PERSISTENT_WORKER_PATH)
            _PERSISTENT_WORKER_SCRIPT_CACHE = ""
    return _PERSISTENT_WORKER_SCRIPT_CACHE


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

    HEARTBEAT_INTERVAL = 30  # seconds
    HEARTBEAT_TIMEOUT = 5  # seconds

    MAX_RESTART_ATTEMPTS = 3

    def __init__(self) -> None:
        self._proc: subprocess.Popen[Any] | None = None
        self._script_path: str | None = None
        self._lock = threading.Lock()
        # Serializes concurrent calls to ``_send_command`` (synth + heartbeat).
        # Without this, two threads can race on ``proc.stdout.readline()`` and
        # receive concatenated or split JSON lines, causing ``"Invalid JSON
        # response: Extra data"`` parse errors that look like subprocess crashes.
        # See F106.
        self._cmd_lock = threading.Lock()
        self._using_cuda = False
        self._sample_rate = 22050
        self._model_loaded = False
        self._last_heartbeat_ok = True
        self._heartbeat_interval = 30.0
        self._heartbeat_timeout = 5.0
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_stop = threading.Event()
        self._restart_count = 0

    @property
    def using_cuda(self) -> bool:
        return self._using_cuda

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, model_path: str, config_path: str, device: str = "auto") -> dict[str, Any]:
        """
        Start the persistent subprocess and load the model.

        Returns:
            dict with status, using_cuda, sample_rate, provider
        """
        with self._lock:
            self._ensure_stopped()

            # Store paths for restart
            self._last_model_path = model_path
            self._last_config_path = config_path
            self._last_device = device

            # Use the external worker script
            if not _PERSISTENT_WORKER_PATH.exists():
                raise FileNotFoundError(f"Piper worker script not found: {_PERSISTENT_WORKER_PATH}")
            self._script_path = str(_PERSISTENT_WORKER_PATH)

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
            except Exception as e:
                logger.debug("Suppressed error: %s", e, exc_info=True)

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
                creationflags=get_creation_flags(),
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
                self._last_model_path = model_path
                self._last_config_path = config_path
                self._last_device = device
                provider = resp.get("provider", "unknown")
                logger.info(
                    f"[PiperManager] Model loaded: CUDA={self._using_cuda}, "
                    f"sample_rate={self._sample_rate}, provider={provider}"
                )
                self._restart_count = 0  # Reset on successful load
                self.start_heartbeat()
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

    def stop(self) -> None:
        """Stop the persistent subprocess."""
        self.stop_heartbeat()
        with self._lock:
            self._ensure_stopped()

    def start_heartbeat(self) -> None:
        """Start heartbeat thread that pings the subprocess every 30s."""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="piper-heartbeat",
        )
        self._heartbeat_thread.start()
        logger.info("[PiperManager] Heartbeat thread started")

    def stop_heartbeat(self) -> None:
        """Stop the heartbeat thread."""
        self._heartbeat_stop.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5.0)
        self._heartbeat_thread = None

    def _heartbeat_loop(self) -> None:
        """Periodically ping subprocess and restart if unresponsive."""
        while not self._heartbeat_stop.is_set():
            self._heartbeat_stop.wait(timeout=self._heartbeat_interval)
            if self._heartbeat_stop.is_set():
                break
            if not self.is_alive:
                logger.warning("[PiperManager] Heartbeat: subprocess not alive, attempting restart")
                self._restart_subprocess()
                continue
            try:
                resp = self._send_command({"action": "ping"}, timeout=self._heartbeat_timeout)
                if resp.get("status") != "success":
                    logger.warning(f"[PiperManager] Heartbeat: unexpected response {resp}, restarting")
                    self._restart_subprocess()
            except Exception as e:
                logger.error(f"[PiperManager] Heartbeat: ping failed ({e}), restarting subprocess")
                self._restart_subprocess()

    def _restart_subprocess(self) -> None:
        """Restart the subprocess (reload model from scratch).

        NOTE: must NOT call ``self.start()`` inside ``self._lock`` because
        ``start()`` also acquires ``self._lock``, causing a deadlock on
        a non-reentrant ``threading.Lock`` (ROB-02).
        """
        with self._lock:
            self._restart_count += 1
        logger.warning(
            f"[PiperManager] Restarting subprocess (attempt {self._restart_count}/{self.MAX_RESTART_ATTEMPTS})..."
        )
        with self._lock:
            model_path = getattr(self, "_last_model_path", None)
            config_path = getattr(self, "_last_config_path", None)
            device = getattr(self, "_last_device", "auto")
            # Downgrade to CPU after max restart attempts
            if self._restart_count > self.MAX_RESTART_ATTEMPTS:
                logger.warning("[PiperManager] Max restarts reached, forcing CPU fallback")
                device = "cpu"
                self._restart_count = 0
            self._ensure_stopped()
        # Lock released before calling start() to avoid deadlock (ROB-02)
        if model_path and config_path:
            try:
                self.start(model_path, config_path, device)
                if device == "cpu":
                    logger.info("[PiperManager] Subprocess restarted on CPU")
                else:
                    logger.info("[PiperManager] Subprocess restarted successfully")
            except Exception as e:
                logger.error(f"[PiperManager] Restart failed: {e}")

    def _send_command(self, cmd: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
        """Send a command and wait for response.

        All calls are serialized through ``self._cmd_lock`` so that concurrent
        callers (e.g. a synth request and the heartbeat thread) cannot race
        on ``proc.stdout.readline()`` and produce garbled JSON responses.
        See F106.
        """
        with self._cmd_lock:
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
                    response_line: list[str | None] = [None]
                    read_error: list[Exception | None] = [None]
                    proc = self._proc
                    if proc is None or proc.stdout is None:
                        return {"status": "error", "error": "Subprocess not running"}

                    def read_line() -> None:
                        try:
                            response_line[0] = proc.stdout.readline()  # type: ignore[union-attr]
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

                parsed: dict[str, Any] = json.loads(line.strip())
                return parsed

            except json.JSONDecodeError as e:
                return {"status": "error", "error": f"Invalid JSON response: {e}"}
            except Exception as e:
                return {"status": "error", "error": str(e)}

    def _read_stderr(self) -> None:
        """Read stderr in background thread to prevent deadlock."""
        if not self._proc or not self._proc.stderr:
            return
        try:
            for line in self._proc.stderr:
                line = line.strip()
                if line:
                    logger.info(f"[PiperGPU] {line}")
        except Exception as e:
            logger.debug("Suppressed error: %s", e, exc_info=True)

    def _ensure_stopped(self) -> None:
        """Stop subprocess if running (must be called with lock held).

        The persistent Piper worker communicates via a JSON line protocol on
        ``stdin``/``stdout``.  When we request a graceful shutdown we must also
        consume the JSON response that the worker writes before it exits.  If we
        ignore that response the worker can block on a full stdout pipe, leaving
        the subprocess alive and causing the test suite to hang.

        The blocking waits (``proc.wait``) happen outside ``self._lock`` to
        avoid holding the lock for up to 8 seconds during process shutdown.
        """
        proc = self._proc
        if not proc:
            return

        # --- Quick operations under lock: signal shutdown, close pipes ---
        try:
            if proc.stdin:
                try:
                    shutdown_cmd = json.dumps({"action": "shutdown"}) + "\n"
                    proc.stdin.write(shutdown_cmd)
                    proc.stdin.flush()
                except Exception:
                    pass
        except Exception:
            pass

        # Release lock for blocking waits
        self._lock.release()
        try:
            # Read any pending response to unblock the worker
            try:
                if proc.stdout:
                    if sys.platform != "win32":
                        import select

                        ready, _, _ = select.select([proc.stdout], [], [], 3)
                        if ready:
                            proc.stdout.readline()
                    else:
                        response_line_shutdown: list[str | None] = [None]
                        proc_shutdown = proc

                        def _read() -> None:
                            try:
                                if proc_shutdown and proc_shutdown.stdout:
                                    response_line_shutdown[0] = proc_shutdown.stdout.readline()
                            except Exception as e:
                                logger.debug("Suppressed error: %s", e, exc_info=True)

                        t = threading.Thread(target=_read)
                        t.start()
                        t.join(3)
            except Exception as e:
                logger.debug("Failed to read from subprocess stdout: %s", e)

            # Wait for graceful exit
            with contextlib.suppress(Exception):
                proc.wait(timeout=3)

            # Force kill if still running
            if proc.poll() is None:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        capture_output=True,
                        creationflags=get_creation_flags(),
                    )
                else:
                    proc.kill()
                with contextlib.suppress(Exception):
                    proc.wait(timeout=5)
        finally:
            self._lock.acquire()
            # Close pipes and clear reference under lock
            try:
                if proc.stdin:
                    proc.stdin.close()
            except Exception:
                pass
            try:
                if proc.stdout:
                    proc.stdout.close()
            except Exception:
                pass
            try:
                if proc.stderr:
                    proc.stderr.close()
            except Exception:
                pass
            self._proc = None

        # The worker script is a permanent file (modules/piper_worker.py),
        # so we don't clean it up here.
        self._script_path = None

        # Reset internal state flags.
        self._model_loaded = False
        self._using_cuda = False
        self._last_heartbeat_ok = True


# ──────────────────────────────────────────────────────────────────────
# ONE-SHOT LOADER (existing functionality, kept for compatibility)
# ──────────────────────────────────────────────────────────────────────


def load_piper_model_subprocess(
    voice_name: str, model_path: str, config_path: str, device: str = "auto", timeout: int = 90
) -> dict[str, Any]:
    """
    Load Piper model in a one-shot subprocess (validates model works).

    Returns:
        dict with keys: status, using_cuda, sample_rate, provider, error
    """
    start_time = time.time()

    if not _LOADER_SCRIPT_PATH.exists():
        logger.error(f"[PIPER_DEBUG] Loader script not found: {_LOADER_SCRIPT_PATH}")
        return {"status": "error", "error": f"Loader script not found: {_LOADER_SCRIPT_PATH}"}

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
            [sys.executable, str(_LOADER_SCRIPT_PATH), voice_name, model_path, config_path, device],
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
            data = json.loads(stdout[json_start:] if json_start >= 0 else stdout)
            logger.info(f"[PIPER_DEBUG] Load result: {data}")
            return dict(data)
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


def check_piper_environment() -> dict[str, Any]:
    """Check if piper and onnxruntime are available, report versions."""
    result: dict[str, Any] = {
        "piper_available": False,
        "onnxruntime_available": False,
        "onnx_version": None,
        "providers": [],
        "cuda_available": False,
        "python_path": sys.executable,
        "python_version": sys.version,
    }

    try:
        import importlib.util

        result["piper_available"] = importlib.util.find_spec("piper") is not None
    except Exception as e:
        result["piper_error"] = str(e)

    try:
        import onnxruntime as ort

        result["onnxruntime_available"] = True
        result["onnx_version"] = ort.__version__
        providers: list[str] = list(ort.get_available_providers())
        result["providers"] = providers
        result["cuda_available"] = "CUDAExecutionProvider" in providers
    except ImportError as e:
        result["onnx_error"] = str(e)

    return result
