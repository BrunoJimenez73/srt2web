"""
Recording Output - Graba el stream procesado a archivos continuos.

Este módulo recibe los datos del pipeline y los muxea en un archivo de video
continuo, con soporte para:
- Grabación continua (un archivo o múltiples archivos)
- Split por tiempo (cada X minutos) o tamaño (cada X MB)
- Re-encoding opcional o passthrough (copy)
- Subtítulos burnt-in o externos
- Codecs: h264_nvenc, libx264, h265, etc.

Configuración (output.recording):
    output_path: Ruta del archivo de salida (default: ./output/recording.mp4)
    format: Formato del contenedor (mp4, mkv, webm)
    codec: Codec de video (h264_nvenc, h265_nvenc, libx264, libx265, copy)
    video_bitrate: Bitrate de video (ej: 5000k) - para CBR
    video_crf: Valor CRF (18-28) - para modo CRF
    quality_mode: crf o cbr
    audio_codec: Codec de audio (aac, opus, copy)
    audio_bitrate: Bitrate de audio (ej: 128k)
    split_mode: none, time, size
    split_value: Minutos (si split_mode=time) o MB (si split_mode=size)
    subtitles: none, burnt, vtt
    video_preset: fast, medium, slow (para encoding)
"""

import os
import glob
import logging
import subprocess
import threading
import time
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from core.output_sink import OutputSink
from core.module_base import PipelineData
from core.ffmpeg_utils import ensure_ffmpeg, check_gpu_support


