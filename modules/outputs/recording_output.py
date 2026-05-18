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
    subtitles: none, burnt, track, vtt (default: track)
    video_preset: fast, medium, slow (para encoding)
"""

import os
import shutil
import subprocess
import threading
import time
from datetime import datetime
from typing import Optional

from core.ffmpeg_utils import check_gpu_support, ensure_ffmpeg
from core.module_base import ModuleState, ModuleStatus, PipelineData
from core.output_sink import OutputSink
from core.subprocess_utils import get_creation_flags


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
        self._gpu_info = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False, "videotoolbox": False}

        self._last_process_time_ms: float = 0.0
        self._processed_chunks: int = 0
        self._bytes_written: int = 0
        self._start_time: float = 0.0
        self._file_start_time: float = 0.0
        self._pending_data: Optional[PipelineData] = None
        self._recording_dir: str = ""
        self._saved_video_paths: list[str] = []
        self._saved_audio_paths: list[str] = []
        self._latest_subs_path: Optional[str] = None

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
        self._subtitles = config.get("subtitles", "track")
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

    def get_status(self) -> ModuleStatus:
        """Obtener estado del output."""
        recording_duration = time.time() - self._file_start_time if self._file_start_time else 0
        video_bitrate = self._video_bitrate if self._quality_mode == "cbr" else f"CRF{self._video_crf}"

        return ModuleStatus(
            name="recording_output",
            state=ModuleState.RUNNING if self._running else ModuleState.IDLE,
            enabled=True,
            processed_chunks=self._processed_chunks,
            last_process_time_ms=self._last_process_time_ms,
            extra={
                "output_path": self._output_path,
                "current_file": self._current_file,
                "format": self._format,
                "codec": self._codec,
                "quality_mode": self._quality_mode,
                "split_mode": self._split_mode,
                "subtitles": self._subtitles,
                "bytes_written": self._bytes_written,
                "recording_duration_sec": recording_duration,
                "encoder": self._codec,
                "video_bitrate": video_bitrate,
                "audio_codec": self._audio_codec,
                "audio_bitrate": self._audio_bitrate,
                "using_gpu": self._codec in ["h264_nvenc", "h265_nvenc"],
                "gpu_info": self._gpu_info,
                "saved_videos": len(self._saved_video_paths),
                "saved_audios": len(self._saved_audio_paths),
            },
        ).to_dict()

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
        rec_dir_abs = os.path.abspath(self._recording_dir)
        with open(concat_list, "w", encoding="utf-8") as f:
            for vp in self._saved_video_paths:
                if os.path.exists(vp):
                    vp_abs = os.path.abspath(vp)
                    vp_rel = os.path.relpath(vp_abs, rec_dir_abs).replace("\\", "/")
                    f.write(f"file '{vp_rel}'\n")

        cmd = [
            self._ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list,
        ]

        has_audio = bool(self._saved_audio_paths)

        if has_audio:
            audio_concat = os.path.join(self._recording_dir, "audio_concat.txt")
            with open(audio_concat, "w", encoding="utf-8") as f:
                for ap in self._saved_audio_paths:
                    if os.path.exists(ap):
                        ap_abs = os.path.abspath(ap)
                        ap_rel = os.path.relpath(ap_abs, rec_dir_abs).replace("\\", "/")
                        f.write(f"file '{ap_rel}'\n")
            cmd.extend(["-f", "concat", "-safe", "0", "-i", audio_concat])

        # Subtitle handling: burnt (render into video), track (mux as subtitle stream), vtt (save as sidecar)
        subs_srt = None
        if self._subtitles in ("burnt", "track"):
            subs_srt = self._concat_subtitle_chunks()
            if subs_srt and os.path.exists(subs_srt):
                cmd.extend(["-i", subs_srt])

        has_subs_input = subs_srt is not None and os.path.exists(subs_srt) if subs_srt else False

        # Map inputs
        if has_audio and has_subs_input:
            cmd.extend(["-map", "0:v", "-map", "1:a"])
            if self._subtitles == "track":
                cmd.extend(["-map", "2:s"])
        elif has_audio:
            cmd.extend(["-map", "0:v", "-map", "1:a"])
        elif has_subs_input:
            cmd.extend(["-map", "0:v"])
            if self._subtitles == "track":
                cmd.extend(["-map", "1:s"])
        else:
            cmd.extend(["-map", "0:v"])

        # Video codec - burnt subtitles require re-encoding with filter
        if self._subtitles == "burnt" and has_subs_input:
            subs_path_escaped = subs_srt.replace("\\", "/").replace(":", "\\\\:")
            cmd.extend(["-vf", f"subtitles='{subs_path_escaped}'"])
            if self._codec != "copy":
                cmd.extend(["-c:v", self._codec])
                if self._quality_mode == "crf":
                    cmd.extend(["-crf", str(self._video_crf)])
                else:
                    cmd.extend(["-b:v", self._video_bitrate])
                cmd.extend(["-preset", self._video_preset])
            else:
                # copy codec incompatible with subtitle filter, force libx264
                cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "23"])
        elif self._codec == "copy":
            cmd.extend(["-c:v", "copy"])
        else:
            cmd.extend(["-c:v", self._codec])
            if self._quality_mode == "crf":
                cmd.extend(["-crf", str(self._video_crf)])
            else:
                cmd.extend(["-b:v", self._video_bitrate])
            cmd.extend(["-preset", self._video_preset])

        # Audio codec
        if self._audio_codec == "copy":
            cmd.extend(["-c:a", "copy"])
        else:
            cmd.extend(["-c:a", self._audio_codec, "-b:a", self._audio_bitrate])

        # Subtitle codec (track mode)
        if self._subtitles == "track" and has_subs_input:
            cmd.extend(["-c:s", "mov_text"])

        cmd.append(output_file)

        self.logger.info(
            f"Concatenating {len(self._saved_video_paths)} chunks -> {output_file}"
            + (" + subtitles" if has_subs_input else "")
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=get_creation_flags(),
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
        # Store data for later use in concat (to get subtitles_path, etc)
        self._pending_data = data

        if not self._running:
            self.logger.debug("Recording write: not running, skipping")
            return

        self.logger.debug(f"Recording write: processing chunk {data.chunk_index}")

        if not self._recording_dir:
            self._recording_dir = os.path.join(self._output_dir or "./output", "recording")
            os.makedirs(self._recording_dir, exist_ok=True)
            self.logger.info(f"Recording dir: {self._recording_dir}")

        chunk_idx = data.chunk_index

        # Track subtitle path for final concat
        subs_path = getattr(data, "subtitles_path", None)
        if subs_path and os.path.exists(subs_path):
            self._latest_subs_path = subs_path

        # Check for video_path (set by VideoMuxer) or video_chunk_path (from input)
        video_path = getattr(data, "video_path", None) or getattr(data, "video_chunk_path", None)
        audio_path = getattr(data, "mixed_audio_path", None) or getattr(data, "audio_path", None)

        self.logger.info(f"[Recording] chunk {chunk_idx}: video={bool(video_path)}, audio={bool(audio_path)}")

        total_bytes = 0
        errors = []

        if video_path and os.path.exists(video_path):
            saved_video = os.path.join(self._recording_dir, f"rec_v_{chunk_idx:06d}.ts")
            try:
                shutil.copy2(video_path, saved_video)
                self._saved_video_paths.append(saved_video)
                total_bytes += os.path.getsize(saved_video)
                self.logger.info(f"[Recording] saved video chunk {chunk_idx}")
            except Exception as e:
                self.logger.warning(f"Could not copy video chunk: {e}")
                errors.append(str(e))
        elif video_path:
            self.logger.warning(f"[Recording] video path exists but file not found: {video_path}")
        else:
            self.logger.debug(f"[Recording] no video path for chunk {chunk_idx}")

        if audio_path and os.path.exists(audio_path):
            saved_audio = os.path.join(self._recording_dir, f"rec_a_{chunk_idx:06d}.wav")
            try:
                shutil.copy2(audio_path, saved_audio)
                self._saved_audio_paths.append(saved_audio)
                total_bytes += os.path.getsize(saved_audio)
                self.logger.info(f"[Recording] saved audio chunk {chunk_idx}")
            except Exception as e:
                self.logger.warning(f"Could not copy audio chunk: {e}")
                errors.append(str(e))

        self._processed_chunks += 1

        # Update health tracking
        if errors:
            self._set_error("; ".join(errors))
        else:
            self._update_write_stats(total_bytes)
            self._clear_error()

    def _concat_subtitle_chunks(self) -> Optional[str]:
        """Convert latest VTT subtitle file to SRT for recording."""
        # Check the stored subtitle path first
        if self._latest_subs_path and os.path.exists(self._latest_subs_path):
            vtt_file = self._latest_subs_path
        else:
            # Fallback: look in subtitles directory
            subs_dir = os.path.join(self._output_dir or "./output", "subtitles")
            vtt_file = os.path.join(subs_dir, "subs.vtt")
            if not os.path.exists(vtt_file):
                self.logger.debug(f"No subtitle file found at {vtt_file}")
                return None

        output_srt = os.path.join(self._recording_dir, "recording_subs.srt")

        try:
            with open(vtt_file, encoding="utf-8") as f:
                content = f.read()

            with open(output_srt, "w", encoding="utf-8") as out:
                seq = 1
                lines = content.split("\n")
                in_timing = False
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith("WEBVTT") or stripped.startswith("NOTE"):
                        continue
                    if "-->" in stripped:
                        in_timing = True
                        # Convert VTT timing (00:00:01.000 --> 00:00:02.000) to SRT (comma separator)
                        timing_line = stripped.replace(".", ",", 2)
                        out.write(f"{seq}\n{timing_line}\n")
                    elif stripped and in_timing:
                        out.write(f"{stripped}\n\n")
                        seq += 1
                    elif stripped == "" or not stripped:
                        in_timing = False

            if seq > 1:
                self.logger.info(f"Converted VTT -> SRT: {output_srt} ({seq - 1} cues)")
                return output_srt
            else:
                self.logger.debug("No subtitle cues found in VTT file")
                return None
        except Exception as e:
            self.logger.warning(f"Could not convert subtitles: {e}")
            return None

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
