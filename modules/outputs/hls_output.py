"""
HLS Output - Envía stream procesado vía HLS para navegador web.

Este módulo recibe los datos del pipeline y los empaqueta en formato HLS
(fragmentos .ts + playlist .m3u8) para reproducción en navegador.

Configuración (output.web o output.hls):
    segment_duration: Duración de cada segmento en segundos (default: 15)
    list_size: Número de segmentos en la playlist (default: 6)
    audio_offset_ms: Offset de audio en milisegundos (default: 0)
"""

import os
import sys
import glob
import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional

from core.output_sink import OutputSink
from core.module_base import PipelineData
from core.ffmpeg_utils import ensure_ffmpeg, check_gpu_support
from core.encoder_config import EncoderConfig


class HLSOutput(OutputSink):
    """
    Empaqueta video + audio en formato HLS.

    Utiliza FFmpeg para crear segmentos HLS con soporte para
    aceleración por hardware (NVENC, QSV, AMF).
    """

    def __init__(self, config: dict):
        super().__init__("web", config)

        # Configuración HLS
        self._segment_duration = config.get("segment_duration", 15)
        self._list_size = config.get("list_size", 6)
        self._audio_offset_ms = config.get("audio_offset_ms", 0)

        # Configuración de encoder
        self._encoder_config = EncoderConfig(config if config else {})

        # Estado interno
        self._ffmpeg_path: Optional[str] = None
        self._hls_dir: str = ""
        self._segment_index: int = 0
        self._manifest_lock = threading.Lock()
        self._gpu_info = {"nvenc": False, "qsv": False, "amf": False}
        self._total_duration_emitted: float = 0.0
        self._segment_durations: dict = {}

    def configure(self, config: dict) -> None:
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

    def get_stream_info(self) -> dict:
        """Obtener información del stream para el cliente."""
        return {
            "type": "web",
            "hls_dir": self._hls_dir,
            "master_url": f"/hls/master.m3u8",
            "stream_url": f"/hls/stream.m3u8",
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
        for f in glob.glob(os.path.join(self._hls_dir, "*.ts")):
            try:
                os.remove(f)
            except OSError:
                pass
        for f in glob.glob(os.path.join(self._hls_dir, "*.m3u8")):
            try:
                os.remove(f)
            except OSError:
                pass

        self._segment_index = 0
        self.logger.info(f"HLS output ready: {self._hls_dir}")

    def stop(self) -> None:
        """Detener salida HLS."""
        self._hls_dir = ""
        self.logger.info("HLS output stopped")

    def write(self, data: PipelineData) -> None:
        """
        Escribir chunk al stream HLS.

        Args:
            PipelineData con video_chunk_path y opcionalmente audio paths.
        """
        input_path = data.video_chunk_path
        if not input_path or not os.path.exists(input_path):
            self.logger.warning(f"No input video chunk for index {data.chunk_index}")
            return

        # Determinar audio a usar
        audio_input = data.mixed_audio_path or data.dubbed_audio_path

        # Calcular offset de tiempo
        offset_sec = f"{self._total_duration_emitted:.3f}"
        chunk_duration = data.duration or self._segment_duration

        # Guardar duración para el manifest
        self._segment_durations[self._segment_index] = chunk_duration

        # Determinar encoder
        encoder, preset, extra_args = self._get_encoder_config()

        # Construir comando FFmpeg
        cmd = [self._ffmpeg_path, "-y", "-i", input_path]

        if audio_input and os.path.exists(audio_input):
            audio_delay_sec = self._audio_offset_ms / 1000.0
            cmd.extend(["-itsoffset", str(audio_delay_sec), "-i", audio_input])

        # Obtener argumentos de audio desde EncoderConfig
        audio_args = self._encoder_config.get_audio_args()

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

        # Añadir preset solo para CPU (para GPU se pasa en extra_args)
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
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            if result.returncode != 0:
                self.logger.error(f"FFmpeg mux error: {result.stderr[-500:]}")
                return

        except subprocess.TimeoutExpired:
            self.logger.error("FFmpeg mux timed out")
            return
        except Exception as e:
            self.logger.error(f"FFmpeg mux exception: {e}")
            return

        # Actualizar duración acumulada
        self._total_duration_emitted += chunk_duration

        # Actualizar manifest
        self._update_manifest()

        # Limpiar chunk de entrada
        try:
            os.remove(input_path)
        except OSError:
            pass

        data.output_hls_path = os.path.join(self._hls_dir, "master.m3u8")

        self.logger.info(
            f"HLS segment written: seg_{self._segment_index:06d}.ts (duration={chunk_duration:.3f}s)"
        )
        self._segment_index += 1

    def _get_encoder_config(self) -> tuple:
        """Determinar configuración del encoder (CPU/GPU) basado en preferencias."""
        encoder = "libx264"
        preset = self._encoder_config.video_preset
        extra_args = []

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
        if encoder_mode == "gpu_nvenc" and self._gpu_info["nvenc"]:
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

        else:
            # CPU encoder con configuración CRF
            encoder = "libx264"
            preset = self._encoder_config.video_preset
            extra_args = self._encoder_config.get_cpu_args()
            self.logger.info(
                f"Using CPU encoder libx264 (preset: {preset}, crf: {self._encoder_config.video_crf})"
            )

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
                        old_idx = int(
                            os.path.basename(old_seg)
                            .replace("seg_", "")
                            .replace(".ts", "")
                        )
                        self._segment_durations.pop(old_idx, None)
                    except (OSError, ValueError):
                        pass
                segments = segments[-self._list_size :]

            # Media sequence number
            media_seq = 0
            if segments:
                try:
                    media_seq = int(
                        os.path.basename(segments[0])
                        .replace("seg_", "")
                        .replace(".ts", "")
                    )
                except ValueError:
                    media_seq = 0

            # Escribir media playlist
            media_lines = [
                "#EXTM3U",
                "#EXT-X-VERSION:4",
                f"#EXT-X-TARGETDURATION:{self._segment_duration + 2}",
                f"#EXT-X-MEDIA-SEQUENCE:{media_seq}",
            ]

            for seg_path in segments:
                seg_name = os.path.basename(seg_path)
                try:
                    seg_idx = int(seg_name.replace("seg_", "").replace(".ts", ""))
                    dur = self._segment_durations.get(
                        seg_idx, float(self._segment_duration)
                    )
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
            subs_path = os.path.join(self._hls_dir, "subs.vtt")
            has_subs = os.path.exists(subs_path)

            master_lines = [
                "#EXTM3U",
                "#EXT-X-VERSION:4",
            ]

            if has_subs:
                master_lines.append(
                    '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="Spanish",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="es",URI="subs.vtt"'
                )
                master_lines.append(
                    '#EXT-X-STREAM-INF:BANDWIDTH=2000000,CODECS="avc1.64001f,mp4a.40.2",SUBTITLES="subs"'
                )
            else:
                master_lines.append(
                    '#EXT-X-STREAM-INF:BANDWIDTH=2000000,CODECS="avc1.64001f,mp4a.40.2"'
                )

            master_lines.append("stream.m3u8")

            try:
                with open(master_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(master_lines) + "\n")
            except Exception as e:
                self.logger.error(f"Failed to write master playlist: {e}")


# Auto-registro en factory
from core.io_factory import OutputFactory

OutputFactory.register("web", HLSOutput)
OutputFactory.register("hls", HLSOutput)  # Alias
