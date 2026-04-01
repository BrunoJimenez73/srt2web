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
from pathlib import Path
from typing import Optional

from core.input_source import InputSource
from core.module_base import PipelineData
from core.ffmpeg_utils import ensure_ffmpeg, get_video_duration


class SRTInput(InputSource):
    """
    Recibe un stream SRT y produce chunks de video segmentados.

    Utiliza FFmpeg como subprocess para recibir el stream SRT
    y escribir segmentos de duración fija.
    """

    def __init__(self, config: dict):
        super().__init__("srt", config)

        # Configuración SRT
        self._srt_port = config.get("listen_port", 9000)
        self._srt_mode = config.get("mode", "listener")
        self._srt_latency_ms = config.get("latency_ms", 1000)
        self._srt_caller_address = config.get("caller_address", "")

        # Configuración de chunks
        self._chunk_duration = config.get("chunk_duration_sec", 15)

        # Estado interno
        self._ffmpeg_path: Optional[str] = None
        self._ffmpeg_proc: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._chunks_dir: str = ""
        self._last_chunk_index: int = -1
        self._cumulative_duration: float = 0.0  # Track cumulative duration for sync

    def configure(self, config: dict) -> None:
        """Aplicar configuración."""
        self._srt_port = config.get("listen_port", self._srt_port)
        self._srt_mode = config.get("mode", self._srt_mode)
        self._srt_latency_ms = config.get("latency_ms", self._srt_latency_ms)
        self._srt_caller_address = config.get(
            "caller_address", self._srt_caller_address
        )
        self._chunk_duration = config.get("chunk_duration_sec", self._chunk_duration)

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
        """Iniciar receptor SRT."""
        try:
            self.logger.info("Starting SRT input...")
            self._ensure_stopped()
            time.sleep(0.5)

            self._last_chunk_index = -1
            self.logger.info("Getting FFmpeg path...")
            self._ffmpeg_path = ensure_ffmpeg()
            self.logger.info(f"FFmpeg path: {self._ffmpeg_path}")

            # Crear directorio de chunks
            self._chunks_dir = os.path.join(self._output_dir or "./output", "chunks")
            os.makedirs(self._chunks_dir, exist_ok=True)
            self.logger.info(f"Chunks directory: {self._chunks_dir}")

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

            # Hilo monitor
            self._monitor_thread = threading.Thread(
                target=self._monitor_ffmpeg,
                daemon=True,
                name="srt-input-monitor",
            )
            self._monitor_thread.start()

            self.logger.info(f"SRT input started on port {self._srt_port}")
            self.logger.info("SRT input started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start SRT input: {type(e).__name__}: {e}")
            import traceback
            self.logger.error(f"SRT input traceback: {traceback.format_exc()}")
            raise

    def stop(self) -> None:
        """Detener receptor SRT."""
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
            except Exception as e:
                self.logger.debug(f"Process cleanup: {e}")
            finally:
                self._ffmpeg_proc = None

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

    def _monitor_ffmpeg(self) -> None:
        """Monitorear stderr de FFmpeg para logs."""
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
                    else:
                        self.logger.debug(f"[FFmpeg] {line}")
        except Exception:
            pass

    def _ensure_stopped(self) -> None:
        """Asegurar que cualquier proceso anterior esté detenido."""
        # Esto es para limpieza en Windows
        pass


# Auto-registro en factory
from core.io_factory import InputFactory

InputFactory.register("srt", SRTInput)
