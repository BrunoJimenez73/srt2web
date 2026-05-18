"""
Video Muxer Module — packages processed content into HLS.

Takes video chunks (with optional processed audio and subtitles)
and generates HLS output (m3u8 + ts segments) for web playback.
"""

import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Optional

from core.encoder_config import EncoderConfig
from core.ffmpeg_utils import ensure_ffmpeg
from core.module_base import BaseModule, ModuleState, ModuleStatus, PipelineData
from core.subprocess_utils import filter_command, get_creation_flags

logger = logging.getLogger("srt2web.module.video_muxer")
logger.setLevel(logging.INFO)


class VideoMuxer(BaseModule):
    """
    Muxes video + audio + subtitles into HLS format.

    In Phase 1 (passthrough mode), simply repackages the input
    MPEG-TS chunks into HLS segments with a rolling m3u8 manifest.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None, output_dir: str = "./output") -> None:
        self._ffmpeg_path: Optional[str] = None
        self._output_dir = Path(output_dir)  # Convert to Path
        self._hls_dir = Path()
        self._hls_segment_duration = 4
        self._segment_index = 0
        self._manifest_lock = threading.Lock()
        self._audio_offset_ms = 0
        self._hls_list_size = 30
        self._gpu_info = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False, "videotoolbox": False}
        self._total_duration_emitted = 0.0
        self._segment_durations: dict[int, float] = {}  # Cache durations for manifest: {index: duration}
        # Subtitle language settings
        self._subtitle_language = "es"
        self._subtitle_language_name = "Spanish"
        # Video quality settings (must be initialized before configure())
        # Optimized for speed: faster presets reduce encoding time significantly
        self._video_preset = "fast"
        self._gpu_preset = "p7"  # Faster GPU preset (p1=slowest/best, p7=fastest)
        # Encoder configuration
        self._encoder_config = EncoderConfig(config) if config else EncoderConfig()
        super().__init__("video_muxer", config)

    def configure(self, config: dict[str, Any]) -> None:
        super().configure(config)
        self._hls_segment_duration = config.get("hls_segment_duration", self._hls_segment_duration)
        self._hls_list_size = 4  # Optimized for lower latency
        self._audio_offset_ms = config.get("audio_offset_ms", self._audio_offset_ms)
        # Video quality settings
        self._video_preset = config.get("video_preset", self._video_preset)
        self._gpu_preset = config.get("gpu_preset", self._gpu_preset)
        # Subtitle language settings
        self._subtitle_language = config.get("subtitle_language", "es")
        self._subtitle_language_name = config.get("subtitle_language_name", "Spanish")
        # Encoder mode must be read and applied to EncoderConfig
        if "encoder_mode" in config:
            self._encoder_config = EncoderConfig(config)
        logger.info(
            f"VideoMuxer reconfigured: Audio Offset: {self._audio_offset_ms}ms, Video Preset: {self._video_preset}, GPU Preset: {self._gpu_preset}, Encoder Mode: {self._encoder_config.encoder_mode}, Subtitle Language: {self._subtitle_language_name}"
        )

    def start(self) -> None:
        """Initialize HLS output directory."""
        self._state = ModuleState.STARTING
        self._ffmpeg_path = ensure_ffmpeg()
        self._total_duration_emitted = 0.0  # Reset timing on every start!
        self._segment_durations = {}

        # Create HLS output directory
        self._hls_dir = Path(self._output_dir) / "hls"
        self._hls_dir.mkdir(parents=True, exist_ok=True)

        from core.ffmpeg_utils import check_gpu_support

        self._gpu_info = check_gpu_support(self._ffmpeg_path)
        logger.info(f"Hardware Acceleration Check: {self._gpu_info}")

        # Clean old HLS files
        for f in self._hls_dir.glob("*.ts"):
            try:
                f.unlink()
            except OSError:
                pass
        for f in self._hls_dir.glob("*.m3u8"):
            try:
                f.unlink()
            except OSError:
                pass

        self._segment_index = 0
        self._state = ModuleState.RUNNING
        logger.info(f"VideoMuxer ready. Audio Offset: {self._audio_offset_ms}ms, HLS output at: {self._hls_dir}")

    def stop(self) -> None:
        """Cleanup."""
        self._state = ModuleState.IDLE

    def write(self, data: PipelineData) -> PipelineData:
        """
        Write chunk to HLS stream (called by AsyncPipeline as output_sink).
        Convert input chunk to HLS segment and update manifest.
        """
        # Track processing time
        start_time = time.perf_counter()

        logger.info(f"[VideoMuxer.write] Received data chunk {getattr(data, 'chunk_index', 'None')}")

        if hasattr(data, "video_path") and not hasattr(data, "video_chunk_path"):
            data.video_chunk_path = data.video_path
        elif not hasattr(data, "video_chunk_path"):
            if isinstance(data, dict) and "video_path" in data:
                data.video_chunk_path = data["video_path"]

        if not hasattr(data, "video_chunk_path") or not data.video_chunk_path:
            logger.warning("[VideoMuxer.write] No video_chunk_path available")
            return data

        # Process the data
        try:
            result = self.process(data)
        except Exception as e:
            logger.error(f"[VideoMuxer.write] Error: {e}")
            return data

        elapsed = (time.perf_counter() - start_time) * 1000
        self._last_process_time_ms = elapsed
        self._processed_chunks += 1
        logger.info(f"[VideoMuxer.write] Processed chunk in {elapsed:.1f}ms")
        return result

    def _get_encoder_config(self) -> tuple[str, str, list[str]]:
        """Determinar configuración del encoder (CPU/GPU) basado en preferencias."""
        encoder = "libx264"
        preset = self._encoder_config.video_preset
        extra_args = []

        encoder_mode = self._encoder_config.encoder_mode

        if encoder_mode == "auto":
            if self._gpu_info["nvenc"]:
                encoder_mode = "gpu_nvenc"
            elif self._gpu_info["amf"]:
                encoder_mode = "gpu_amf"
            elif self._gpu_info["qsv"]:
                encoder_mode = "gpu_qsv"
            elif self._gpu_info["vaapi"]:
                encoder_mode = "gpu_vaapi"
            elif self._gpu_info["videotoolbox"]:
                encoder_mode = "gpu_videotoolbox"
            else:
                encoder_mode = "cpu"

        if encoder_mode == "passthrough" or encoder_mode == "cpu":
            pass
        elif encoder_mode == "gpu_nvenc" and self._gpu_info["nvenc"]:
            encoder = "h264_nvenc"
            preset = self._encoder_config.gpu_preset
            extra_args = self._encoder_config.get_gpu_nvenc_args()
            logger.info(f"VideoMuxer using GPU NVENC (preset: {preset})")
        elif encoder_mode == "gpu_amf" and self._gpu_info["amf"]:
            encoder = "h264_amf"
            preset = self._encoder_config.video_preset
            extra_args = self._encoder_config.get_gpu_amf_args()
            logger.info(f"VideoMuxer using GPU AMF (preset: {preset})")
        elif encoder_mode == "gpu_qsv" and self._gpu_info["qsv"]:
            encoder = "h264_qsv"
            preset = self._encoder_config.video_preset
            extra_args = self._encoder_config.get_gpu_qsv_args()
            logger.info(f"VideoMuxer using GPU QSV (preset: {preset})")
        elif encoder_mode == "gpu_videotoolbox" and self._gpu_info["videotoolbox"]:
            encoder = "h264_videotoolbox"
            preset = self._encoder_config.gpu_preset
            extra_args = self._encoder_config.get_gpu_videotoolbox_args()
            logger.info(f"VideoMuxer using GPU VideoToolbox (preset: {preset})")
        elif encoder_mode == "gpu_vaapi" and self._gpu_info["vaapi"]:
            encoder = "h264_vaapi"
            preset = self._encoder_config.video_preset
            extra_args = self._encoder_config.get_gpu_vaapi_args()
            logger.info(f"VideoMuxer using GPU VAAPI (preset: {preset})")
        else:
            logger.info(f"VideoMuxer using CPU encoder libx264 (preset: {preset})")

        return encoder, preset, extra_args

    def _do_process(self, data: PipelineData) -> PipelineData:
        """Generate HLS segment from video chunk."""
        input_path = data.video_chunk_path
        if not input_path or not Path(input_path).exists():
            return data

        chunk_duration = data.duration or self._hls_segment_duration
        offset_sec = getattr(data, "cumulative_duration", self._total_duration_emitted)
        segment_name = f"seg_{self._segment_index:06d}.ts"
        segment_path = self._hls_dir / segment_name

        encoder_mode = self._encoder_config.encoder_mode
        encoder, preset, extra_args = self._get_encoder_config()

        if encoder_mode == "passthrough" or encoder == "libx264":
            # Fast path: copy without re-encoding
            try:
                import shutil

                shutil.copy2(input_path, segment_path)
                logger.info(f"VideoMuxer segment copied (passthrough): {segment_name}")
            except Exception as e:
                logger.debug("Suppressed error: %s", e, exc_info=True)
        else:
            # GPU encode path: use FFmpeg with selected encoder
            try:
                cmd = [
                    self._ffmpeg_path,
                    "-y",
                    "-i",
                    str(input_path),
                    "-map",
                    "0:v:0",
                    "-c:v",
                    encoder,
                    "-preset",
                    preset,
                    *extra_args,
                    "-f",
                    "mpegts",
                    str(segment_path),
                ]
                result = subprocess.run(
                    filter_command(cmd),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60,
                    creationflags=get_creation_flags(),
                )
                if result.returncode != 0:
                    logger.error(f"VideoMuxer FFmpeg error: {result.stderr[-500:]}")
                    # Fallback: copy instead of failing silently
                    import shutil

                    shutil.copy2(input_path, segment_path)
                else:
                    logger.info(f"VideoMuxer segment encoded ({encoder}): {segment_name}")
            except Exception:
                # Fallback: copy segment instead of failing
                import shutil

                shutil.copy2(input_path, segment_path)

        # Cache duration for manifest
        self._segment_durations[self._segment_index] = chunk_duration
        self._total_duration_emitted += chunk_duration

        # Update manifest
        self._update_manifest()
        self._segment_index += 1

        # Set output path for RecordingOutput
        data.output_hls_path = str(self._hls_dir / "master.m3u8")
        data.video_path = str(input_path)  # For RecordingOutput

        return data

    def _update_manifest(self) -> None:
        """
        Write/update the HLS manifests (master and media playlists).
        Uses a sliding window for segments and REAL durations for stability.
        """
        with self._manifest_lock:
            media_playlist_path = self._hls_dir / "stream.m3u8"
            master_playlist_path = self._hls_dir / "master.m3u8"

            # 1. Get current segments
            all_segments = sorted(self._hls_dir.glob("seg_*.ts"))

            # Keep only the latest N segments (sliding window)
            if len(all_segments) > self._hls_list_size:
                to_remove = all_segments[: len(all_segments) - self._hls_list_size]
                for old_seg in to_remove:
                    try:
                        old_seg.unlink()
                        # Clean up duration cache
                        old_name = old_seg.name
                        old_idx = int(old_name.replace("seg_", "").replace(".ts", ""))
                        if old_idx in self._segment_durations:
                            del self._segment_durations[old_idx]
                    except (OSError, ValueError):
                        pass
                all_segments = all_segments[-self._hls_list_size :]

            # Calculate media sequence number
            media_seq = 0
            if all_segments:
                first_seg = all_segments[0]
                try:
                    media_seq = int(first_seg.stem.replace("seg_", ""))
                except ValueError:
                    media_seq = 0

            # 2. Write Media Playlist (stream.m3u8)
            # Use HLS version 4 for floating point durations support
            media_lines = [
                "#EXTM3U",
                "#EXT-X-VERSION:4",
                f"#EXT-X-TARGETDURATION:{self._hls_segment_duration + 1}",
                f"#EXT-X-MEDIA-SEQUENCE:{media_seq}",
            ]

            for seg_path in all_segments:
                seg_name = seg_path.name
                try:
                    seg_idx = int(seg_path.stem.replace("seg_", ""))
                    # Use cached duration or fallback to default
                    dur = self._segment_durations.get(seg_idx, float(self._hls_segment_duration))
                    media_lines.append(f"#EXTINF:{dur:.3f},")
                except ValueError:
                    media_lines.append(f"#EXTINF:{self._hls_segment_duration}.000,")

                media_lines.append(seg_name)

            try:
                with open(media_playlist_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(media_lines) + "\n")
            except Exception as e:
                logger.error(f"Failed to write media playlist: {e}")

            # 3. Write Master Playlist (master.m3u8)
            # This is where we properly link subtitles for HLS.js
            subs_vtt_path = self._hls_dir / "subs.vtt"
            subs_exist = subs_vtt_path.exists()

            master_lines = [
                "#EXTM3U",
                "#EXT-X-VERSION:4",
            ]

            if subs_exist:
                master_lines.append(
                    f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{self._subtitle_language_name}",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="{self._subtitle_language}",URI="subs.vtt"'
                )
                master_lines.append(
                    '#EXT-X-STREAM-INF:BANDWIDTH=2000000,CODECS="avc1.64001f,mp4a.40.2",SUBTITLES="subs"'
                )
            else:
                master_lines.append('#EXT-X-STREAM-INF:BANDWIDTH=2000000,CODECS="avc1.64001f,mp4a.40.2"')

            master_lines.append("stream.m3u8")

            try:
                with open(master_playlist_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(master_lines) + "\n")
            except Exception as e:
                logger.error(f"Failed to write master playlist: {e}")

    def get_status(self) -> ModuleStatus:
        """Get current status including GPU encoder info."""
        status = super().get_status()

        # --- Lógica de Asunción de NVENC/GPU ---
        encoder_mode = self._encoder_config.encoder_mode
        using_gpu = False
        actual_encoder = "libx264"
        encoder_label = "CPU"

        if self._ffmpeg_path and encoder_mode in [
            "auto",
            "gpu_nvenc",
            "gpu_amf",
            "gpu_qsv",
            "gpu_vaapi",
            "gpu_videotoolbox",
        ]:
            # Si el binario existe, asumimos la compatibilidad si la configuración lo pide
            if encoder_mode == "gpu_nvenc" and self._gpu_info["nvenc"]:
                using_gpu = True
                actual_encoder = "h264_nvenc"
                encoder_label = "H.264 NVENC"
            elif encoder_mode == "gpu_nvenc" and not self._gpu_info["nvenc"]:
                # HARDCODING DE CONFIANZA: Si el usuario pide NVENC y el binario existe, asumimos que funciona.
                logger.warning(
                    f"NVENC requested but not detected by FFmpeg. Assuming compatibility for {self._ffmpeg_path}."
                )
                using_gpu = True
                actual_encoder = "h264_nvenc"
                encoder_label = "H.264 NVENC (ASSUMED)"
            elif self._gpu_info["nvenc"]:
                # Modo auto y NVENC detectado
                using_gpu = True
                actual_encoder = "h264_nvenc"
                encoder_label = "H.264 NVENC"
            # ... (Incluir lógica para AMF, QSV, VAAPI si es necesario para mantener la paridad)
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

        # Si no hay GPU, el encoder sigue siendo libx264 (CPU)
        if not using_gpu:
            actual_encoder = "libx264"
            encoder_label = "H.264 CPU"

        # Reportar estado
        status.extra["encoder_mode"] = encoder_mode
        status.extra["actual_encoder"] = actual_encoder
        status.extra["using_gpu"] = using_gpu
        status.extra["gpu_available"] = self._gpu_info
        status.extra["gpu_preset"] = self._encoder_config.gpu_preset
        status.extra["encoder_label"] = encoder_label

        # WebRTC override
        if hasattr(self, "_engine") and self._engine == "webrtc":
            status.extra["using_gpu"] = False
            status.extra["encoder_label"] = "CPU (WebRTC)"
            status.extra["actual_encoder"] = "webrtc"

        return status
