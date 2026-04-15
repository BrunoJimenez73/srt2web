"""
File Input - Lee video desde un archivo local.

Útil para:
- Testing del pipeline
- Procesamiento de archivos pre-grabados
- Modo "offline" del sistema

Configuración (input.file):
    path: Ruta al archivo de video (requerido)
    loop: Repetir cuando termine (default: false)
    speed: Velocidad de reproducción (default: 1.0)
    chunk_duration_sec: Duración de cada chunk (default: 15)
"""

import os
import sys
import glob
import time
import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional

from core.input_source import InputSource
from core.module_base import PipelineData
from core.ffmpeg_utils import ensure_ffmpeg, get_video_duration


class FileInput(InputSource):
    """
    Lee un archivo de video local y lo segmenta en chunks.
    """

    def __init__(self, config: dict):
        super().__init__("file", config)

        # Configuración
        self._file_path = config.get("path", "")
        self._loop = config.get("loop", False)
        self._speed = config.get("speed", 1.0)
        self._chunk_duration = config.get("chunk_duration_sec", 15)

        # Estado interno
        self._ffmpeg_path: Optional[str] = None
        self._ffmpeg_proc: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._chunks_dir: str = ""
        self._last_chunk_index: int = -1
        self._file_finished: bool = False
        self._cumulative_duration: float = 0.0  # Track cumulative duration for sync
        self._is_paused: bool = False
        self._current_position: float = 0.0  # Current playback position in seconds
        self._file_duration: float = 0.0  # Total file duration

        # GPU info for hwaccel
        self._gpu_info = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False}
        self._hwaccel_enabled = False
        self._hwaccel_device = "0"

    def configure(self, config: dict) -> None:
        """Aplicar configuración."""
        self._file_path = config.get("path", self._file_path)
        self._loop = config.get("loop", self._loop)
        self._speed = config.get("speed", self._speed)
        self._chunk_duration = config.get("chunk_duration_sec", self._chunk_duration)

    def get_connection_info(self) -> dict:
        """Obtener información del archivo incluyendo duración y posición actual."""
        # Obtener duración del archivo si aún no la tenemos
        if self._file_duration == 0.0 and self._file_path and os.path.exists(self._file_path):
            self._file_duration = get_video_duration(self._file_path) or 0.0
            
        return {
            "type": "file",
            "path": self._file_path,
            "loop": self._loop,
            "speed": self._speed,
            "exists": os.path.exists(self._file_path) if self._file_path else False,
            "duration": self._file_duration,
            "position": self._current_position,
            "is_paused": self._is_paused,
            "is_playing": self.is_receiving() and not self._is_paused,
        }

    def pause(self) -> None:
        """Pausar la reproducción del archivo."""
        if self._ffmpeg_proc and not self._is_paused:
            # Enviar señal SIGSTOP para pausar el proceso FFmpeg
            try:
                import signal
                if sys.platform == "win32":
                    # En Windows no hay SIGSTOP, usamos otro método
                    # Para simplificar, detenemos y reiniciamos en la posición actual
                    self._stop_current()
                    self._is_paused = True
                    self.logger.info(f"File playback paused at {self._current_position:.2f}s")
                else:
                    os.kill(self._ffmpeg_proc.pid, signal.SIGSTOP)
                    self._is_paused = True
                    self.logger.info(f"File playback paused at {self._current_position:.2f}s")
            except Exception as e:
                self.logger.error(f"Failed to pause: {e}")

    def play(self) -> None:
        """Reanudar la reproducción del archivo."""
        if self._is_paused:
            if sys.platform == "win32":
                # En Windows, reiniciamos desde la posición actual
                self._restart_from_position(self._current_position)
            else:
                import signal
                try:
                    if self._ffmpeg_proc:
                        os.kill(self._ffmpeg_proc.pid, signal.SIGCONT)
                    self._is_paused = False
                    self.logger.info("File playback resumed")
                except Exception as e:
                    self.logger.error(f"Failed to resume: {e}")
            self._is_paused = False

    def seek(self, position: float) -> None:
        """Mover la reproducción a una posición específica (en segundos)."""
        if not self._file_path or not os.path.exists(self._file_path):
            self.logger.error("Cannot seek: file not configured or not found")
            return
            
        # Obtener duración si no la tenemos
        if self._file_duration == 0.0:
            self._file_duration = get_video_duration(self._file_path) or 0.0
            
        # Validar posición
        position = max(0, min(position, self._file_duration))
        self._current_position = position
        
        # Reiniciar desde la nueva posición
        self._restart_from_position(position)
        self.logger.info(f"Seeked to position: {position:.2f}s")

    def _restart_from_position(self, position: float) -> None:
        """Reiniciar FFmpeg desde una posición específica."""
        self._stop_current()
        time.sleep(0.5)
        
        # Limpiar chunks antiguos
        if self._chunks_dir:
            for f in glob.glob(os.path.join(self._chunks_dir, "chunk_*.ts")):
                try:
                    os.remove(f)
                except OSError:
                    pass
        
        self._last_chunk_index = -1
        self._cumulative_duration = position  # Ajustar duración acumulada
        self._file_finished = False
        
        # Reconstruir comando FFmpeg con -ss para start time
        chunk_pattern = os.path.join(self._chunks_dir, "chunk_%06d.ts")
        cmd = [self._ffmpeg_path, "-y"]
        
        # Añadir hwaccel
        if self._hwaccel_enabled:
            if self._gpu_info.get("nvenc"):
                cmd.extend(["-hwaccel", "cuda", "-hwaccel_device", self._hwaccel_device])
            elif self._gpu_info.get("qsv"):
                cmd.extend(["-hwaccel", "qsv", "-hwaccel_device", self._hwaccel_device])
            elif self._gpu_info.get("vaapi"):
                cmd.extend(["-hwaccel", "vaapi"])
        
        # Input con seek position
        cmd.extend([
            "-ss", str(position),  # Seek al inicio
            "-i", self._file_path,
            "-c", "copy",
            "-f", "segment",
            "-segment_time", str(self._chunk_duration),
            "-segment_format", "mpegts",
            "-reset_timestamps", "1",
            "-strftime", "0",
        ])
        
        if self._loop:
            cmd.extend(["-stream_loop", "-1"])
        
        if self._speed != 1.0:
            cmd.extend(["-filter:v", f"setpts={1.0 / self._speed}*PTS"])
        
        cmd.append(chunk_pattern)
        
        self.logger.info(f"Restarting file input from {position:.2f}s: {self._file_path}")
        
        self._ffmpeg_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            ),
        )
        
        self._monitor_thread = threading.Thread(
            target=self._monitor_ffmpeg,
            daemon=True,
            name="file-input-monitor",
        )
        self._monitor_thread.start()

    def start(self) -> None:
        """Iniciar lectura del archivo."""
        if not self._file_path:
            raise ValueError("File path not configured")

        if not os.path.exists(self._file_path):
            raise FileNotFoundError(f"File not found: {self._file_path}")

        self._stop_current()
        time.sleep(0.5)

        self._last_chunk_index = -1
        self._file_finished = False
        self._ffmpeg_path = ensure_ffmpeg()

        # Crear directorio de chunks
        self._chunks_dir = os.path.join(self._output_dir or "./output", "chunks")
        os.makedirs(self._chunks_dir, exist_ok=True)

        # Detectar soporte GPU para hwaccel
        from core.ffmpeg_utils import check_gpu_support
        self._gpu_info = check_gpu_support(self._ffmpeg_path)

        # Habilitar hwaccel si hay GPU disponible
        if self._gpu_info.get("nvenc"):
            self._hwaccel_enabled = True
        elif self._gpu_info.get("qsv"):
            self._hwaccel_enabled = True
        elif self._gpu_info.get("vaapi"):
            self._hwaccel_enabled = True
        else:
            self._hwaccel_enabled = False

        # Limpiar chunks antiguos
        for f in glob.glob(os.path.join(self._chunks_dir, "chunk_*.ts")):
            try:
                os.remove(f)
            except OSError:
                pass

        # Reset cumulative duration tracking
        self._cumulative_duration = 0.0

        # Comando FFmpeg para segmentar archivo
        chunk_pattern = os.path.join(self._chunks_dir, "chunk_%06d.ts")

        # Construir comando con soporte hwaccel
        cmd = [self._ffmpeg_path, "-y"]

        # Añadir hwaccel si hay GPU disponible
        if self._hwaccel_enabled:
            if self._gpu_info.get("nvenc"):
                cmd.extend(["-hwaccel", "cuda", "-hwaccel_device", self._hwaccel_device])
            elif self._gpu_info.get("qsv"):
                cmd.extend(["-hwaccel", "qsv", "-hwaccel_device", self._hwaccel_device])
            elif self._gpu_info.get("vaapi"):
                cmd.extend(["-hwaccel", "vaapi"])

        # Resto del comando
        cmd.extend([
            "-i", self._file_path,
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
        ])

        if self._loop:
            cmd.extend(["-stream_loop", "-1"])

        if self._speed != 1.0:
            cmd.extend(["-filter:v", f"setpts={1.0 / self._speed}*PTS"])

        cmd.append(chunk_pattern)

        self.logger.info(f"Starting file input: {self._file_path}")

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

        # Hilo monitor
        self._monitor_thread = threading.Thread(
            target=self._monitor_ffmpeg,
            daemon=True,
            name="file-input-monitor",
        )
        self._monitor_thread.start()

        self.logger.info(f"File input started: {self._file_path}")

    def stop(self) -> None:
        """Detener lectura."""
        self._stop_current()
        self.logger.info("File input stopped")

    def _stop_current(self) -> None:
        """Detener proceso actual."""
        if self._ffmpeg_proc:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self._ffmpeg_proc.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    self._ffmpeg_proc.terminate()
                self._ffmpeg_proc.wait(timeout=2)
            except Exception:
                pass
            finally:
                self._ffmpeg_proc = None

    def get_next_chunk(self) -> Optional[PipelineData]:
        """Obtener siguiente chunk del archivo."""
        if not self._chunks_dir:
            return None

        # Verificar si el proceso terminó (archivo terminó)
        if self._ffmpeg_proc and self._ffmpeg_proc.poll() is not None:
            if not self._loop:
                self._file_finished = True

        chunks = sorted(glob.glob(os.path.join(self._chunks_dir, "chunk_*.ts")))

        if not chunks:
            return None

        # Excluir el último (todavía escribiéndose)
        if len(chunks) < 2:
            return None

        # Encontrar siguiente chunk no procesado
        processable = []
        for chunk_path in chunks[:-1]:
            fname = os.path.basename(chunk_path)
            try:
                idx = int(fname.replace("chunk_", "").replace(".ts", ""))
                if idx > self._last_chunk_index:
                    processable.append((idx, chunk_path))
            except ValueError:
                continue

        if not processable:
            # Si no hay más chunks y el archivo terminó, reiniciar si hay loop
            if self._loop and self._file_finished:
                self._file_finished = False
                self._last_chunk_index = -1
                # Limpiar y reiniciar
                for f in glob.glob(os.path.join(self._chunks_dir, "chunk_*.ts")):
                    try:
                        os.remove(f)
                    except OSError:
                        pass
                self.start()
            return None

        # Tomar el más antiguo
        processable.sort()
        idx, chunk_path = processable[0]
        self._last_chunk_index = idx

        # Medir duración real
        actual_duration = get_video_duration(chunk_path) or self._chunk_duration

        # Validate duration (warn if FFmpeg segment duration differs too much)
        duration_diff = abs(actual_duration - self._chunk_duration)
        if duration_diff > 0.05:  # 50ms threshold
            self.logger.warning(
                f"Chunk {idx} duration {actual_duration:.3f}s differs from "
                f"expected {self._chunk_duration:.3f}s by {duration_diff * 1000:.1f}ms"
            )

        # Set cumulative duration BEFORE processing
        chunk_cumulative = self._cumulative_duration

        # Update cumulative for next chunk
        self._cumulative_duration += actual_duration

        # Update current position based on cumulative duration
        self._current_position = chunk_cumulative + actual_duration

        self.logger.debug(
            f"New chunk from file: {chunk_path} (cumulative: {chunk_cumulative:.3f}s, position: {self._current_position:.3f}s)"
        )

        return PipelineData(
            chunk_index=idx,
            timestamp=time.time(),
            duration=actual_duration,
            cumulative_duration=chunk_cumulative,
            video_chunk_path=chunk_path,
        )

    def is_receiving(self) -> bool:
        """Verificar si está procesando."""
        if self._file_finished and not self._loop:
            return False
        if self._ffmpeg_proc is None:
            return False
        return self._ffmpeg_proc.poll() is None

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
        """Monitorear stderr de FFmpeg."""
        if not self._ffmpeg_proc or not self._ffmpeg_proc.stderr:
            return

        try:
            for line in self._ffmpeg_proc.stderr:
                line = line.strip()
                if line:
                    if "error" in line.lower():
                        self.logger.error(f"[FFmpeg] {line}")
                    elif "warning" in line.lower():
                        self.logger.warning(f"[FFmpeg] {line}")
        except Exception:
            pass


# Auto-registro en factory
from core.io_factory import InputFactory

InputFactory.register("file", FileInput)
