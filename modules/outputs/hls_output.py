"""
HLS Output - Envía stream procesado vía HLS para navegador web.

Este módulo recibe los datos del pipeline y los empaqueta en formato HLS
(fragmentos .ts + playlist .m3u8) para reproducción en navegador.

Configuración (output.web o output.hls):
    segment_duration: Duración de cada segmento en segundos (default: 15)
    list_size: Número de segmentos en la playlist (default: 6)
    audio_offset_ms: Offset de audio en milisegundos (default: 0)
"""

import contextlib
import glob
import logging
import os
import subprocess
import sys
import threading
from typing import Any

from core.encoder_config import EncoderConfig
from core.ffmpeg_pool import FFmpegPool, get_pool
from core.ffmpeg_utils import check_gpu_support, ensure_ffmpeg, get_video_duration, starts_with_keyframe
from core.module_base import ModuleState, ModuleStatus, PipelineData
from core.output_sink import OutputSink
from core.subprocess_utils import filter_command, get_creation_flags

logger = logging.getLogger(__name__)


class HLSOutput(OutputSink):
    """
    Empaqueta video + audio en formato HLS.

    Utiliza FFmpeg para crear segmentos HLS con soporte para
    aceleración por hardware (NVENC, QSV, AMF).
    """

    def __init__(self, config: dict[str, Any], pool: FFmpegPool | None = None):
        super().__init__("web", config)

        self._pool = pool or get_pool()

        # Configuración HLS
        self._segment_duration = config.get("segment_duration", 15)
        self._list_size = config.get("list_size", 6)
        self._audio_offset_ms = config.get("audio_offset_ms", 0)

        # Configuración de subtítulos
        self._subtitle_language = config.get("subtitle_language", "es")
        self._subtitle_language_name = config.get("subtitle_language_name", "Spanish")

        # F169 — ABR bitrate ladder
        self._bitrate_ladder = config.get(
            "bitrate_ladder",
            [
                {"name": "low", "bandwidth": 500000, "width": 854, "height": 480},
                {"name": "medium", "bandwidth": 1500000, "width": 1280, "height": 720},
                {"name": "high", "bandwidth": 3000000, "width": 1920, "height": 1080},
            ],
        )

        # Configuración de encoder
        self._encoder_config = EncoderConfig(config if config else {})
        self._enabled = config.get("enabled", True)

        # Estado interno
        self._ffmpeg_path: str | None = None
        self._hls_dir: str = ""
        self._segment_index: int = 0
        self._manifest_lock = threading.Lock()
        self._gpu_info = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False, "videotoolbox": False}
        self._total_duration_emitted: float = 0.0
        self._segment_durations: dict[int, float] = {}
        # Timing tracking for frontend metrics
        self._last_process_time_ms: float = 0.0

    def configure(self, config: dict[str, Any]) -> None:
        """Aplicar configuración."""
        self._segment_duration = config.get("segment_duration", self._segment_duration)
        self._list_size = config.get("list_size", self._list_size)
        self._audio_offset_ms = config.get("audio_offset_ms", self._audio_offset_ms)
        self._enabled = config.get("enabled", self._enabled)

        # Actualizar configuración de encoder
        self._encoder_config = EncoderConfig(config)

        # Actualizar idioma de subtítulos
        if "subtitle_language" in config:
            self._subtitle_language = config["subtitle_language"]
        if "subtitle_language_name" in config:
            self._subtitle_language_name = config["subtitle_language_name"]
        if "bitrate_ladder" in config:
            self._bitrate_ladder = config["bitrate_ladder"]

        self.logger.info(
            f"HLS output reconfigured: segment={self._segment_duration}s, list_size={self._list_size}, "
            f"encoder_mode={self._encoder_config.encoder_mode}, video_preset={self._encoder_config.video_preset}"
        )

    def get_stream_info(self) -> dict[str, Any]:
        """Obtener información del stream para el cliente."""
        return {
            "type": "web",
            "hls_dir": self._hls_dir,
            "master_url": "/hls/master.m3u8",
            "stream_url": "/hls/stream.m3u8",
            "segment_duration": self._segment_duration,
            "bitrate_ladder": self._bitrate_ladder,
        }

    def start(self) -> None:
        """Iniciar salida HLS."""
        if not self._enabled:
            self.logger.info("HLS output disabled, skipping start")
            return
        self._ffmpeg_path = ensure_ffmpeg()
        self._total_duration_emitted = 0.0
        self._segment_durations = {}

        # Crear directorio HLS
        self._hls_dir = os.path.join(self._output_dir or "./output", "hls")
        os.makedirs(self._hls_dir, exist_ok=True)

        # Verificar GPU
        self._gpu_info = check_gpu_support(self._ffmpeg_path)
        self.logger.info(f"Hardware acceleration: {self._gpu_info}")

        # Limpiar archivos antiguos
        for ts_file in glob.glob(os.path.join(self._hls_dir, "*.ts")):
            with contextlib.suppress(OSError):
                os.remove(ts_file)
        for m3u8_file in glob.glob(os.path.join(self._hls_dir, "*.m3u8")):
            with contextlib.suppress(OSError):
                os.remove(m3u8_file)

        self._segment_index = 0

        # Create initial master playlist with ABR ladder
        master_path = os.path.join(self._hls_dir, "master.m3u8")
        try:
            with open(master_path, "w", encoding="utf-8") as master_file:
                master_file.write("#EXTM3U\n")
                master_file.write("#EXT-X-VERSION:4\n")
                master_file.write(
                    f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{self._subtitle_language_name}",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="{self._subtitle_language}",URI="/subtitles/subs.m3u8"\n'
                )
                # Single stream entry (all ABR variants point to same stream.m3u8)
                profile = self._bitrate_ladder[1] if len(self._bitrate_ladder) > 1 else self._bitrate_ladder[0]
                bw = profile.get("bandwidth", 1500000)
                w = profile.get("width", 1280)
                h = profile.get("height", 720)
                master_file.write(
                    f'#EXT-X-STREAM-INF:BANDWIDTH={bw},RESOLUTION={w}x{h},CODECS="avc1.64001f,mp4a.40.2",SUBTITLES="subs"\n'
                )
                master_file.write("stream.m3u8\n")
        except Exception as e:
            self.logger.error(f"Failed to create initial master playlist: {e}")

        # Create empty stream.m3u8 so the player doesn't hit a fatal 404
        # while waiting for the first chunk. HLSOutput.write() replaces this
        # with the real media playlist on the first processed chunk.
        stream_path = os.path.join(self._hls_dir, "stream.m3u8")
        try:
            with open(stream_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write("#EXT-X-VERSION:4\n")
                f.write("#EXT-X-TARGETDURATION:10\n")
                f.write("#EXT-X-MEDIA-SEQUENCE:0\n")
                # No DISCONTINUITY — this is the first playlist, there is
                # nothing to be discontinuous from. HLS.js may flush the
                # buffer on a discontinuity boundary, causing a stall.
        except Exception as e:
            self.logger.error(f"Failed to create empty stream playlist: {e}")

        self.logger.info(f"HLS output ready: {self._hls_dir}")

    def stop(self) -> None:
        """Detener salida HLS."""
        self._hls_dir = ""
        self.logger.info("HLS output stopped")

    @staticmethod
    def _is_h264(input_path: str) -> bool:
        """Check if input video is already H.264 (can be remuxed without re-encode)."""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=codec_name",
                    "-of",
                    "csv=p=0",
                    input_path,
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return "h264" in (result.stdout or "").lower()
        except Exception as e:
            logger.debug(f"Failed to check if FFmpeg supports h264: {e}")
            return False

    def write(self, data: PipelineData) -> None:
        """
        Escribir chunk al stream HLS.

        Args:
            PipelineData con video_chunk_path y opcionalmente audio paths.
        """
        import time

        start_time = time.perf_counter()

        if not self._enabled:
            return

        input_path = data.video_chunk_path
        if not input_path or not os.path.exists(input_path):
            self.logger.warning(f"No input video chunk for index {data.chunk_index}")
            return

        # Solo usar audio mezclado (original + TTS); nunca TTS solo.
        # Si el mixer no está activo o falló, conservar el audio original del video.
        audio_input = data.mixed_audio_path if data.mixed_audio_path and os.path.exists(data.mixed_audio_path) else None

        chunk_duration = data.duration or self._segment_duration

        # ── Fast path: remux when input is already H.264 AND starts with keyframe ──
        # Avoid re-encoding when the input codec is already H.264.
        # Only re-encode when passthrough mode is off AND input is not H.264
        # or doesn't start with a keyframe (which would cause stuttering).
        is_h264 = self._is_h264(input_path)
        has_keyframe = starts_with_keyframe(input_path)
        can_remux = (is_h264 and has_keyframe) or self._encoder_config.encoder_mode == "passthrough"
        if is_h264 and not has_keyframe:
            self.logger.info("Input does not start with keyframe, falling back to re-encode (prevents stuttering)")

        if can_remux:
            segment_name = f"seg_{self._segment_index:06d}.ts"
            segment_path = os.path.join(self._hls_dir, segment_name)

            has_mixed_audio = data.mixed_audio_path and os.path.exists(data.mixed_audio_path)
            if not has_mixed_audio:
                # Fastest path: pure file copy — no subprocess, no FFmpeg overhead
                import shutil

                try:
                    shutil.copy2(input_path, segment_path)
                except Exception as e:
                    self.logger.error(f"Segment copy error: {e}")
                    self._set_error(str(e))
                    self._segment_index += 1
                    return
                actual_duration = get_video_duration(segment_path) or chunk_duration
                self._segment_durations[self._segment_index] = actual_duration
                self._total_duration_emitted += actual_duration
                self._update_manifest()
                data.output_hls_path = os.path.join(self._hls_dir, "master.m3u8")
                elapsed = (time.perf_counter() - start_time) * 1000
                self._last_process_time_ms = elapsed
                seg_size = os.path.getsize(segment_path)
                self._update_write_stats(seg_size)
                self._clear_error()
                self.logger.info(f"HLS segment copied: {segment_name} (process_time={elapsed:.1f}ms)")
                self._segment_index += 1
                return

            # Has mixed audio: remux video + re-encode audio through FFmpegPool
            audio_delay_sec = self._audio_offset_ms / 1000.0
            cmd = [
                self._ffmpeg_path,
                "-y",
                "-i",
                input_path,
                "-itsoffset",
                str(audio_delay_sec),
                "-i",
                data.mixed_audio_path,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                self._encoder_config.audio_bitrate,
                "-f",
                "mpegts",
                segment_path,
            ]
            assert self._ffmpeg_path is not None, "start() must be called before write"
            job_id = f"hls-remux-audio-{self._segment_index:06d}"
            if not self._pool.acquire(self._ffmpeg_path, job_id, timeout=30):
                self.logger.warning("FFmpegPool timeout for remux job %s", job_id)
                self._segment_index += 1
                return
            try:
                result = subprocess.run(
                    filter_command(cmd),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30,
                    creationflags=get_creation_flags(),
                )
                if result.returncode != 0:
                    self.logger.error(f"FFmpeg mux error: {result.stderr[-500:]}")
                    self._set_error(f"FFmpeg exit code {result.returncode}")
                    self._segment_index += 1
                    return
            except subprocess.TimeoutExpired:
                self.logger.error("FFmpeg mux timed out")
                self._set_error("FFmpeg mux timed out")
                self._segment_index += 1
                return
            except Exception as e:
                self.logger.error(f"FFmpeg mux exception: {e}")
                self._set_error(str(e))
                self._segment_index += 1
                return
            finally:
                self._pool.release(job_id)

            actual_duration = get_video_duration(segment_path)
            if actual_duration <= 0:
                actual_duration = chunk_duration
            self._segment_durations[self._segment_index] = actual_duration
            self._total_duration_emitted += actual_duration
            self._update_manifest()
            data.output_hls_path = os.path.join(self._hls_dir, "master.m3u8")
            elapsed = (time.perf_counter() - start_time) * 1000
            self._last_process_time_ms = elapsed
            seg_size = os.path.getsize(segment_path)
            self._update_write_stats(seg_size)
            self._clear_error()
            self.logger.info(f"HLS segment remuxed (audio-only): {segment_name} (process_time={elapsed:.1f}ms)")
            self._segment_index += 1
            return

        # ── Slow path: requiere FFmpeg (con audio TTS o encoder normal) ──
        encoder, preset, extra_args = self._get_encoder_config()

        cmd = [self._ffmpeg_path, "-y", "-i", input_path]

        if audio_input and os.path.exists(audio_input):
            audio_delay_sec = self._audio_offset_ms / 1000.0
            cmd.extend(["-itsoffset", str(audio_delay_sec), "-i", audio_input])

        # MPEG-TS container does not support Opus audio — force AAC
        audio_codec = "aac" if self._encoder_config.audio_codec == "opus" else self._encoder_config.audio_codec
        audio_args = [
            "-c:a",
            audio_codec,
            "-b:a",
            self._encoder_config.audio_bitrate,
            "-ar",
            str(self._encoder_config.audio_sample_rate),
        ]

        cmd.extend(
            [
                "-map",
                "0:v:0",
                "-map",
                "1:a:0" if audio_input else "0:a:0",
            ]
        )
        cmd.extend(audio_args)
        cmd.extend(["-c:v", encoder])

        if "nvenc" in encoder:
            fps = self._encoder_config.video_fps or 25
            gop_frames = int(round(fps * self._segment_duration))
            cmd.extend(["-preset", preset, "-g", str(gop_frames), "-keyint_min", str(gop_frames), "-no-scenecut", "1"])
        elif encoder == "libx264":
            cmd.extend(["-preset", preset])
        cmd.extend(extra_args)
        cmd.extend(
            [
                "-force_key_frames",
                f"expr:gte(t,n*{self._segment_duration})",
                "-f",
                "mpegts",
                os.path.join(self._hls_dir, f"seg_{self._segment_index:06d}.ts"),
            ]
        )

        assert self._ffmpeg_path is not None, "start() must be called before write"
        job_id = f"hls-encode-{self._segment_index:06d}"
        if not self._pool.acquire(self._ffmpeg_path, job_id, timeout=30):
            self.logger.warning("FFmpegPool timeout for encode job %s", job_id)
            self._segment_index += 1
            return
        try:
            result = subprocess.run(
                filter_command(cmd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
                creationflags=get_creation_flags(),
            )
            if result.returncode != 0:
                # Fallback: retry with CPU encoder if GPU encoder failed
                self.logger.warning(f"FFmpeg encode error (will retry with CPU): {result.stderr[-200:]}")
                fallback_cmd = [self._ffmpeg_path, "-y", "-i", input_path]
                if audio_input and os.path.exists(audio_input):
                    audio_delay_sec = self._audio_offset_ms / 1000.0
                    fallback_cmd.extend(["-itsoffset", str(audio_delay_sec), "-i", audio_input])
                fallback_cmd.extend(
                    [
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0" if audio_input else "0:a:0",
                    ]
                )
                fallback_cmd.extend(audio_args)
                fallback_cmd.extend(
                    [
                        "-c:v",
                        "libx264",
                        "-preset",
                        "fast",
                        "-crf",
                        "23",
                        "-profile:v",
                        "high",
                        "-tune",
                        "zerolatency",
                        "-force_key_frames",
                        f"expr:gte(t,n*{self._segment_duration})",
                        "-f",
                        "mpegts",
                        os.path.join(self._hls_dir, f"seg_{self._segment_index:06d}.ts"),
                    ]
                )
                self.logger.info("Retrying segment with libx264 CPU encoder")
                result = subprocess.run(
                    filter_command(fallback_cmd),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60,
                    creationflags=get_creation_flags(),
                )
                if result.returncode != 0:
                    self.logger.error(f"FFmpeg CPU fallback also failed: {result.stderr[-500:]}")
                    self._set_error(f"FFmpeg exit code {result.returncode}")
                    self._segment_index += 1
                    return
                self.logger.info("CPU fallback succeeded")
        except subprocess.TimeoutExpired:
            self.logger.error("FFmpeg encode timed out")
            self._set_error("FFmpeg encode timed out")
            self._segment_index += 1
            return
        except Exception as e:
            self.logger.error(f"FFmpeg encode exception: {e}")
            self._set_error(str(e))
            self._segment_index += 1
            return
        finally:
            self._pool.release(job_id)

        segment_path = os.path.join(self._hls_dir, f"seg_{self._segment_index:06d}.ts")
        actual_duration = get_video_duration(segment_path)
        if actual_duration <= 0:
            actual_duration = chunk_duration
        self._segment_durations[self._segment_index] = actual_duration
        self._total_duration_emitted += actual_duration
        self._update_manifest()

        data.output_hls_path = os.path.join(self._hls_dir, "master.m3u8")
        elapsed = (time.perf_counter() - start_time) * 1000
        self._last_process_time_ms = elapsed

        if os.path.exists(segment_path):
            seg_size = os.path.getsize(segment_path)
            self._update_write_stats(seg_size)
        self._clear_error()

        self.logger.info(
            f"HLS segment written: seg_{self._segment_index:06d}.ts (duration={actual_duration:.3f}s, process_time={elapsed:.1f}ms)"
        )
        self._segment_index += 1

    def _get_encoder_config(self) -> tuple[str, str, list[str]]:
        """Determinar configuración del encoder (CPU/GPU) basado en preferencias."""
        encoder, preset, extra_args = self._encoder_config.resolve_encoder(self._gpu_info)
        self.logger.info(f"Using encoder: {encoder} (preset: {preset or 'default'})")
        return encoder, preset, extra_args

    def _update_manifest(self) -> None:
        """Actualizar playlists HLS."""
        with self._manifest_lock:
            media_path = os.path.join(self._hls_dir, "stream.m3u8")
            master_path = os.path.join(self._hls_dir, "master.m3u8")

            # Obtener segmentos actuales
            segments = sorted(glob.glob(os.path.join(self._hls_dir, "seg_*.ts")))

            # Sliding window
            if len(segments) > self._list_size:
                for old_seg in segments[: -self._list_size]:
                    try:
                        os.remove(old_seg)
                        old_idx = int(os.path.basename(old_seg).replace("seg_", "").replace(".ts", ""))
                        self._segment_durations.pop(old_idx, None)
                    except (OSError, ValueError):
                        pass
                segments = segments[-self._list_size :]

            # Media sequence number
            media_seq = 0
            if segments:
                try:
                    media_seq = int(os.path.basename(segments[0]).replace("seg_", "").replace(".ts", ""))
                except ValueError:
                    media_seq = 0

            # Push video media_seq — no longer needed, subtitle playlist
            # always uses media_seq=0 (VTT cues are media-relative).

            # TARGETDURATION must be >= actual max segment duration (HLS RFC)
            max_dur = max(self._segment_durations.values()) if self._segment_durations else self._segment_duration
            target_duration = int(max_dur) + 1
            media_lines = [
                "#EXTM3U",
                "#EXT-X-VERSION:4",
                f"#EXT-X-TARGETDURATION:{target_duration}",
                f"#EXT-X-MEDIA-SEQUENCE:{media_seq}",
            ]

            for seg_path in segments:
                seg_name = os.path.basename(seg_path)
                try:
                    seg_idx = int(seg_name.replace("seg_", "").replace(".ts", ""))
                    dur = self._segment_durations.get(seg_idx, float(self._segment_duration))
                    # Clamp to target_duration to avoid HLS spec violations
                    dur = min(dur, float(target_duration))
                    media_lines.append(f"#EXTINF:{dur:.3f},")
                except ValueError:
                    media_lines.append(f"#EXTINF:{self._segment_duration}.000,")
                # Each pipeline chunk has independent PTS/DTS starting from 0.
                # #EXT-X-DISCONTINUITY tells HLS.js not to expect continuous
                # timestamps, which prevents GapController from detecting
                # phantom holes and causing bufferStalledError.
                media_lines.append("#EXT-X-DISCONTINUITY")
                media_lines.append(seg_name)

            try:
                media_tmp = media_path + ".tmp"
                with open(media_tmp, "w", encoding="utf-8") as f:
                    f.write("\n".join(media_lines) + "\n")
                if sys.platform == "win32":
                    if os.path.exists(media_path):
                        os.remove(media_path)
                    os.rename(media_tmp, media_path)
                else:
                    os.replace(media_tmp, media_path)
            except Exception as e:
                self.logger.error(f"Failed to write media playlist: {e}")

            # Escribir master playlist con ABR ladder
            master_lines = [
                "#EXTM3U",
                "#EXT-X-VERSION:4",
                f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{self._subtitle_language_name}",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="{self._subtitle_language}",URI="/subtitles/subs.m3u8"',
            ]
            # Single stream entry (all ABR variants point to same stream.m3u8)
            profile = self._bitrate_ladder[1] if len(self._bitrate_ladder) > 1 else self._bitrate_ladder[0]
            bw = profile.get("bandwidth", 1500000)
            w = profile.get("width", 1280)
            h = profile.get("height", 720)
            master_lines.append(
                f'#EXT-X-STREAM-INF:BANDWIDTH={bw},RESOLUTION={w}x{h},CODECS="avc1.64001f,mp4a.40.2",SUBTITLES="subs"'
            )
            master_lines.append("stream.m3u8")

            try:
                master_tmp = master_path + ".tmp"
                with open(master_tmp, "w", encoding="utf-8") as f:
                    f.write("\n".join(master_lines) + "\n")
                if sys.platform == "win32":
                    if os.path.exists(master_path):
                        os.remove(master_path)
                    os.rename(master_tmp, master_path)
                else:
                    os.replace(master_tmp, master_path)
            except Exception as e:
                self.logger.error(f"Failed to write master playlist: {e}")

    def get_status(self) -> ModuleStatus:
        """Get status including GPU encoder info."""
        encoder_extra = self._encoder_config.get_encoder_status(self._gpu_info, self._ffmpeg_path)

        return ModuleStatus(
            name="web",
            state=ModuleState.RUNNING if (self._hls_dir and self._enabled) else ModuleState.IDLE,
            enabled=self._enabled,
            processed_chunks=self._segment_index,
            last_process_time_ms=self._last_process_time_ms,
            extra=encoder_extra,
        )
