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
import logging
import subprocess
import threading
import time
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from core.output_sink import OutputSink
from core.module_base import PipelineData
from core.ffmpeg_utils import ensure_ffmpeg, check_gpu_support


class RecordingOutput(OutputSink):
    """
    Graba el stream procesado a archivos de video continuos.

    Estrategia: copia cada video + audio chunk a directorio temporal.
    Al detener (stop()), concatena todos los chunks en un archivo usando
    concat demuxer de FFmpeg.
    """

    def __init__(self, config: dict):
        super().__init__("recording", config)

        self._ffmpeg_path: Optional[str] = None
        self._process: Optional[subprocess.Popen] = None
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
        self._recording_dir: str = ""
        self._saved_video_paths: List[str] = []
        self._saved_audio_paths: List[str] = []

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

    def set_output_dir(self, output_dir: str) -> None:
        """Set output directory and prepare recording temp dir."""
        super().set_output_dir(output_dir)
        self._recording_dir = os.path.join(output_dir, "recording")
        os.makedirs(self._recording_dir, exist_ok=True)
        self.logger.info(f"Recording temp dir: {self._recording_dir}")

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
                "using_gpu": self._codec in ["h264_nvenc", "h265_nvenc"],
                "gpu_info": self._gpu_info,
                "saved_videos": len(self._saved_video_paths),
                "saved_audios": len(self._saved_audio_paths),
            }
        }

    def _build_ffmpeg_cmd(self, output_file: str, input_video: Optional[str],
                         input_audio: Optional[str], input_subs: Optional[str]) -> List[str]:
        """Construir comando FFmpeg según configuración."""
        cmd = [self._ffmpeg_path, "-y"]

        input_count = 0

        if input_video and os.path.exists(input_video):
            cmd.extend(["-i", input_video])
            input_count += 1
        else:
            self.logger.debug(f"Video input not found: {input_video}")

        if input_audio and os.path.exists(input_audio):
            cmd.extend(["-i", input_audio])
            input_count += 1

        if input_subs and os.path.exists(input_subs) and self._subtitles == "burnt":
            cmd.extend(["-i", input_subs])
            input_count += 1

        if input_count == 0:
            self.logger.warning("No inputs available for recording")
            return []

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

        cmd.extend([
            "-movflags", "+faststart",
            "-f", self._format,
            output_file
        ])

        self.logger.debug(f"FFmpeg cmd: {' '.join(filter(None, cmd))}")
        return cmd

    def _get_ffmpeg_cmd(self, output_file: str) -> List[str]:
        """Compatibilidad tests: usa pending_data para construir comando."""
        input_video = getattr(self._pending_data, 'video_chunk_path', None) if self._pending_data else None
        input_audio = getattr(self._pending_data, 'mixed_audio_path', None) if self._pending_data else None
        input_subs = getattr(self._pending_data, 'subtitles_path', None) if self._pending_data else None
        return self._build_ffmpeg_cmd(output_file, input_video, input_audio, input_subs)

    def _get_next_output_path(self) -> str:
        """Obtener siguiente ruta de salida (para split)."""
        base, ext = os.path.splitext(self._output_path)
        if self._segment_index == 0:
            return self._output_path
        return f"{base}_{self._segment_index:03d}{ext}"

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
        self._saved_video_paths.clear()
        self._saved_audio_paths.clear()

        os.makedirs(os.path.dirname(self._output_path) or ".", exist_ok=True)

        if not self._recording_dir:
            self._recording_dir = os.path.join(self._output_dir or "./output", "recording")
            os.makedirs(self._recording_dir, exist_ok=True)

        self._current_file = self._get_next_output_path()
        self.logger.info(f"Recording started: {self._current_file}")

    def stop(self) -> None:
        """Concatenar todos los chunks en un archivo y limpiar."""
        self._running = False

        if self._process:
            try:
                self._process.stdin.flush()
                self._process.stdin.close()
                self._process.wait(timeout=5)
            except Exception as e:
                self.logger.warning(f"Error closing FFmpeg: {e}")
                try:
                    self._process.terminate()
                except:
                    pass
            finally:
                self._process = None

        if self._saved_video_paths:
            self._do_concat()

        for f in self._saved_video_paths + self._saved_audio_paths:
            try:
                os.remove(f)
            except OSError:
                pass
        self._saved_video_paths.clear()
        self._saved_audio_paths.clear()

        if self._recording_dir and os.path.exists(self._recording_dir):
            try:
                os.rmdir(self._recording_dir)
            except OSError:
                pass

        duration = time.time() - self._start_time
        self.logger.info(
            f"Recording stopped. {self._processed_chunks} chunks -> {self._output_path}, "
            f"{self._bytes_written / (1024*1024):.1f} MB, {duration:.1f}s"
        )

    def _do_concat(self) -> None:
        """Concatenar chunks guardados en un archivo usando concat demuxer."""
        if not self._saved_video_paths:
            return

        output_file = os.path.abspath(self._output_path)

        if os.path.exists(output_file):
            base, ext = os.path.splitext(output_file)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = f"{base}_{ts}{ext}"
            try:
                os.rename(output_file, backup)
                self.logger.info(f"Previous recording backed up: {backup}")
            except Exception as e:
                self.logger.warning(f"Could not backup previous: {e}")

        concat_list = os.path.join(self._recording_dir, "concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for vp in self._saved_video_paths:
                if os.path.exists(vp):
                    f.write(f"file '{vp}'\n")

        cmd = [
            self._ffmpeg_path, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
        ]

        has_audio = bool(self._saved_audio_paths)

        if has_audio:
            audio_concat = os.path.join(self._recording_dir, "audio_concat.txt")
            with open(audio_concat, "w", encoding="utf-8") as f:
                for ap in self._saved_audio_paths:
                    if os.path.exists(ap):
                        f.write(f"file '{ap}'\n")
            cmd.extend(["-f", "concat", "-safe", "0", "-i", audio_concat])

        if has_audio:
            cmd.extend(["-map", "0:v", "-map", "1:a"])
        else:
            cmd.extend(["-map", "0:v"])

        if self._codec == "copy":
            cmd.extend(["-c:v", "copy"])
        else:
            cmd.extend(["-c:v", self._codec])
            if self._quality_mode == "crf":
                cmd.extend(["-crf", str(self._video_crf)])
            else:
                cmd.extend(["-b:v", self._video_bitrate])
            cmd.extend(["-preset", self._video_preset])

        if self._audio_codec == "copy":
            cmd.extend(["-c:a", "copy"])
        else:
            cmd.extend(["-c:a", self._audio_codec, "-b:a", self._audio_bitrate])

        cmd.append(output_file)

        self.logger.info(f"Concatenating {len(self._saved_video_paths)} chunks -> {output_file}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            if result.returncode == 0:
                size = os.path.getsize(output_file)
                self._bytes_written = size
                self.logger.info(f"Recording saved: {output_file} ({size / (1024*1024):.1f} MB)")
            else:
                self.logger.error(f"Concat failed: {result.stderr[-500:]}")
        except subprocess.TimeoutExpired:
            self.logger.error("Concat timed out")
        except Exception as e:
            self.logger.error(f"Concat error: {e}")

    def write(self, data: PipelineData) -> None:
        """Copiar video + audio chunks a directorio temporal para concat posterior."""
        if not self._running:
            self.logger.debug(f"Recording write: not running, skipping")
            return

        self.logger.debug(f"Recording write: processing chunk {data.chunk_index}")

        if not self._recording_dir:
            self._recording_dir = os.path.join(self._output_dir or "./output", "recording")
            os.makedirs(self._recording_dir, exist_ok=True)
            self.logger.info(f"Recording dir: {self._recording_dir}")

        chunk_idx = data.chunk_index

        # Check for video_path (set by VideoMuxer before delete) or video_chunk_path
        video_path = getattr(data, 'video_path', None) or getattr(data, 'video_chunk_path', None)
        audio_path = getattr(data, 'mixed_audio_path', None) or getattr(data, 'audio_path', None)
        
        self.logger.debug(f"Recording: video_path={video_path}, audio_path={audio_path}")
        
        if video_path and os.path.exists(video_path):
            saved_video = os.path.join(self._recording_dir, f"rec_v_{chunk_idx:06d}.ts")
            try:
                shutil.copy2(video_path, saved_video)
                self._saved_video_paths.append(saved_video)
                self.logger.debug(f"Recording: saved video {chunk_idx}")
            except Exception as e:
                self.logger.warning(f"Could not copy video chunk: {e}")

        if audio_path and os.path.exists(audio_path):
            saved_audio = os.path.join(self._recording_dir, f"rec_a_{chunk_idx:06d}.wav")
            try:
                shutil.copy2(audio_path, saved_audio)
                self._saved_audio_paths.append(saved_audio)
                self.logger.debug(f"Recording: saved audio {chunk_idx}")
            except Exception as e:
                self.logger.warning(f"Could not copy audio chunk: {e}")

        self._processed_chunks += 1
        self.logger.debug(f"Recording: saved chunk {chunk_idx}")

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