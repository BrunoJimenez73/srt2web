"""
HLS Output - Envía stream procesado vía HLS para navegador web.

Este módulo recibe los datos del pipeline y los empaqueta en formato HLS
(fragmentos .ts + playlist .m3u8) para reproducción en navegador.

Configuración (output.web o output.hls):
    segment_duration: Duración de cada segmento en segundos (default: 15)
    list_size: Número de segmentos en la playlist (default: 6)
    audio_offset_ms: Offset de audio en milisegundos (default: 0)
"""

import glob
import os
import subprocess
import threading
from typing import Any, Optional

from core.encoder_config import EncoderConfig
from core.ffmpeg_pool import shutdown_pool
from core.ffmpeg_utils import check_gpu_support, ensure_ffmpeg
from core.module_base import ModuleState, ModuleStatus, PipelineData
from core.output_sink import OutputSink
from core.subprocess_utils import filter_command, get_creation_flags


class HLSOutput(OutputSink):
    """
    Empaqueta video + audio en formato HLS.

    Utiliza FFmpeg para crear segmentos HLS con soporte para
    aceleración por hardware (NVENC, QSV, AMF).
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__("web", config)

        # Configuración HLS
        self._segment_duration = config.get("segment_duration", 15)
        self._list_size = config.get("list_size", 6)
        self._audio_offset_ms = config.get("audio_offset_ms", 0)

        # Configuración de subtítulos
        self._subtitle_language = config.get("subtitle_language", "es")
        self._subtitle_language_name = config.get("subtitle_language_name", "Spanish")

        # Configuración de encoder
        self._encoder_config = EncoderConfig(config if config else {})

        # Estado interno
        self._ffmpeg_path: Optional[str] = None
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

        # Actualizar configuración de encoder
        self._encoder_config = EncoderConfig(config)

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
        }

    def start(self) -> None:
        """Iniciar salida HLS."""
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
            try:
                os.remove(ts_file)
            except OSError:
                pass
        for m3u8_file in glob.glob(os.path.join(self._hls_dir, "*.m3u8")):
            try:
                os.remove(m3u8_file)
            except OSError:
                pass

        self._segment_index = 0

        # Create initial master playlist with correct language
        master_path = os.path.join(self._hls_dir, "master.m3u8")
        try:
            with open(master_path, "w", encoding="utf-8") as master_file:
                master_file.write("#EXTM3U\n")
                master_file.write("#EXT-X-VERSION:4\n")
                master_file.write(
                    f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{self._subtitle_language_name}",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="{self._subtitle_language}",URI="/subtitles/subs.vtt"\n'
                )
                master_file.write(
                    '#EXT-X-STREAM-INF:BANDWIDTH=2000000,CODECS="avc1.64001f,mp4a.40.2",SUBTITLES="subs"\n'
                )
                master_file.write("stream.m3u8\n")
            self.logger.info(f"Created initial master playlist with language: {self._subtitle_language_name}")
        except Exception as e:
            self.logger.error(f"Failed to create initial master playlist: {e}")

        self.logger.info(f"HLS output ready: {self._hls_dir}")

    def stop(self) -> None:
        """Detener salida HLS."""
        self._hls_dir = ""
        # Shutdown FFmpeg pool on stop
        shutdown_pool()
        self.logger.info("HLS output stopped")

    def write(self, data: PipelineData) -> None:
        """
        Escribir chunk al stream HLS.

        Args:
            PipelineData con video_chunk_path y opcionalmente audio paths.
        """
        import time

        start_time = time.perf_counter()

        input_path = data.video_chunk_path
        if not input_path or not os.path.exists(input_path):
            self.logger.warning(f"No input video chunk for index {data.chunk_index}")
            return

        # Determinar audio a usar
        audio_input = data.mixed_audio_path or data.dubbed_audio_path

        # Calcular offset de tiempo - usar cumulative_duration para sincronizar con subtitles
        offset_sec = f"{getattr(data, 'cumulative_duration', self._total_duration_emitted):.3f}"
        chunk_duration = data.duration or self._segment_duration

        # Guardar duración para el manifest
        self._segment_durations[self._segment_index] = chunk_duration

        encoder_mode = self._encoder_config.encoder_mode

        # ── Fast path: passthrough sin TTS → FFmpeg solo remux (copy + PTS offset) ──
        # Necesitamos -output_ts_offset para que los PTS del segmento alineen con
        # los timestamps absolutos del VTT de subtítulos.
        # Usamos data.mixed_audio_path específicamente (no audio_input) porque
        # dubbed_audio_path puede estar seteado por AudioExtractor incluso sin TTS.
        if encoder_mode == "passthrough" and not data.mixed_audio_path:
            segment_name = f"seg_{self._segment_index:06d}.ts"
            segment_path = os.path.join(self._hls_dir, segment_name)
            cmd = [
                self._ffmpeg_path,
                "-y",
                "-i",
                input_path,
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                "-output_ts_offset",
                offset_sec,
                "-f",
                "mpegts",
                segment_path,
            ]
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
                    self.logger.error(f"FFmpeg mux error: {result.stderr[-500:]}")
                    self._set_error(f"FFmpeg exit code {result.returncode}")
                    return
            except subprocess.TimeoutExpired:
                self.logger.error("FFmpeg mux timed out")
                self._set_error("FFmpeg mux timed out")
                return
            except Exception as e:
                self.logger.error(f"FFmpeg mux exception: {e}")
                self._set_error(str(e))
                return

            self._total_duration_emitted += chunk_duration
            self._update_manifest()
            data.output_hls_path = os.path.join(self._hls_dir, "master.m3u8")
            elapsed = (time.perf_counter() - start_time) * 1000
            self._last_process_time_ms = elapsed
            seg_size = os.path.getsize(segment_path)
            self._update_write_stats(seg_size)
            self._clear_error()
            self.logger.info(
                f"HLS segment written (remux): {segment_name} (duration={chunk_duration:.3f}s, process_time={elapsed:.1f}ms)"
            )
            self._segment_index += 1
            return

        # ── Slow path: requiere FFmpeg (con audio TTS o encoder normal) ──
        encoder, preset, extra_args = self._get_encoder_config()

        cmd = [self._ffmpeg_path, "-y", "-i", input_path]

        if audio_input and os.path.exists(audio_input):
            audio_delay_sec = self._audio_offset_ms / 1000.0
            cmd.extend(["-itsoffset", str(audio_delay_sec), "-i", audio_input])

        # MPEG-TS container does not support Opus audio — force AAC
        if self._encoder_config.audio_codec == "opus":
            audio_codec = "aac"
        else:
            audio_codec = self._encoder_config.audio_codec
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

        if encoder == "libx264":
            cmd.extend(["-preset", preset])
        cmd.extend(extra_args)
        cmd.extend(
            [
                "-output_ts_offset",
                offset_sec,
                "-f",
                "mpegts",
                os.path.join(self._hls_dir, f"seg_{self._segment_index:06d}.ts"),
            ]
        )

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
                self.logger.error(f"FFmpeg mux error: {result.stderr[-500:]}")
                self._set_error(f"FFmpeg exit code {result.returncode}")
                return
        except subprocess.TimeoutExpired:
            self.logger.error("FFmpeg mux timed out")
            self._set_error("FFmpeg mux timed out")
            return
        except Exception as e:
            self.logger.error(f"FFmpeg mux exception: {e}")
            self._set_error(str(e))
            return

        self._total_duration_emitted += chunk_duration
        self._update_manifest()

        data.output_hls_path = os.path.join(self._hls_dir, "master.m3u8")
        elapsed = (time.perf_counter() - start_time) * 1000
        self._last_process_time_ms = elapsed

        segment_path = os.path.join(self._hls_dir, f"seg_{self._segment_index:06d}.ts")
        if os.path.exists(segment_path):
            seg_size = os.path.getsize(segment_path)
            self._update_write_stats(seg_size)
        self._clear_error()

        self.logger.info(
            f"HLS segment written: seg_{self._segment_index:06d}.ts (duration={chunk_duration:.3f}s, process_time={elapsed:.1f}ms)"
        )
        self._segment_index += 1

    def _get_encoder_config(self) -> tuple[str, str, list[str]]:
        """Determinar configuración del encoder (CPU/GPU) basado en preferencias."""
        encoder = "libx264"
        preset = self._encoder_config.video_preset
        extra_args: list[str] = []

        # Determinar encoder basado en modo configurado y disponibilidad de hardware
        encoder_mode = self._encoder_config.encoder_mode

        if encoder_mode == "auto":
            # Auto-detectar mejor hardware disponible
            if self._gpu_info["nvenc"]:
                encoder_mode = "gpu_nvenc"
            elif self._gpu_info["amf"]:
                encoder_mode = "gpu_amf"
            elif self._gpu_info["qsv"]:
                encoder_mode = "gpu_qsv"
            else:
                encoder_mode = "cpu"

        # Configurar encoder según modo seleccionado
        if encoder_mode == "passthrough":
            encoder = "copy"
            preset = ""
            extra_args = []
            self.logger.info("Using passthrough mode (no re-encoding)")
        elif encoder_mode == "gpu_nvenc" and self._gpu_info["nvenc"]:
            encoder = "h264_nvenc"
            preset = self._encoder_config.gpu_preset
            extra_args = self._encoder_config.get_gpu_nvenc_args()
            self.logger.info(f"Using GPU NVENC encoder (preset: {preset})")

        elif encoder_mode == "gpu_amf" and self._gpu_info["amf"]:
            encoder = "h264_amf"
            preset = self._encoder_config.video_preset
            extra_args = self._encoder_config.get_gpu_amf_args()
            self.logger.info(f"Using GPU AMF encoder (preset: {preset})")

        elif encoder_mode == "gpu_qsv" and self._gpu_info["qsv"]:
            encoder = "h264_qsv"
            preset = self._encoder_config.video_preset
            extra_args = self._encoder_config.get_gpu_qsv_args()
            self.logger.info(f"Using GPU QSV encoder (preset: {preset})")

        elif encoder_mode == "gpu_videotoolbox" and self._gpu_info["videotoolbox"]:
            encoder = "h264_videotoolbox"
            preset = self._encoder_config.gpu_preset
            extra_args = self._encoder_config.get_gpu_videotoolbox_args()
            self.logger.info(f"Using GPU VideoToolbox encoder (preset: {preset})")

        elif encoder_mode == "gpu_vaapi" and self._gpu_info["vaapi"]:
            encoder = "h264_vaapi"
            preset = self._encoder_config.video_preset
            extra_args = self._encoder_config.get_gpu_vaapi_args()
            self.logger.info(f"Using GPU VAAPI encoder (preset: {preset})")

        else:
            # CPU encoder con configuración CRF
            encoder = "libx264"
            preset = self._encoder_config.video_preset
            extra_args = self._encoder_config.get_cpu_args()
            self.logger.info(f"Using CPU encoder libx264 (preset: {preset}, crf: {self._encoder_config.video_crf})")

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

            # Escribir media playlist
            media_lines = [
                "#EXTM3U",
                "#EXT-X-VERSION:4",
                f"#EXT-X-TARGETDURATION:{self._segment_duration + 1}",
                f"#EXT-X-MEDIA-SEQUENCE:{media_seq}",
            ]

            for seg_path in segments:
                seg_name = os.path.basename(seg_path)
                try:
                    seg_idx = int(seg_name.replace("seg_", "").replace(".ts", ""))
                    dur = self._segment_durations.get(seg_idx, float(self._segment_duration))
                    media_lines.append(f"#EXTINF:{dur:.3f},")
                except ValueError:
                    media_lines.append(f"#EXTINF:{self._segment_duration}.000,")
                media_lines.append(seg_name)

            try:
                with open(media_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(media_lines) + "\n")
            except Exception as e:
                self.logger.error(f"Failed to write media playlist: {e}")

            # Escribir master playlist
            # Check subtitles directory (where SubtitleGenerator writes) first, then hls dir
            subs_dir = os.path.join(self._output_dir or "./output", "subtitles")
            subs_path_local = os.path.join(subs_dir, "subs.vtt")
            subs_path_hls = os.path.join(self._hls_dir, "subs.vtt")
            has_subs = os.path.exists(subs_path_local) or os.path.exists(subs_path_hls)

            # Check for dual track (alternative language)
            alt_subs_path = os.path.join(subs_dir, "subs_original.vtt")
            has_alt_subs = os.path.exists(alt_subs_path)

            master_lines = [
                "#EXTM3U",
                "#EXT-X-VERSION:4",
            ]

            if has_subs:
                # Primary subtitle track
                master_lines.append(
                    f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{self._subtitle_language_name}",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="{self._subtitle_language}",URI="/subtitles/subs.vtt"'
                )
                # Secondary track (original language) if dual track is active
                if has_alt_subs:
                    alt_lang = "en" if self._subtitle_language != "en" else "es"
                    alt_name = "Original" if self._subtitle_language_name != "English" else "Translated"
                    master_lines.append(
                        f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{alt_name}",DEFAULT=NO,AUTOSELECT=YES,FORCED=NO,LANGUAGE="{alt_lang}",URI="/subtitles/subs_original.vtt"'
                    )
                master_lines.append(
                    '#EXT-X-STREAM-INF:BANDWIDTH=2000000,CODECS="avc1.64001f,mp4a.40.2",SUBTITLES="subs"'
                )
            else:
                master_lines.append('#EXT-X-STREAM-INF:BANDWIDTH=2000000,CODECS="avc1.64001f,mp4a.40.2"')

            master_lines.append("stream.m3u8")

            try:
                with open(master_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(master_lines) + "\n")
            except Exception as e:
                self.logger.error(f"Failed to write master playlist: {e}")

    def get_status(self) -> ModuleStatus:
        """Get status including GPU encoder info."""
        using_gpu = False
        actual_encoder = "libx264"
        encoder_label = "CPU"

        encoder_mode = self._encoder_config.encoder_mode

        if encoder_mode == "passthrough":
            actual_encoder = "copy"
            encoder_label = "Passthrough"
        elif self._ffmpeg_path and encoder_mode in [
            "auto",
            "gpu_nvenc",
            "gpu_amf",
            "gpu_qsv",
            "gpu_vaapi",
            "gpu_videotoolbox",
        ]:
            if encoder_mode == "gpu_nvenc" and self._gpu_info["nvenc"]:
                using_gpu = True
                actual_encoder = "h264_nvenc"
                encoder_label = "H.264 NVENC"
            elif encoder_mode == "gpu_nvenc" and not self._gpu_info["nvenc"]:
                using_gpu = True
                actual_encoder = "h264_nvenc"
                encoder_label = "H.264 NVENC (ASSUMED)"
            elif self._gpu_info["nvenc"]:
                using_gpu = True
                actual_encoder = "h264_nvenc"
                encoder_label = "H.264 NVENC"
            elif self._gpu_info["amf"]:
                using_gpu = True
                actual_encoder = "h264_amf"
                encoder_label = "H.264 AMF"
            elif self._gpu_info["qsv"]:
                using_gpu = True
                actual_encoder = "h264_qsv"
                encoder_label = "H.264 QSV"
            elif self._gpu_info["vaapi"]:
                using_gpu = True
                actual_encoder = "h264_vaapi"
                encoder_label = "H.264 VAAPI"
            elif self._gpu_info["videotoolbox"]:
                using_gpu = True
                actual_encoder = "h264_videotoolbox"
                encoder_label = "H.264 VideoToolbox"

        if not using_gpu and encoder_mode != "passthrough":
            encoder_label = "H.264 CPU"

        return ModuleStatus(
            name="video_muxer",
            state=ModuleState.RUNNING if self._hls_dir else ModuleState.IDLE,
            enabled=True,
            processed_chunks=self._segment_index,
            last_process_time_ms=self._last_process_time_ms,
            extra={
                "encoder_mode": encoder_mode,
                "actual_encoder": actual_encoder,
                "using_gpu": using_gpu,
                "gpu_available": self._gpu_info,
                "gpu_preset": self._encoder_config.gpu_preset,
                "encoder_label": encoder_label,
            },
        )


# Auto-registro en factory
from core.io_factory import OutputFactory

OutputFactory.register("web", HLSOutput)