class RecordingOutput(OutputSink):
    """
    Graba el stream procesado a archivos de video continuos.

    Utiliza FFmpeg para muxear video + audio + subtítulos en tiempo real.
    Soporta aceleración por hardware (NVENC, QSV, AMF) y split automático.
    """

    def __init__(self, config: dict):
        super().__init__("recording", config)

        self._ffmpeg_path: Optional[str] = None
        self._process: Optional[subprocess.Popen] = None
        self._input_pipe: Optional[str] = None
        self._output_path: str = ""
        self._current_file: str = ""
        self._segment_index: int = 0
        self._lock = threading.Lock()
        self._running = False
        self._gpu_info = {"nvenc": False, "qsv": False, "amf": False}

        self._last_process_time_ms: float = 0.0
        self._processed_chunks: int = 0
        self._bytes_written: int = 0
        self._start_time: float = 0.0
        self._file_start_time: float = 0.0
        self._pending_data: Optional[PipelineData] = None

        self._apply_config(config)

    def _apply_config(self, config: dict) -> None:
        """Aplicar configuración."""
        self._output_path = config.get("output_path", "./output/recording.mp4")
        self._format = config.get("format", "mp4")
        self._codec = config.get("codec", "copy")
        self._video_bitrate = config.get("video_bitrate", "5000k")
        self._video_crf = config.get("video_crf", 23)
        self._quality_mode = config.get("quality_mode", "cbr")
        self._audio_codec = config.get("audio_codec", "copy")
        self._audio_bitrate = config.get("audio_bitrate", "128k")
        self._split_mode = config.get("split_mode", "none")
        self._split_value = config.get("split_value", 600)
        self._subtitles = config.get("subtitles", "none")
        self._video_preset = config.get("video_preset", "fast")

        self.logger.info(
            f"RecordingOutput configured: format={self._format}, codec={self._codec}, "
            f"quality={self._quality_mode}, split={self._split_mode}:{self._split_value}"
        )

    def configure(self, config: dict) -> None:
        """Aplicar nueva configuración (para hot-reload)."""
        self._apply_config(config)
        self.logger.info("RecordingOutput reconfigured")

    def get_stream_info(self) -> dict:
        """Obtener información del stream."""
        return {
            "type": "recording",
            "output_path": self._output_path,
            "current_file": self._current_file,
            "format": self._format,
            "codec": self._codec,
            "quality_mode": self._quality_mode,
            "split_mode": self._split_mode,
            "subtitles": self._subtitles,
            "processed_chunks": self._processed_chunks,
            "bytes_written": self._bytes_written,
            "recording_duration_sec": time.time() - self._file_start_time if self._file_start_time else 0,
        }

    def get_status(self) -> dict:
        """Obtener estado del output."""
        return {
            "state": "running" if self._running else "idle",
            "enabled": True,
            "processed_chunks": self._processed_chunks,
            "last_process_time_ms": self._last_process_time_ms,
            "output_path": self._output_path,
            "current_file": self._current_file,
            "format": self._format,
            "codec": self._codec,
            "quality_mode": self._quality_mode,
            "split_mode": self._split_mode,
            "subtitles": self._subtitles,
            "bytes_written": self._bytes_written,
            "recording_duration_sec": time.time() - self._file_start_time if self._file_start_time else 0,
            "extra": {
                "encoder": self._codec,
                "video_bitrate": self._video_bitrate if self._quality_mode == "cbr" else f"CRF{self._video_crf}",
                "audio_codec": self._audio_codec,
                "audio_bitrate": self._audio_bitrate,
            }
        }

    def _get_ffmpeg_cmd(self, output_file: str) -> List[str]:
        """Construir comando FFmpeg según configuración."""
        cmd = [self._ffmpeg_path, "-y"]

        input_video = None
        input_audio = None
        input_subs = None

        if self._pending_data:
            if hasattr(self._pending_data, 'video_chunk_path') and self._pending_data.video_chunk_path:
                input_video = self._pending_data.video_chunk_path
            if hasattr(self._pending_data, 'mixed_audio_path') and self._pending_data.mixed_audio_path:
                input_audio = self._pending_data.mixed_audio_path
            if hasattr(self._pending_data, 'subtitles_path') and self._pending_data.subtitles_path:
                input_subs = self._pending_data.subtitles_path

        input_count = 0

        if input_video and os.path.exists(input_video):
            cmd.extend(["-i", input_video])
            input_count += 1
        else:
            self.logger.warning(f"Video input not found, cannot record: {input_video}")
            return []

        if input_audio and os.path.exists(input_audio):
            cmd.extend(["-i", input_audio])
            input_count += 1

        if input_subs and os.path.exists(input_subs) and self._subtitles == "burnt":
            cmd.extend(["-i", input_subs])
            input_count += 1

        map_args = []

        if input_count >= 1:
            map_args.extend(["-map", "0:v:0"])

        if input_count >= 2:
            map_args.extend(["-map", "1:a:0"])

        if input_count >= 3 and self._subtitles == "burnt":
            map_args.extend(["-map", "2:s:0"])

        cmd.extend(map_args)

        video_codec = self._codec
        audio_codec = self._audio_codec

        if video_codec != "copy":
            if video_codec == "h264_nvenc":
                cmd.extend(["-c:v", "h264_nvenc", "-preset", self._video_preset])
                if self._quality_mode == "cbr":
                    cmd.extend(["-b:v", self._video_bitrate])
                else:
                    cmd.extend(["-crf", str(self._video_crf), "-rc", "vbr"])
            elif video_codec == "h265_nvenc":
                cmd.extend(["-c:v", "hevc_nvenc", "-preset", self._video_preset])
                if self._quality_mode == "cbr":
                    cmd.extend(["-b:v", self._video_bitrate])
                else:
                    cmd.extend(["-crf", str(self._video_crf), "-rc", "vbr"])
            elif video_codec == "libx264":
                cmd.extend(["-c:v", "libx264", "-preset", self._video_preset])
                if self._quality_mode == "cbr":
                    cmd.extend(["-b:v", self._video_bitrate])
                else:
                    cmd.extend(["-crf", str(self._video_crf)])
            else:
                cmd.extend(["-c:v", "copy"])
        else:
            cmd.extend(["-c:v", "copy"])

        if audio_codec != "copy":
            if audio_codec == "aac":
                cmd.extend(["-c:a", "aac", "-b:a", self._audio_bitrate])
            elif audio_codec == "opus":
                cmd.extend(["-c:a", "libopus", "-b:a", self._audio_bitrate])
            else:
                cmd.extend(["-c:a", "copy"])
        else:
            cmd.extend(["-c:a", "copy"])

        if self._subtitles == "burnt" and input_count >= 3:
            cmd.extend(["-scodec", "mov_text"])
        elif self._subtitles == "vtt":
            pass

        cmd.extend([
            "-movflags", "+faststart",
            "-f", self._format,
            output_file
        ])

        self.logger.info(f"FFmpeg command: {' '.join(filter(None, cmd))}")
        return cmd

    def _should_split(self) -> bool:
        """Determinar si se debe hacer split."""
        if self._split_mode == "none":
            return False

        if self._split_mode == "time":
            elapsed = time.time() - self._file_start_time
            return elapsed >= self._split_value

        elif self._split_mode == "size":
            if os.path.exists(self._current_file):
                size_mb = os.path.getsize(self._current_file) / (1024 * 1024)
                return size_mb >= self._split_value

        return False

    def _get_next_output_path(self) -> str:
        """Obtener siguiente ruta de salida (para split)."""
        base, ext = os.path.splitext(self._output_path)
        if self._segment_index == 0:
            return self._output_path
        return f"{base}_{self._segment_index:03d}{ext}"

    def start(self) -> None:
        """Iniciar la grabación."""
        self._ffmpeg_path = ensure_ffmpeg()
        self._gpu_info = check_gpu_support(self._ffmpeg_path)
        self._running = True
        self._processed_chunks = 0
        self._bytes_written = 0
        self._segment_index = 0
        self._start_time = time.time()
        self._file_start_time = time.time()

        os.makedirs(os.path.dirname(self._output_path) or ".", exist_ok=True)

        self._current_file = self._get_next_output_path()
        self.logger.info(f"Recording started: {self._current_file}")

    def stop(self) -> None:
        """Detener la grabación."""
        self._running = False

        if self._process:
            try:
                self._process.stdin.flush()
                self._process.stdin.close()
                self._process.wait(timeout=5)
            except Exception as e:
                self.logger.error(f"Error stopping FFmpeg: {e}")
                try:
                    self._process.terminate()
                except:
                    pass
            finally:
                self._process = None

        duration = time.time() - self._start_time
        self.logger.info(
            f"Recording stopped. Processed {self._processed_chunks} chunks, "
            f"{self._bytes_written / (1024*1024):.1f} MB, duration: {duration:.1f}s"
        )

    def write(self, data: PipelineData) -> None:
        """Escribir datos al archivo de grabación."""
        if not self._running:
            return

        start_time = time.perf_counter()

        self._pending_data = data

        if self._should_split():
            self._do_split()

        self._current_file = self._get_next_output_path()

        cmd = self._get_ffmpeg_cmd(self._current_file)
        if not cmd:
            self.logger.error("Failed to build FFmpeg command")
            return

        try:
            if self._segment_index == 0 or not self._process:
                if self._process:
                    try:
                        self._process.stdin.flush()
                        self._process.stdin.close()
                        self._process.wait(timeout=5)
                    except:
                        pass

                self._process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self._file_start_time = time.time()
                self.logger.info(f"Started new recording segment: {self._current_file}")

            if self._process and self._process.stdin:
                self._process.stdin.write(b'\x00')
                self._process.stdin.flush()

            if os.path.exists(self._current_file):
                self._bytes_written += os.path.getsize(self._current_file)

            self._processed_chunks += 1

        except Exception as e:
            self.logger.error(f"Error writing to recording: {e}")

        elapsed = (time.perf_counter() - start_time) * 1000
        self._last_process_time_ms = elapsed

    def _do_split(self) -> None:
        """Realizar split del archivo."""
        if self._process:
            try:
                self._process.stdin.flush()
                self._process.stdin.close()
                self._process.wait(timeout=5)
            except Exception as e:
                self.logger.warning(f"Error closing current segment: {e}")
            finally:
                self._process = None

        self._segment_index += 1
        self.logger.info(f"Splitting recording: segment {self._segment_index}")


def _register():
    """Auto-register this output module."""
    try:
        from core.io_factory import OutputFactory
        OutputFactory.register("recording", RecordingOutput)
    except ImportError:
        pass


_register()