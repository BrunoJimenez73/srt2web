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

import os
import sys
import glob
import time
import logging
import subprocess
import threading
import struct
from pathlib import Path
from typing import Optional

from core.input_source import InputSource
from core.module_base import PipelineData
from core.ffmpeg_utils import ensure_ffmpeg, get_video_duration
from core.watchdog import FFmpegWatchdog


class SRTInput(InputSource):
    """
    Recibe un stream SRT y produce chunks de video segmentados.

    Utiliza FFmpeg como subprocess para recibir el stream SRT
    y escribir segmentos de duración fija.

    Incluye FFmpegWatchdog para detectar crashes/hangs y reiniciar
    automáticamente el proceso.
    """

    def __init__(self, config: dict):
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
        self._ffmpeg_path: Optional[str] = None
        self._ffmpeg_proc: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._chunks_dir: str = ""
        self._last_chunk_index: int = -1
        self._cumulative_duration: float = 0.0  # Track cumulative duration for sync

        # Watchdog para detección de crashes/hangs
        self._watchdog: Optional[FFmpegWatchdog] = None
        self._watchdog_enabled = config.get("watchdog_enabled", True)
        self._watchdog_check_interval = config.get("watchdog_check_interval", 5.0)
        self._watchdog_hang_timeout = config.get("watchdog_hang_timeout", 60.0)
        self._watchdog_max_restarts = config.get("watchdog_max_restarts", 10)
        self._is_restarting = False  # Flag para evitar restarts concurrentes

        # GPU info for hwaccel (detect once at init)
        self._gpu_info = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False}
        self._hwaccel_enabled = False
        self._hwaccel_device = "0"

    def configure(self, config: dict) -> None:
        """Aplicar configuración."""
        self._srt_port = config.get("listen_port", self._srt_port)
        self._srt_mode = config.get("mode", self._srt_mode)
        self._srt_latency_ms = config.get("latency_ms", self._srt_latency_ms)
        self._srt_caller_address = config.get(
            "caller_address", self._srt_caller_address
        )
        self._chunk_duration = config.get("chunk_duration_sec", self._chunk_duration)
        
        # Watchdog config
        self._watchdog_enabled = config.get("watchdog_enabled", self._watchdog_enabled)
        self._watchdog_check_interval = config.get("watchdog_check_interval", self._watchdog_check_interval)
        self._watchdog_hang_timeout = config.get("watchdog_hang_timeout", self._watchdog_hang_timeout)
        self._watchdog_max_restarts = config.get("watchdog_max_restarts", self._watchdog_max_restarts)

    def get_connection_info(self) -> dict:
        """Obtener información de conexión para el usuario."""
        latency_us = self._srt_latency_ms * 1000

        if self._srt_mode == "caller" and self._srt_caller_address:
            srt_url = f"srt://{self._srt_caller_address}:{self._srt_port}?mode=caller&latency={latency_us}"
        else:
            srt_url = (
                f"srt://0.0.0.0:{self._srt_port}?mode=listener&latency={latency_us}"
            )

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
            self._ensure_stopped()
            
            # Wait for port release - with better socket handling on Windows
            if sys.platform == "win32":
                self.logger.info(f"Checking port {self._srt_port} availability...")
                for attempt in range(15):  # Try 15 times (up to 15 seconds)
                    try:
                        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        test_sock.bind(('0.0.0.0', self._srt_port))
                        test_sock.close()
                        self.logger.info(f"✓ Port {self._srt_port} is available")
                        break
                    except OSError as e:
                        self.logger.warning(f"Port {self._srt_port} in use ({e}), attempting cleanup...")
                        # Aggressive cleanup: kill ALL processes using this port
                        subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], 
                                     capture_output=True, timeout=2)
                        subprocess.run(["taskkill", "/F", "/IM", "ffprobe.exe"], 
                                     capture_output=True, timeout=2)
                        # Also try to kill by finding PID using netstat
                        try:
                            result = subprocess.run(
                                ["powershell", "-Command", 
                                 f"Get-NetTCPConnection -LocalPort {self._srt_port} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"],
                                capture_output=True, timeout=5
                            )
                        except:
                            pass
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
                    test_sock.bind(('0.0.0.0', self._srt_port))
                    test_sock.close()
                    self.logger.info(f"✓ Port {self._srt_port} is available")
                except OSError:
                    self.logger.warning(f"Port {self._srt_port} in use, continuing anyway...")
            
            self._last_chunk_index = -1
            self.logger.info("Getting FFmpeg path...")
            self._ffmpeg_path = ensure_ffmpeg()
            self.logger.info(f"FFmpeg path: {self._ffmpeg_path}")

            # Crear directorio de chunks
            self._chunks_dir = os.path.join(self._output_dir or "./output", "chunks")
            os.makedirs(self._chunks_dir, exist_ok=True)
            self.logger.info(f"Chunks directory: {self._chunks_dir}")

            # Detectar soporte GPU para hwaccel
            from core.ffmpeg_utils import check_gpu_support
            self._gpu_info = check_gpu_support(self._ffmpeg_path)
            self.logger.info(f"Input GPU support: {self._gpu_info}")

            # Habilitar hwaccel si hay GPU disponible
            if self._gpu_info.get("nvenc"):
                self._hwaccel_enabled = True
                self.logger.info("Input: Using NVDEC hardware acceleration")
            elif self._gpu_info.get("qsv"):
                self._hwaccel_enabled = True
                self._hwaccel_device = "0"
                self.logger.info("Input: Using QSV hardware acceleration")
            elif self._gpu_info.get("vaapi"):
                self._hwaccel_enabled = True
                self.logger.info("Input: Using VAAPI hardware acceleration")
            else:
                self._hwaccel_enabled = False
                self.logger.info("Input: No GPU acceleration available, using CPU")

            # Limpiar chunks antiguos
            for f in glob.glob(os.path.join(self._chunks_dir, "chunk_*.ts")):
                try:
                    os.remove(f)
                except OSError:
                    pass

            # Reset cumulative duration tracking
            self._cumulative_duration = 0.0

            # Construir URL SRT
            latency_us = self._srt_latency_ms * 1000
            if self._srt_mode == "caller" and self._srt_caller_address:
                srt_url = f"srt://{self._srt_caller_address}:{self._srt_port}?mode=caller&latency={latency_us}"
            else:
                srt_url = (
                    f"srt://0.0.0.0:{self._srt_port}?mode=listener&latency={latency_us}"
                )
            self.logger.info(f"SRT URL: {srt_url}")

            # Comando FFmpeg para recepción segmentada
            chunk_pattern = os.path.join(self._chunks_dir, "chunk_%06d.ts")

            # Construir comando con soporte hwaccel (GPU acceleration)
            cmd = [self._ffmpeg_path, "-y"]

            # Añadir hwaccel si hay GPU disponible
            if self._hwaccel_enabled:
                if self._gpu_info.get("nvenc"):
                    cmd.extend(["-hwaccel", "cuda", "-hwaccel_device", self._hwaccel_device])
                elif self._gpu_info.get("qsv"):
                    cmd.extend(["-hwaccel", "qsv", "-hwaccel_device", self._hwaccel_device])
                elif self._gpu_info.get("vaapi"):
                    cmd.extend(["-hwaccel", "vaapi"])

            # Comando FFmpeg para recepción segmentada
            cmd.extend([
                "-i", srt_url,
                "-c", "copy",
                "-f", "segment",
                "-segment_time", str(self._chunk_duration),
                "-segment_format", "mpegts",
                "-reset_timestamps", "1",
                "-strftime", "0",
                "-max_muxing_queue_size", "1024",
                "-fflags", "+genpts+discardcorrupt",
                "-flush_packets", "1",
                chunk_pattern,
            ])

            # Log detallado del comando para debug
            safe_cmd = [c if len(c) < 100 else c[:50]+"..." for c in cmd]
            self.logger.info(f"FFmpeg cmd: {' '.join(safe_cmd)}")

            self.logger.info(f"Starting SRT input: {' '.join(cmd)}")
            self.logger.info("Starting FFmpeg process...")

            # Iniciar proceso FFmpeg
            self._ffmpeg_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
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

        self._watchdog.attach_process(
            process=self._ffmpeg_proc,
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

        self._is_restarting = True
        try:
            self.logger.info("Watchdog requesting FFmpeg restart...")

            # Detener proceso actual
            self._kill_ffmpeg_process()

            # Esperar un poco antes de reiniciar
            time.sleep(1.0)

            # Reiniciar el proceso
            self.logger.info("Restarting SRT input...")
            self._start_ffmpeg_process()

            # Re-attach al watchdog con el nuevo proceso
            if self._watchdog:
                self._watchdog.attach_process(
                    process=self._ffmpeg_proc,
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
        chunk_pattern = os.path.join(self._chunks_dir, "chunk_%06d.ts")

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

        self.logger.info(f"Restarting SRT input: {' '.join(cmd)}")

        # Iniciar proceso FFmpeg
        self._ffmpeg_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            ),
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
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=3,
                    )
                    # ALSO kill any ffmpeg using the SRT port
                    try:
                        subprocess.run(
                            ["cmd", "/C", f"for /F \"tokens=5\" %a in ('netstat -ano ^| findstr :{self._srt_port} ^| findstr LISTENING') do @echo %a"],
                            capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            timeout=3,
                        )
                    except:
                        pass
                else:
                    self._ffmpeg_proc.terminate()
                self._ffmpeg_proc.wait(timeout=2)
            except Exception as e:
                self.logger.debug(f"Process cleanup: {e}")
            finally:
                self._ffmpeg_proc = None

    def stop(self) -> None:
        """Stop SRT receiver and ensure port release."""
        import subprocess
        import socket
        
        self.logger.info("=== STOPPING SRT INPUT ===")
        
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
                        result = subprocess.run(["taskkill", "/F", "/IM", proc_name], 
                                           capture_output=True, timeout=3)
                        if result.returncode != 0:
                            break  # No process found
                        time.sleep(0.5)
                    except:
                        pass
            
            # Wait for port to be released with multiple attempts
            port_free = False
            for attempt in range(10):  # Try 10 times (up to 10 seconds)
                try:
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
                    test_sock.bind(('0.0.0.0', self._srt_port))
                    test_sock.close()
                    self.logger.info(f"✓ Port {self._srt_port} is now FREE")
                    port_free = True
                    break
                except OSError as e:
                    self.logger.warning(f"Port {self._srt_port} still in use: {e}, attempt {attempt+1}/10")
                    # Aggressive cleanup
                    subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], capture_output=True, timeout=2)
                    if attempt < 9:
                        time.sleep(1)
            
            if not port_free:
                self.logger.warning(f"Port {self._srt_port} may not be fully released, trying anyway...")

        self.logger.info("SRT input stopped")

    def get_next_chunk(self) -> Optional[PipelineData]:
        """
        Obtener el siguiente chunk disponible.

        Returns:
            PipelineData con el chunk de video, o None si no hay ninguno.
        """
        if not self._chunks_dir:
            return None

        chunks = sorted(glob.glob(os.path.join(self._chunks_dir, "chunk_*.ts")))

        if not chunks:
            self.logger.debug(f"SRT input: no chunks found in {self._chunks_dir}")
            return None

        # With 2+ chunks: exclude the latest (might still be writing)
        # With 1 chunk: process it if old enough (FFmpeg has moved on)
        if len(chunks) >= 2:
            chunks = chunks[:-1]
        elif len(chunks) == 1:
            chunk_age = time.time() - os.path.getmtime(chunks[0])
            if chunk_age < self._chunk_duration * 0.8:
                self.logger.debug(f"SRT input: only 1 chunk, age={chunk_age:.1f}s < {self._chunk_duration * 0.8:.1f}s, waiting...")
                return None
            self.logger.debug(f"SRT input: single chunk old enough ({chunk_age:.1f}s), processing")
        else:
            return None

        # Encontrar siguiente chunk no procesado
        processable = []
        for chunk_path in chunks:
            fname = os.path.basename(chunk_path)
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

        # Medir duración real
        actual_duration = get_video_duration(chunk_path) or self._chunk_duration

        # Validate duration (warn if FFmpeg segment duration differs too much)
        duration_diff = abs(actual_duration - self._chunk_duration)
        if duration_diff > 0.05:  # 50ms threshold
            self.logger.warning(
                f"Chunk {idx} duration {actual_duration:.3f}s differs from "
                f"expected {self._chunk_duration:.3f}s by {duration_diff * 1000:.1f}ms"
            )

        # Set cumulative duration BEFORE processing (will be corrected after if needed)
        chunk_cumulative = self._cumulative_duration

        # Update cumulative for next chunk
        self._cumulative_duration += actual_duration

        self.logger.info(
            f"New chunk: {chunk_path} (cumulative: {chunk_cumulative:.3f}s)"
        )

        # Log first chunk specifically for debugging
        if idx == 0:
            self.logger.info("FIRST SRT CHUNK GENERATED BY FFMPEG")
            self.logger.info(f"First chunk path: {chunk_path}")

        # Notify watchdog of activity
        if self._watchdog:
            self._watchdog.notify_activity()

        # Create PipelineData with video chunk (using correct dataclass syntax)
        return PipelineData(
            video_chunk_path=chunk_path,
            audio_chunk_path=None,
            chunk_index=idx,
            duration=actual_duration,
            cumulative_duration=chunk_cumulative,
            metadata={"source": "srt"}
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

    def get_watchdog_status(self) -> dict:
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

    def get_status(self) -> dict:
        """Get status including GPU acceleration info."""
        return {
            "name": "input",
            "state": "running" if self.is_receiving() else "idle",
            "enabled": True,
            "processed_chunks": self._last_chunk_index + 1 if self._last_chunk_index >= 0 else 0,
            "last_process_time_ms": 0,
            "extra": {
                "using_gpu": self._hwaccel_enabled,
                "gpu_info": self._gpu_info,
                "encoder_label": "NVDEC" if self._gpu_info.get("nvenc") else "QSV" if self._gpu_info.get("qsv") else "VAAPI" if self._gpu_info.get("vaapi") else "CPU",
                "hwaccel": self._hwaccel_enabled,
            }
        }

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
                    elif "connection" in line.lower() or "accept" in line.lower() or "stream" in line.lower() or "duration" in line.lower():
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
        import subprocess
        import socket
        
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
                try:
                    subprocess.run(["taskkill", "/F", "/IM", proc_name], 
                                capture_output=True, timeout=2)
                except:
                    pass
        
        # Wait a moment for socket to be released
        time.sleep(1)
        
        # Verify port is free before returning
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_sock.bind(('0.0.0.0', self._srt_port))
            test_sock.close()
            self.logger.info(f"Port {self._srt_port} is ready")
        except OSError:
            self.logger.warning(f"Port {self._srt_port} still in use in _ensure_stopped")
            # Don't wait forever - proceed anyway


# Auto-registro en factory
from core.io_factory import InputFactory

InputFactory.register("srt", SRTInput)