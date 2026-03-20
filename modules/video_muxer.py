"""
Video Muxer Module — packages processed content into HLS.

Takes video chunks (with optional processed audio and subtitles)
and generates HLS output (m3u8 + ts segments) for web playback.
"""

import os
import sys
import glob
import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional

from core.module_base import BaseModule, PipelineData, ModuleState
from core.ffmpeg_utils import ensure_ffmpeg
from core.encoder_config import EncoderConfig

logger = logging.getLogger("srt2web.module.video_muxer")


class VideoMuxer(BaseModule):
    """
    Muxes video + audio + subtitles into HLS format.

    In Phase 1 (passthrough mode), simply repackages the input
    MPEG-TS chunks into HLS segments with a rolling m3u8 manifest.
    """

    def __init__(self, config: Optional[dict] = None, output_dir: str = "./output"):
        self._ffmpeg_path: Optional[str] = None
        self._output_dir = output_dir
        self._hls_dir = ""
        self._hls_segment_duration = 4
        self._segment_index = 0
        self._manifest_lock = threading.Lock()
        self._audio_offset_ms = 0
        self._hls_list_size = 30
        self._gpu_info = {"nvenc": False, "qsv": False, "amf": False, "vaapi": False}
        self._total_duration_emitted = 0.0
        self._segment_durations = {}  # Cache durations for manifest: {index: duration}
        # Subtitle language settings
        self._subtitle_language = "es"
        self._subtitle_language_name = "Spanish"
        # Encoder configuration
        self._encoder_config = EncoderConfig(config) if config else EncoderConfig()
        super().__init__("video_muxer", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._hls_segment_duration = config.get(
            "hls_segment_duration", self._hls_segment_duration
        )
        self._hls_list_size = 4  # Optimized for lower latency
        self._audio_offset_ms = config.get("audio_offset_ms", self._audio_offset_ms)
        # Video quality settings
        self._video_preset = config.get("video_preset", self._video_preset)
        self._gpu_preset = config.get("gpu_preset", self._gpu_preset)
        # Subtitle language settings
        self._subtitle_language = config.get("subtitle_language", "es")
        self._subtitle_language_name = config.get("subtitle_language_name", "Spanish")
        logger.info(
            f"VideoMuxer reconfigured: Audio Offset: {self._audio_offset_ms}ms, Video Preset: {self._video_preset}, GPU Preset: {self._gpu_preset}, Subtitle Language: {self._subtitle_language_name}"
        )

    def start(self) -> None:
        """Initialize HLS output directory."""
        self._state = ModuleState.STARTING
        self._ffmpeg_path = ensure_ffmpeg()
        self._total_duration_emitted = 0.0  # Reset timing on every start!
        self._segment_durations = {}

        # Create HLS output directory
        self._hls_dir = os.path.join(self._output_dir, "hls")
        os.makedirs(self._hls_dir, exist_ok=True)

        from core.ffmpeg_utils import check_gpu_support

        self._gpu_info = check_gpu_support(self._ffmpeg_path)
        logger.info(f"Hardware Acceleration Check: {self._gpu_info}")

        # Clean old HLS files
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
        self._state = ModuleState.RUNNING
        logger.info(
            f"VideoMuxer ready. Audio Offset: {self._audio_offset_ms}ms, HLS output at: {self._hls_dir}"
        )

    def stop(self) -> None:
        """Cleanup."""
        self._state = ModuleState.IDLE

    def _do_process(self, data: PipelineData) -> PipelineData:
        """
        Convert input chunk to HLS segment and update manifest.
        """
        input_path = data.video_chunk_path
        if not input_path or not os.path.exists(input_path):
            logger.warning(f"No input video chunk for index {data.chunk_index}")
            return data

        # Output segment filename
        segment_name = f"seg_{self._segment_index:06d}.ts"
        segment_path = os.path.join(self._hls_dir, segment_name)

        # Check if we have processed audio to mux in
        audio_input = data.mixed_audio_path or data.dubbed_audio_path
        # No subtitles_path used here yet, but kept for future use if needed

        # Calculate the proper timestamp offset based on cumulative duration
        # This prevents the 'stuttering' caused by imprecise chunk durations.
        offset_sec = f"{self._total_duration_emitted:.3f}"
        chunk_duration = data.duration or self._hls_segment_duration

        # Save duration for manifest
        self._segment_durations[self._segment_index] = chunk_duration

        # Determine Encoder and Preset using EncoderConfig
        encoder = "libx264"
        preset = self._encoder_config.video_preset
        extra_args = []

        # Get encoder mode from configuration
        encoder_mode = self._encoder_config.encoder_mode

        # Auto-detect if configured to auto
        if encoder_mode == "auto":
            if self._gpu_info["nvenc"]:
                encoder_mode = "gpu_nvenc"
            elif self._gpu_info["amf"]:
                encoder_mode = "gpu_amf"
            elif self._gpu_info["qsv"]:
                encoder_mode = "gpu_qsv"
            elif self._gpu_info["vaapi"]:
                encoder_mode = "gpu_vaapi"
            else:
                encoder_mode = "cpu"

        # Configure encoder based on mode
        if encoder_mode == "gpu_nvenc" and self._gpu_info["nvenc"]:
            encoder = "h264_nvenc"
            preset = self._encoder_config.gpu_preset
            extra_args = self._encoder_config.get_gpu_nvenc_args()
            logger.info(
                f"[VideoMuxer] Using GPU encoder: h264_nvenc (preset: {preset})"
            )
        elif encoder_mode == "gpu_amf" and self._gpu_info["amf"]:
            encoder = "h264_amf"
            preset = self._encoder_config.video_preset
            extra_args = self._encoder_config.get_gpu_amf_args()
            logger.info(f"[VideoMuxer] Using GPU encoder: h264_amf (preset: {preset})")
        elif encoder_mode == "gpu_qsv" and self._gpu_info["qsv"]:
            encoder = "h264_qsv"
            preset = self._encoder_config.video_preset
            extra_args = self._encoder_config.get_gpu_qsv_args()
            logger.info(f"[VideoMuxer] Using GPU encoder: h264_qsv (preset: {preset})")
        elif encoder_mode == "gpu_vaapi" and self._gpu_info["vaapi"]:
            encoder = "h264_vaapi"
            extra_args = ["-vaapi_device", "/dev/dri/renderD128"]
            logger.info(f"[VideoMuxer] Using GPU encoder: h264_vaapi")
        else:
            # CPU encoder
            encoder = "libx264"
            preset = self._encoder_config.video_preset
            extra_args = self._encoder_config.get_cpu_args()
            logger.info(f"[VideoMuxer] Using CPU encoder: libx264 (preset: {preset})")

        # Get audio configuration from EncoderConfig
        audio_args = self._encoder_config.get_audio_args()

        common_args = [
            "-map",
            "0:v:0",
            "-map",
            "1:a:0" if audio_input else "0:a:0",
        ]
        common_args.extend(audio_args)
        common_args.extend(
            [
                "-output_ts_offset",
                offset_sec,
                "-f",
                "mpegts",
                segment_path,
            ]
        )

        # Build FFmpeg command
        cmd = [self._ffmpeg_path, "-y", "-i", input_path]
        if audio_input and os.path.exists(audio_input):
            audio_delay_sec = self._audio_offset_ms / 1000.0
            cmd.extend(["-itsoffset", str(audio_delay_sec), "-i", audio_input])

        # If we had subtitles to burn in (Phase 2), we would add them here.
        # But for stability, we are currently muxing them or burning them in elsewhere.
        # Minimal implementation for stabilization.
        cmd.extend(["-c:v", encoder, "-preset", preset])
        cmd.extend(extra_args)
        cmd.extend(common_args)

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
                logger.error(f"FFmpeg mux error: {result.stderr[-500:]}")
                return data

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg mux timed out")
            return data
        except Exception as e:
            logger.error(f"FFmpeg mux exception: {e}")
            return data

        # Use actual audio duration for cumulative timing (important for TTS sync)
        actual_audio_duration = chunk_duration
        audio_input = data.mixed_audio_path or data.dubbed_audio_path
        if audio_input and os.path.exists(audio_input):
            actual_audio_duration = (
                self._get_audio_duration(audio_input) or chunk_duration
            )

        # Update cumulative duration with actual audio length
        self._total_duration_emitted += actual_audio_duration

        # DEBUG: Log segment timing
        logger.info(
            f"[VideoMuxer] Segment {self._segment_index}: orig_dur={chunk_duration:.3f}s, real_dur={actual_audio_duration:.3f}s, offset={offset_sec}s, total={self._total_duration_emitted:.3f}s"
        )

        # Update HLS manifest
        self._update_manifest()
        self._segment_index += 1

        data.output_hls_path = os.path.join(self._hls_dir, "master.m3u8")

        # Clean up old input chunk to save disk space
        try:
            os.remove(input_path)
        except OSError:
            pass

        logger.debug(
            f"HLS segment written: {segment_name} (Duration: {chunk_duration:.3f}s)"
        )
        return data

    def _update_manifest(self) -> None:
        """
        Write/update the HLS manifests (master and media playlists).
        Uses a sliding window for segments and REAL durations for stability.
        """
        with self._manifest_lock:
            media_playlist_path = os.path.join(self._hls_dir, "stream.m3u8")
            master_playlist_path = os.path.join(self._hls_dir, "master.m3u8")

            # 1. Get current segments
            all_segments = sorted(glob.glob(os.path.join(self._hls_dir, "seg_*.ts")))

            # Keep only the latest N segments (sliding window)
            if len(all_segments) > self._hls_list_size:
                to_remove = all_segments[: len(all_segments) - self._hls_list_size]
                for old_seg in to_remove:
                    try:
                        os.remove(old_seg)
                        # Clean up duration cache
                        old_name = os.path.basename(old_seg)
                        old_idx = int(old_name.replace("seg_", "").replace(".ts", ""))
                        if old_idx in self._segment_durations:
                            del self._segment_durations[old_idx]
                    except (OSError, ValueError):
                        pass
                all_segments = all_segments[-self._hls_list_size :]

            # Calculate media sequence number
            media_seq = 0
            if all_segments:
                first_seg = os.path.basename(all_segments[0])
                try:
                    media_seq = int(first_seg.replace("seg_", "").replace(".ts", ""))
                except ValueError:
                    media_seq = 0

            # 2. Write Media Playlist (stream.m3u8)
            # Use HLS version 4 for floating point durations support
            media_lines = [
                "#EXTM3U",
                "#EXT-X-VERSION:4",
                f"#EXT-X-TARGETDURATION:{self._hls_segment_duration + 2}",
                f"#EXT-X-MEDIA-SEQUENCE:{media_seq}",
            ]

            for seg_path in all_segments:
                seg_name = os.path.basename(seg_path)
                try:
                    seg_idx = int(seg_name.replace("seg_", "").replace(".ts", ""))
                    # Use cached duration or fallback to default
                    dur = self._segment_durations.get(
                        seg_idx, float(self._hls_segment_duration)
                    )
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
            subs_vtt_path = os.path.join(self._hls_dir, "subs.vtt")
            subs_exist = os.path.exists(subs_vtt_path)

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
                master_lines.append(
                    '#EXT-X-STREAM-INF:BANDWIDTH=2000000,CODECS="avc1.64001f,mp4a.40.2"'
                )

            master_lines.append("stream.m3u8")

            try:
                with open(master_playlist_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(master_lines) + "\n")
            except Exception as e:
                logger.error(f"Failed to write master playlist: {e}")

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration using ffprobe."""
        try:
            ffprobe = (
                self._ffmpeg_path.replace("ffmpeg", "ffprobe")
                if self._ffmpeg_path
                else "ffprobe"
            )
            if not os.path.exists(ffprobe):
                ffprobe = "ffprobe"
            cmd = [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return float(result.stdout.strip())
        except Exception:
            return 0.0
