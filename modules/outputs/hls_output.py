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
import re
import subprocess
import threading
from collections.abc import Callable
from typing import Any

from core.encoder_config import EncoderConfig
from core.ffmpeg_pool import FFmpegPool, get_pool
from core.ffmpeg_utils import check_gpu_support, ensure_ffmpeg, get_video_duration, starts_with_keyframe
from core.module_base import ModuleState, ModuleStatus, PipelineData
from core.output_sink import OutputSink
from core.paths import atomic_replace
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
        self._subtitle_resync_callback: Callable[[], None] | None = None

        # F169 — ABR bitrate ladder
        self._bitrate_ladder = config.get(
            "bitrate_ladder",
            [
                {"name": "low", "bandwidth": 500000, "width": 854, "height": 480},
                {"name": "medium", "bandwidth": 1500000, "width": 1280, "height": 720},
                {"name": "high", "bandwidth": 3000000, "width": 1920, "height": 1080},
            ],
        )
        # The schema supplies the ladder for real application configs. Keep
        # hand-built HLSOutput({}) instances on the legacy single-rendition
        # path unless a ladder was explicitly configured.
        self._abr_enabled = (
            "bitrate_ladder" in config and len(self._bitrate_ladder) > 1 and config.get("encoder_mode") != "passthrough"
        )
        self._variant_durations: dict[str, dict[int, float]] = {}

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
            self._abr_enabled = len(self._bitrate_ladder) > 1 and config.get("encoder_mode") != "passthrough"

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

    def _profile_name(self, profile: dict[str, Any], index: int) -> str:
        """Return a filesystem-safe, stable name for an ABR profile."""
        raw_name = str(profile.get("name", f"variant_{index}"))
        return re.sub(r"[^A-Za-z0-9_-]", "_", raw_name) or f"variant_{index}"

    def _primary_profile_index(self) -> int:
        return len(self._bitrate_ladder) // 2

    def _master_playlist_lines(self) -> list[str]:
        """Build a master playlist with one media playlist per rendition."""
        lines = [
            "#EXTM3U",
            "#EXT-X-VERSION:4",
            f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{self._subtitle_language_name}",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="{self._subtitle_language}",URI="/subtitles/subs.m3u8"',
        ]
        profiles = self._bitrate_ladder if self._abr_enabled else [self._bitrate_ladder[self._primary_profile_index()]]
        for profile_index, profile in enumerate(profiles):
            actual_index = profile_index if self._abr_enabled else self._primary_profile_index()
            bw = int(profile.get("bandwidth", 1500000))
            width = int(profile.get("width", 1280))
            height = int(profile.get("height", 720))
            name = self._profile_name(profile, actual_index)
            playlist_uri = "stream.m3u8" if actual_index == self._primary_profile_index() else f"{name}.m3u8"
            lines.append(
                f'#EXT-X-STREAM-INF:BANDWIDTH={bw},RESOLUTION={width}x{height},CODECS="avc1.64001f,mp4a.40.2",SUBTITLES="subs"'
            )
            lines.append(playlist_uri)
        return lines

    def _write_empty_variant_playlists(self) -> None:
        """Create media playlist files before the first encoded segment."""
        if not self._abr_enabled:
            return
        primary = self._primary_profile_index()
        for index, profile in enumerate(self._bitrate_ladder):
            if index == primary:
                continue
            name = self._profile_name(profile, index)
            variant_dir = os.path.join(self._hls_dir, name)
            os.makedirs(variant_dir, exist_ok=True)
            self._variant_durations[name] = {}
            with open(os.path.join(self._hls_dir, f"{name}.m3u8"), "w", encoding="utf-8") as stream_file:
                stream_file.write("#EXTM3U\n#EXT-X-VERSION:4\n#EXT-X-TARGETDURATION:10\n#EXT-X-MEDIA-SEQUENCE:0\n")

    def _generate_abr_variants(self, source_path: str, segment_index: int) -> None:
        """Encode low/high renditions from the primary segment.

        The primary rendition is encoded by ``write``. Deriving the other
        renditions from that self-contained MPEG-TS segment keeps every
        rendition on the same chunk boundary and makes the HLS timelines
        interchangeable for the player.
        """
        if not self._abr_enabled:
            return
        primary = self._primary_profile_index()
        for index, profile in enumerate(self._bitrate_ladder):
            if index == primary:
                continue
            name = self._profile_name(profile, index)
            variant_dir = os.path.join(self._hls_dir, name)
            os.makedirs(variant_dir, exist_ok=True)
            target_path = os.path.join(variant_dir, f"seg_{segment_index:06d}.ts")
            width = int(profile.get("width", 1280))
            height = int(profile.get("height", 720))
            bandwidth = int(profile.get("bandwidth", 1500000))
            cmd = [
                self._ffmpeg_path or "ffmpeg",
                "-y",
                "-i",
                source_path,
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-vf",
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-tune",
                "zerolatency",
                "-b:v",
                str(bandwidth),
                "-maxrate",
                str(bandwidth),
                "-bufsize",
                str(bandwidth * 2),
                "-c:a",
                "copy",
                "-f",
                "mpegts",
                target_path,
            ]
            job_id = f"hls-abr-{name}-{segment_index:06d}"
            if not self._pool.acquire(self._ffmpeg_path or "ffmpeg", job_id, timeout=30):
                self.logger.warning("FFmpegPool timeout for ABR job %s", job_id)
                continue
            try:
                result = subprocess.run(
                    filter_command(cmd),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60,
                    creationflags=get_creation_flags(),
                )
                if result.returncode != 0:
                    self.logger.error("ABR rendition %s failed: %s", name, result.stderr[-500:])
                    continue
                self._variant_durations.setdefault(name, {})[segment_index] = self._segment_durations.get(
                    segment_index, self._segment_duration
                )
            except (subprocess.TimeoutExpired, OSError) as exc:
                self.logger.error("ABR rendition %s failed: %s", name, exc)
            finally:
                self._pool.release(job_id)

    def start(self) -> None:
        """Iniciar salida HLS."""
        if not self._enabled:
            self.logger.info("HLS output disabled, skipping start")
            return
        self._ffmpeg_path = ensure_ffmpeg()
        self._total_duration_emitted = 0.0
        self._segment_durations = {}
        self._variant_durations = {}

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
        if self._abr_enabled:
            primary = self._primary_profile_index()
            for index, profile in enumerate(self._bitrate_ladder):
                if index == primary:
                    continue
                variant_dir = os.path.join(self._hls_dir, self._profile_name(profile, index))
                for ts_file in glob.glob(os.path.join(variant_dir, "*.ts")):
                    with contextlib.suppress(OSError):
                        os.remove(ts_file)

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
                master_file.write("\n".join(self._master_playlist_lines()[2:]) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to create initial master playlist: {e}")

        self._write_empty_variant_playlists()

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
        can_remux = (
            (is_h264 and has_keyframe) or self._encoder_config.encoder_mode == "passthrough"
        ) and not self._abr_enabled
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

        primary_profile = self._bitrate_ladder[self._primary_profile_index()]
        cmd.extend(
            [
                "-b:v",
                str(int(primary_profile.get("bandwidth", 1500000))),
                "-s",
                f"{int(primary_profile.get('width', 1280))}x{int(primary_profile.get('height', 720))}",
            ]
        )

        if "nvenc" in encoder:
            fps = self._encoder_config.video_fps or 25
            gop_frames = round(fps * self._segment_duration)
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
                        "-b:v",
                        str(int(primary_profile.get("bandwidth", 1500000))),
                        "-s",
                        f"{int(primary_profile.get('width', 1280))}x{int(primary_profile.get('height', 720))}",
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
        self._generate_abr_variants(segment_path, self._segment_index)
        self._update_manifest()

        data.output_hls_path = os.path.join(self._hls_dir, "master.m3u8")
        elapsed = (time.perf_counter() - start_time) * 1000
        self._last_process_time_ms = elapsed

        if os.path.exists(segment_path):
            seg_size = os.path.getsize(segment_path)
            self._update_write_stats(seg_size)
        self._clear_error()

        self.logger.info(
            "HLS segment written: seg_%06d.ts (duration=%.3fs, process_time=%.1fms)",
            self._segment_index,
            actual_duration,
            elapsed,
        )
        self._segment_index += 1

    def _get_encoder_config(self) -> tuple[str, str, list[str]]:
        """Determinar configuración del encoder (CPU/GPU) basado en preferencias."""
        encoder, preset, extra_args = self._encoder_config.resolve_encoder(self._gpu_info)
        self.logger.info(f"Using encoder: {encoder} (preset: {preset or 'default'})")
        return encoder, preset, extra_args

    def set_subtitle_resync_callback(self, callback: Callable[[], None] | None) -> None:
        """Register a callback invoked after each manifest update.

        The subtitle generator (modules/subtitle_generator_pkg/) writes its
        playlist slightly BEFORE the video segment of the same chunk is
        published, so its window can lag the video by one fragment. This
        callback lets HLSOutput re-align subs.m3u8 right after stream.m3u8
        advances, keeping both MEDIA-SEQUENCE values identical.
        """
        self._subtitle_resync_callback = callback

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
                        if self._abr_enabled:
                            for profile_index, profile in enumerate(self._bitrate_ladder):
                                name = self._profile_name(profile, profile_index)
                                if name in self._variant_durations:
                                    self._variant_durations[name].pop(old_idx, None)
                                variant_seg = os.path.join(self._hls_dir, name, os.path.basename(old_seg))
                                with contextlib.suppress(OSError):
                                    os.remove(variant_seg)
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

            # The subtitle fragment writer (modules/subtitle_generator_pkg/
            # _fragment_writer.py) reads this same stream.m3u8 to align its
            # window (never ahead of the video) and reuse these EXTINF
            # durations, keeping both playlists on identical timelines.

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
                atomic_replace(media_tmp, media_path)
            except Exception as e:
                self.logger.error(f"Failed to write media playlist: {e}")

            # Publish one media playlist for every configured rendition.
            if self._abr_enabled:
                primary = self._primary_profile_index()
                for index, profile in enumerate(self._bitrate_ladder):
                    if index == primary:
                        continue
                    name = self._profile_name(profile, index)
                    variant_segments = sorted(glob.glob(os.path.join(self._hls_dir, name, "seg_*.ts")))
                    variant_lines = [
                        "#EXTM3U",
                        "#EXT-X-VERSION:4",
                        f"#EXT-X-TARGETDURATION:{target_duration}",
                        f"#EXT-X-MEDIA-SEQUENCE:{media_seq}",
                    ]
                    for variant_seg in variant_segments:
                        seg_name = os.path.basename(variant_seg)
                        try:
                            seg_idx = int(seg_name.replace("seg_", "").replace(".ts", ""))
                        except ValueError:
                            continue
                        dur = self._variant_durations.get(name, {}).get(
                            seg_idx, self._segment_durations.get(seg_idx, float(self._segment_duration))
                        )
                        variant_lines.append(f"#EXTINF:{min(dur, float(target_duration)):.3f},")
                        variant_lines.append("#EXT-X-DISCONTINUITY")
                        variant_lines.append(f"{name}/{seg_name}")
                    try:
                        variant_path = os.path.join(self._hls_dir, f"{name}.m3u8")
                        variant_tmp = variant_path + ".tmp"
                        with open(variant_tmp, "w", encoding="utf-8") as f:
                            f.write("\n".join(variant_lines) + "\n")
                        atomic_replace(variant_tmp, variant_path)
                    except Exception as e:
                        self.logger.error("Failed to write ABR playlist %s: %s", name, e)

            # Escribir master playlist con ABR ladder
            master_lines = self._master_playlist_lines()

            try:
                master_tmp = master_path + ".tmp"
                with open(master_tmp, "w", encoding="utf-8") as f:
                    f.write("\n".join(master_lines) + "\n")
                atomic_replace(master_tmp, master_path)
            except Exception as e:
                self.logger.error(f"Failed to write master playlist: {e}")

        # Re-align the subtitle playlist with the freshly published video
        # window. stream.m3u8 just advanced (new segment / trimmed base);
        # the subtitle writer must read it NOW so both playlists expose
        # the same MEDIA-SEQUENCE and HLS.js keeps the cues.
        if self._subtitle_resync_callback is not None:
            try:
                self.logger.debug(f"[HLSOutput] Firing subtitle resync callback (segment_index={self._segment_index})")
                self._subtitle_resync_callback()
            except Exception as e:
                self.logger.error(f"Subtitle playlist resync failed: {e}")
        else:
            self.logger.debug(
                f"[HLSOutput] NO subtitle resync callback registered (segment_index={self._segment_index})"
            )

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
