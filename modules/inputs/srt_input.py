"""
SRT Input - Recibe streams vía protocolo SRT.

Este módulo escucha conexiones SRT entrantes (de OBS, vMix, etc.)
y produce chunks de video segmentados para el pipeline.

Configuración (input.srt):
    listen_port: Puerto donde escuchar (default: 9000)
    mode: Modo SRT - "listener" o "caller" (default: listener)
    latency_ms: Latencia SRT en milisegundos (default: 1000)
    caller_address: Dirección del caller (para modo caller)
    chunk_duration_sec: Duración de cada chunk en segundos (default: 15)
"""

import contextlib
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from core.chunk_clock import ChunkClock
from core.ffmpeg_utils import ensure_ffmpeg, get_first_packet_pts, get_pcr_from_ts, get_video_duration
from core.input_source import InputSource
from core.io_factory import InputFactory
from core.module_base import ModuleState, ModuleStatus, PipelineData
from core.subprocess_utils import filter_command, get_creation_flags
from core.watchdog import FFmpegWatchdog


class SRTInput(InputSource):
    """
    Recibe un stream SRT y produce chunks de video segmentados.

    Utiliza FFmpeg como subprocess para recibir el stream SRT
    y escribir segmentos de duración fija.

    Incluye FFmpegWatchdog para detectar crashes/hangs y reiniciar
    automáticamente el proceso.
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__("srt", config)
        self.logger.info("=== SRTInput CREATED ===")

        # Configuración SRT
        self._srt_port = config.get("listen_port", 9000)
        self._srt_mode = config.get("mode", "listener")
        self._srt_latency_ms = config.get("latency_ms", 1000)
        self._srt_caller_address = config.get("caller_address", "")

        # Configuración de chunks
        self._chunk_duration = config.get("chunk_duration_sec", 10)

        # Estado interno
        self._ffmpeg_path: str | None = None
        self._ffmpeg_proc: subprocess.Popen[Any] | None = None
        self._monitor_thread: threading.Thread | None = None
        self._chunks_dir: str = ""
        self._last_chunk_index: int = -1
        self._last_process_time: float = 0.0
        # F115: mtime/drift/cumulative state moved to ChunkClock.
        # Owns _last_chunk_mtime and _cumulative_duration behind a
        # tested API; see core/chunk_clock.py for details.
        self._clock = ChunkClock(chunk_duration=self._chunk_duration)

        # Watchdog para detección de crashes/hangs
        self._watchdog: FFmpegWatchdog | None = None
        self._watchdog_enabled = config.get("watchdog_enabled", True)
        self._watchdog_check_interval = config.get("watchdog_check_interval", 5.0)
        self._watchdog_hang_timeout = config.get("watchdog_hang_timeout", 60.0)
        self._watchdog_max_restarts = config.get("watchdog_max_restarts", 10)
        self._is_restarting = False  # Flag para evitar restarts concurrentes
        self._stopping = threading.Event()  # Señal para abortar restart durante stop

        # GPU info for hwaccel (detect once at init)
        self._gpu_info = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False}
        self._hwaccel_enabled = False
        self._hwaccel_device = "0"

    def configure(self, config: dict[str, Any]) -> None:
        """Aplicar configuración."""
        self._srt_port = config.get("listen_port", self._srt_port)
        self._srt_mode = config.get("mode", self._srt_mode)
        self._srt_latency_ms = config.get("latency_ms", self._srt_latency_ms)
        self._srt_caller_address = config.get("caller_address", self._srt_caller_address)
        new_chunk_duration = config.get("chunk_duration_sec", self._chunk_duration)
        if self._clock.update_chunk_duration(new_chunk_duration):
            self.logger.info(
                f"SRT chunk_duration changed: {self._chunk_duration}s → {new_chunk_duration}s, resetting cumulative"
            )
        self._chunk_duration = new_chunk_duration

        # Watchdog config
        self._watchdog_enabled = config.get("watchdog_enabled", self._watchdog_enabled)
        self._watchdog_check_interval = config.get("watchdog_check_interval", self._watchdog_check_interval)
        self._watchdog_hang_timeout = config.get("watchdog_hang_timeout", self._watchdog_hang_timeout)
        self._watchdog_max_restarts = config.get("watchdog_max_restarts", self._watchdog_max_restarts)

    def get_connection_info(self) -> dict[str, Any]:
        """Obtener información de conexión para el usuario."""
        latency_us = self._srt_latency_ms * 1000

        if self._srt_mode == "caller" and self._srt_caller_address:
            srt_url = f"srt://{self._srt_caller_address}:{self._srt_port}?mode=caller&latency={latency_us}"
        else:
            srt_url = f"srt://0.0.0.0:{self._srt_port}?mode=listener&latency={latency_us}"

        return {
            "type": "srt",
            "mode": self._srt_mode,
            "port": self._srt_port,
            "latency_ms": self._srt_latency_ms,
            "url": srt_url,
            "obs_url": f"srt://YOUR_IP:{self._srt_port}?mode=caller&latency={latency_us}",
        }

    def start(self) -> None:
        """Start SRT receiver."""
        import socket
        import subprocess

        try:
            self.logger.info("=== STARTING SRT INPUT ===")
            self._stopping.clear()
            self._ensure_stopped()

            # Wait for port release - with better socket handling on Windows
            if sys.platform == "win32":
                self.logger.info(f"Checking port {self._srt_port} availability...")
                for attempt in range(15):  # Try 15 times (up to 15 seconds)
                    try:
                        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        test_sock.bind(("0.0.0.0", self._srt_port))
                        test_sock.close()
                        self.logger.info(f"✓ Port {self._srt_port} is available")
                        break
                    except OSError as e:
                        self.logger.warning(f"Port {self._srt_port} in use ({e}), attempting cleanup...")
                        # Aggressive cleanup: kill ALL processes using this port
                        subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], capture_output=True, timeout=2)
                        subprocess.run(["taskkill", "/F", "/IM", "ffprobe.exe"], capture_output=True, timeout=2)
                        # Also try to kill by finding PID using netstat
                        with contextlib.suppress(Exception):
                            result = subprocess.run(
                                [
                                    "powershell",
                                    "-Command",
                                    f"Get-NetTCPConnection -LocalPort {self._srt_port} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}",
                                ],
                                capture_output=True,
                                timeout=5,
                            )
                        if attempt < 14:
                            time.sleep(1)
                else:
                    self.logger.error(f"Port {self._srt_port} still in use after 15 attempts - will try anyway")
                    # Don't fail - try to start anyway, FFmpeg might handle it
            else:
                # Non-Windows: simple check
                try:
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    test_sock.bind(("0.0.0.0", self._srt_port))
                    test_sock.close()
                    self.logger.info(f"✓ Port {self._srt_port} is available")
                except OSError:
                    self.logger.warning(f"Port {self._srt_port} in use, continuing anyway...")

            self._last_chunk_index = -1
            self.logger.info("Getting FFmpeg path...")
            self._ffmpeg_path = ensure_ffmpeg()
            self.logger.info(f"FFmpeg path: {self._ffmpeg_path}")

            # Crear directorio de chunks
            self._chunks_dir = str(Path(self._output_dir or "./output") / "chunks")
            Path(self._chunks_dir).mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Chunks directory: {self._chunks_dir}")

            # Detectar soporte GPU para hwaccel
            from core.ffmpeg_process import detect_gpu, resolve_hwaccel

            self._gpu_info = detect_gpu(self._ffmpeg_path, "Input")

            # Habilitar hwaccel si hay GPU disponible
            self._hwaccel_enabled, self._hwaccel_device = resolve_hwaccel(self._gpu_info, "Input")

            # Limpiar chunks antiguos
            from core.ffmpeg_process import cleanup_old_chunks

            cleanup_old_chunks(self._chunks_dir)

            # Reset cumulative duration tracking (F115: delegated to ChunkClock)
            self._clock.reset()

            # Construir URL SRT
            latency_us = self._srt_latency_ms * 1000
            if self._srt_mode == "caller" and self._srt_caller_address:
                srt_url = f"srt://{self._srt_caller_address}:{self._srt_port}?mode=caller&latency={latency_us}"
            else:
                srt_url = f"srt://0.0.0.0:{self._srt_port}?mode=listener&latency={latency_us}"
            self.logger.info(f"SRT URL: {srt_url}")

            # Comando FFmpeg para recepción segmentada
            chunk_pattern = str(Path(self._chunks_dir) / "chunk_%06d.ts")

            # Construir comando con soporte hwaccel (GPU acceleration)
            cmd = [self._ffmpeg_path, "-y"]

            # Añadir hwaccel si hay GPU disponible
            from core.ffmpeg_process import build_hwaccel_args

            cmd.extend(build_hwaccel_args(self._hwaccel_enabled, self._gpu_info, self._hwaccel_device))

            # Comando FFmpeg para recepción segmentada
            cmd.extend(
                [
                    "-i",
                    srt_url,
                    "-c",
                    "copy",
                    "-f",
                    "segment",
                    "-segment_time",
                    str(self._chunk_duration),
                    "-segment_format",
                    "mpegts",
                    "-reset_timestamps",
                    "1",
                    "-strftime",
                    "0",
                    "-max_muxing_queue_size",
                    "1024",
                    "-fflags",
                    "+genpts+discardcorrupt",
                    "-flush_packets",
                    "1",
                    chunk_pattern,
                ]
            )

            # Log detallado del comando para debug
            cmd_argv = filter_command(cmd)
            safe_cmd = [c if len(c) < 100 else c[:50] + "..." for c in cmd_argv]
            self.logger.info(f"FFmpeg cmd: {' '.join(safe_cmd)}")

            self.logger.info(f"Starting SRT input: {' '.join(cmd_argv)}")
            self.logger.info("Starting FFmpeg process...")

            # Iniciar proceso FFmpeg
            self._ffmpeg_proc = subprocess.Popen(
                cmd_argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=get_creation_flags(),
            )

            if not self._ffmpeg_proc:
                raise Exception("FFmpeg process is None")

            self.logger.info(f"FFmpeg process started with PID: {self._ffmpeg_proc.pid}")

            # Hilo monitor para logs stderr
            self._monitor_thread = threading.Thread(
                target=self._monitor_ffmpeg,
                daemon=True,
                name="srt-input-monitor",
            )
            self._monitor_thread.start()

            # Iniciar watchdog si está habilitado
            if self._watchdog_enabled:
                self._start_watchdog()

            self.logger.info(f"SRT input started on port {self._srt_port}")
            self.logger.info("SRT input started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start SRT input: {type(e).__name__}: {e}")
            import traceback

            self.logger.error(f"SRT input traceback: {traceback.format_exc()}")
            raise

    def _start_watchdog(self) -> None:
        """Iniciar el watchdog para monitorear el proceso FFmpeg."""
        if self._watchdog is not None:
            self._watchdog.stop()
            self._watchdog = None

        self._watchdog = FFmpegWatchdog(
            check_interval=self._watchdog_check_interval,
            hang_timeout=self._watchdog_hang_timeout,
            max_restarts=self._watchdog_max_restarts,
            restart_delay=2.0,
        )

        proc = self._ffmpeg_proc
        if proc is not None:
            self._watchdog.attach_process(
                process=proc,
                process_name="SRT-FFmpeg",
                restart_callback=self._on_ffmpeg_restart,
            )
        self._watchdog.start()
        self.logger.info(
            f"SRT watchdog started (check_interval={self._watchdog_check_interval}s, "
            f"hang_timeout={self._watchdog_hang_timeout}s, "
            f"max_restarts={self._watchdog_max_restarts})"
        )

    def _on_ffmpeg_restart(self) -> None:
        """Callback llamado por el watchdog cuando necesita reiniciar FFmpeg."""
        if self._is_restarting:
            self.logger.warning("Restart already in progress, skipping")
            return

        if self._stopping.is_set():
            self.logger.info("Pipeline stopping, aborting FFmpeg restart")
            return

        self._is_restarting = True
        try:
            self.logger.info("Watchdog requesting FFmpeg restart...")

            # Detener proceso actual
            self._kill_ffmpeg_process()

            # Esperar un poco antes de reiniciar
            time.sleep(1.0)

            if self._stopping.is_set():
                self.logger.info("Pipeline stopping, aborting FFmpeg restart after kill")
                return

            # Reiniciar el proceso
            self.logger.info("Restarting SRT input...")
            self._start_ffmpeg_process()

            # Re-attach al watchdog con el nuevo proceso
            if self._watchdog:
                proc = self._ffmpeg_proc
                if proc is not None:
                    self._watchdog.attach_process(
                        process=proc,
                        process_name="SRT-FFmpeg",
                        restart_callback=self._on_ffmpeg_restart,
                    )
                self.logger.info("FFmpeg restarted and re-attached to watchdog")
            else:
                self.logger.warning("Watchdog not available after restart")

        except Exception as e:
            self.logger.error(f"Failed to restart FFmpeg: {type(e).__name__}: {e}")
            import traceback

            self.logger.error(f"Restart traceback: {traceback.format_exc()}")
        finally:
            self._is_restarting = False

    def _start_ffmpeg_process(self) -> None:
        """Crear y iniciar el proceso FFmpeg (para reinicios)."""
        # Construir URL SRT
        latency_us = self._srt_latency_ms * 1000
        if self._srt_mode == "caller" and self._srt_caller_address:
            srt_url = f"srt://{self._srt_caller_address}:{self._srt_port}?mode=caller&latency={latency_us}"
        else:
            srt_url = f"srt://0.0.0.0:{self._srt_port}?mode=listener&latency={latency_us}"

        # Comando FFmpeg para recepción segmentada
        chunk_pattern = str(Path(self._chunks_dir) / "chunk_%06d.ts")

        cmd = [
            self._ffmpeg_path,
            "-y",
            "-i",
            srt_url,
            "-c",
            "copy",
            "-f",
            "segment",
            "-segment_time",
            str(self._chunk_duration),
            "-segment_format",
            "mpegts",
            "-reset_timestamps",
            "1",
            "-strftime",
            "0",
            "-max_muxing_queue_size",
            "1024",
            "-fflags",
            "+genpts+discardcorrupt",
            "-flush_packets",
            "1",
            chunk_pattern,
        ]

        cmd_argv = filter_command(cmd)
        self.logger.info(f"Restarting SRT input: {' '.join(cmd_argv)}")

        # Iniciar proceso FFmpeg
        self._ffmpeg_proc = subprocess.Popen(
            cmd_argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=get_creation_flags(),
        )

        if not self._ffmpeg_proc:
            raise Exception("FFmpeg process restart failed (process is None)")

        self.logger.info(f"FFmpeg process restarted with PID: {self._ffmpeg_proc.pid}")

        # Reiniciar hilo monitor
        self._monitor_thread = threading.Thread(
            target=self._monitor_ffmpeg,
            daemon=True,
            name="srt-input-monitor",
        )
        self._monitor_thread.start()

    def _kill_ffmpeg_process(self) -> None:
        """Matar el proceso FFmpeg de forma segura."""
        import subprocess

        if self._ffmpeg_proc:
            try:
                if sys.platform == "win32":
                    # Kill main process and ALL children
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self._ffmpeg_proc.pid)],
                        capture_output=True,
                        creationflags=get_creation_flags(),
                        timeout=3,
                    )
                    # ALSO kill any ffmpeg using the SRT port
                    with contextlib.suppress(Exception):
                        subprocess.run(
                            [
                                "cmd",
                                "/C",
                                f"for /F \"tokens=5\" %a in ('netstat -ano ^| findstr :{self._srt_port} ^| findstr LISTENING') do @echo %a",
                            ],
                            capture_output=True,
                            creationflags=get_creation_flags(),
                            timeout=3,
                        )
                else:
                    self._ffmpeg_proc.terminate()
                self._ffmpeg_proc.wait(timeout=2)
            except Exception as e:
                self.logger.debug(f"Process cleanup: {e}")
            finally:
                self._ffmpeg_proc = None

    def stop(self) -> None:
        """Stop SRT receiver and ensure port release."""
        import socket
        import subprocess

        self.logger.info("=== STOPPING SRT INPUT ===")
        self._stopping.set()  # Abort any in-flight watchdog restart

        # Stop watchdog first
        if self._watchdog:
            self._watchdog.stop()
            self._watchdog = None

        # Kill FFmpeg process
        self._kill_ffmpeg_process()

        # Force kill ALL ffmpeg processes on Windows with stronger cleanup
        if sys.platform == "win32":
            self.logger.info("Killing all ffmpeg/ffprobe processes...")

            # Kill by process name - multiple times for stubborn processes
            for proc_name in ["ffmpeg.exe", "ffprobe.exe"]:
                for _ in range(3):
                    try:
                        result = subprocess.run(["taskkill", "/F", "/IM", proc_name], capture_output=True, timeout=3)
                        if result.returncode != 0:
                            break  # No process found
                        time.sleep(0.5)
                    except Exception as e:
                        self.logger.debug(f"Failed to kill SRT process {proc_name}: {e}")
                        pass

            # Quick port check — don't block stop for more than ~3s total
            port_free = False
            for attempt in range(3):  # Try 3 times max (was 10)
                try:
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                    test_sock.bind(("0.0.0.0", self._srt_port))
                    test_sock.close()
                    self.logger.info(f"✓ Port {self._srt_port} is now FREE")
                    port_free = True
                    break
                except OSError as e:
                    self.logger.warning(f"Port {self._srt_port} still in use: {e}, attempt {attempt+1}/3")
                    # Aggressive cleanup
                    subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], capture_output=True, timeout=2)
                    if attempt < 2:
                        time.sleep(1)

            if not port_free:
                self.logger.warning(f"Port {self._srt_port} may not be fully released, trying anyway...")

        self.logger.info("SRT input stopped")

    def get_next_chunk(self) -> PipelineData | None:
        """
        Obtener el siguiente chunk disponible.

        Returns:
            PipelineData con el chunk de video, o None si no hay ninguno.
        """
        if not self._chunks_dir:
            return None

        chunks = sorted(Path(self._chunks_dir).glob("chunk_*.ts"))
        _t0 = time.perf_counter()

        if not chunks:
            self.logger.debug(f"SRT input: no chunks found in {self._chunks_dir}")
            return None

        # With 2+ chunks: exclude the latest (might still be writing)
        # With 1 chunk: process it if old enough (FFmpeg has moved on)
        if len(chunks) >= 2:
            chunks = chunks[:-1]
        elif len(chunks) == 1:
            chunk_age = time.time() - chunks[0].stat().st_mtime
            if chunk_age < self._chunk_duration * 0.5:
                self.logger.debug(
                    f"SRT input: only 1 chunk, age={chunk_age:.1f}s < {self._chunk_duration * 0.5:.1f}s, waiting..."
                )
                return None
            self.logger.debug(f"SRT input: single chunk old enough ({chunk_age:.1f}s), processing")
        else:
            return None

        # Encontrar siguiente chunk no procesado
        processable = []
        for chunk_path in chunks:
            fname = chunk_path.name
            try:
                idx = int(fname.replace("chunk_", "").replace(".ts", ""))
                if idx > self._last_chunk_index:
                    processable.append((idx, chunk_path))
            except ValueError:
                continue

        if not processable:
            return None

        # Tomar el más antiguo
        processable.sort()
        idx, chunk_path = processable[0]
        self._last_chunk_index = idx

        self.logger.debug(f"SRT input: returning chunk {idx}: {chunk_path}")

        # F150: Try PTS-based timing first (eliminates mtime drift)
        # Falls back to mtime if PTS extraction fails
        pts_seconds = get_first_packet_pts(str(chunk_path))
        if pts_seconds is None:
            pts_seconds = get_pcr_from_ts(str(chunk_path))

        if pts_seconds is not None:
            chunk_cumulative = self._clock.record_pts(pts_seconds)
        else:
            # Fallback to mtime if PTS extraction fails
            chunk_cumulative = self._clock.record_mtime(chunk_path.stat().st_mtime)

        self.logger.info(f"New chunk: {chunk_path} (cumulative: {chunk_cumulative:.3f}s)")

        # Log first chunk specifically for debugging
        if idx == 0:
            self.logger.info("FIRST SRT CHUNK GENERATED BY FFMPEG")
            self.logger.info(f"First chunk path: {chunk_path}")

        self._last_process_time = (time.perf_counter() - _t0) * 1000

        # Notify watchdog of activity
        if self._watchdog:
            self._watchdog.notify_activity()

        # Get actual duration from the video chunk file
        actual_duration = get_video_duration(str(chunk_path))
        if actual_duration <= 0:
            actual_duration = self._chunk_duration

        # Create PipelineData with video chunk (using correct dataclass syntax)
        return PipelineData(
            video_chunk_path=str(chunk_path),
            audio_chunk_path=None,
            chunk_index=idx,
            duration=actual_duration,
            cumulative_duration=chunk_cumulative,
            metadata={"source": "srt"},
        )

    def is_receiving(self) -> bool:
        """Verificar si el proceso FFmpeg está corriendo."""
        if self._ffmpeg_proc is None:
            return False
        return self._ffmpeg_proc.poll() is None

    def is_healthy(self) -> bool:
        """Verificar si el watchdog está saludable (si está habilitado)."""
        if self._watchdog:
            return self._watchdog.is_healthy
        return self.is_receiving()

    def get_watchdog_status(self) -> dict[str, Any]:
        """Obtener estado del watchdog para debugging."""
        if self._watchdog:
            return {
                "enabled": self._watchdog_enabled,
                "healthy": self._watchdog.is_healthy,
                "restart_count": self._watchdog.restart_count,
                "max_restarts": self._watchdog_max_restarts,
            }
        return {
            "enabled": self._watchdog_enabled,
            "healthy": self.is_receiving(),
            "restart_count": 0,
            "max_restarts": self._watchdog_max_restarts,
        }

    def get_status(self) -> ModuleStatus:
        """Get status including GPU acceleration info."""
        from core.ffmpeg_process import get_input_status_extra

        return ModuleStatus(
            name="input",
            state=ModuleState.RUNNING if self.is_receiving() else ModuleState.IDLE,
            enabled=True,
            processed_chunks=self._last_chunk_index + 1 if self._last_chunk_index >= 0 else 0,
            last_process_time_ms=self._last_process_time,
            extra=get_input_status_extra(self._gpu_info, self._hwaccel_enabled),
        )

    def _monitor_ffmpeg(self) -> None:
        """Monitorear stderr de FFmpeg para logs."""
        if not self._ffmpeg_proc or not self._ffmpeg_proc.stderr:
            return

        try:
            for line in self._ffmpeg_proc.stderr:
                line = line.strip()
                if line:
                    if "error" in line.lower() or "failed" in line.lower() or "invalid" in line.lower():
                        self.logger.error(f"[FFmpeg] {line}")
                    elif "warning" in line.lower():
                        self.logger.warning(f"[FFmpeg] {line}")
                    elif (
                        "connection" in line.lower()
                        or "accept" in line.lower()
                        or "stream" in line.lower()
                        or "duration" in line.lower()
                    ):
                        self.logger.info(f"[FFmpeg] {line}")
                    else:
                        self.logger.debug(f"[FFmpeg] {line}")

                    # Notificar actividad al watchdog
                    if self._watchdog:
                        self._watchdog.notify_activity()
        except Exception as e:
            self.logger.debug(f"Monitor stderr exception: {e}")

    def _ensure_stopped(self) -> None:
        """Asegurar que cualquier proceso anterior esté detenido."""
        import socket
        import subprocess

        self.logger.info("Ensuring SRT input is stopped...")

        # Detener watchdog
        if self._watchdog:
            self._watchdog.stop()
            self._watchdog = None

        # Detener proceso
        self._kill_ffmpeg_process()

        # Additional cleanup: kill any lingering ffmpeg processes
        if sys.platform == "win32":
            for proc_name in ["ffmpeg.exe", "ffprobe.exe"]:
                with contextlib.suppress(Exception):
                    subprocess.run(["taskkill", "/F", "/IM", proc_name], capture_output=True, timeout=2)

        # Wait a moment for socket to be released
        time.sleep(1)

        # Verify port is free before returning
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_sock.bind(("0.0.0.0", self._srt_port))
            test_sock.close()
            self.logger.info(f"Port {self._srt_port} is ready")
        except OSError:
            self.logger.warning(f"Port {self._srt_port} still in use in _ensure_stopped")
            # Don't wait forever - proceed anyway


# Auto-registro en factory
InputFactory.register("srt", SRTInput)
