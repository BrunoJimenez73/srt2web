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
        self._gpu_info = {"nvenc": False, "qsv": False, "amf": False}
        self._total_duration_emitted = 0.0
        super().__init__("video_muxer", config)

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._hls_segment_duration = config.get(
            "hls_segment_duration", self._hls_segment_duration
        )
        self._hls_list_size = 30  # Increased for stability
        self._audio_offset_ms = config.get("audio_offset_ms", self._audio_offset_ms)
        logger.info(f"VideoMuxer reconfigured: Audio Offset: {self._audio_offset_ms}ms")

    def start(self) -> None:
        """Initialize HLS output directory."""
        self._state = ModuleState.STARTING
        self._ffmpeg_path = ensure_ffmpeg()
        self._total_duration_emitted = 0.0  # Reset timing on every start!

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
        subtitle_input = data.subtitles_path

        # Calculate the proper timestamp offset based on cumulative duration
        # This prevents the 'stuttering' caused by imprecise chunk durations.
        offset_sec = f"{self._total_duration_emitted:.3f}"
        chunk_duration = data.duration or self._hls_segment_duration

        # Determine Encoder and Preset
        encoder = "libx264"
        preset = "ultrafast"
        extra_args = ["-tune", "zerolatency"]

        if self._gpu_info["nvenc"]:
            encoder = "h264_nvenc"
            preset = "p1"  # Fastest NVENC preset
            extra_args = ["-delay", "0", "-zerolatency", "1"]
            logger.info(
                f"[VideoMuxer] Using GPU encoder: h264_nvenc (preset: {preset})"
            )
        elif self._gpu_info["amf"]:
            encoder = "h264_amf"
            preset = "speed"
            logger.info(f"[VideoMuxer] Using GPU encoder: h264_amf (preset: {preset})")
        elif self._gpu_info["qsv"]:
            encoder = "h264_qsv"
            preset = "veryfast"
            logger.info(f"[VideoMuxer] Using GPU encoder: h264_qsv (preset: {preset})")
        else:
            logger.info(f"[VideoMuxer] Using CPU encoder: libx264 (preset: {preset})")

        common_args = [
            "-map",
            "0:v:0",
            "-map",
            "1:a:0" if audio_input else "0:a:0",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-output_ts_offset",
            offset_sec,
            "-f",
            "mpegts",
            segment_path,
        ]

        # Build FFmpeg command
        cmd = [self._ffmpeg_path, "-y", "-i", input_path]
        if audio_input and os.path.exists(audio_input):
            audio_delay_sec = self._audio_offset_ms / 1000.0
            cmd.extend(["-itsoffset", str(audio_delay_sec), "-i", audio_input])

        # Subtitle burn-in if format is srt
        if (
            subtitle_input
            and os.path.exists(subtitle_input)
            and subtitle_input.endswith(".srt")
        ):
            escaped_path = subtitle_input.replace("\\", "/").replace(":", "\\:")
            cmd.extend(
                [
                    "-vf",
                    f"subtitles='{escaped_path}'",
                    "-c:v",
                    encoder,
                    "-preset",
                    preset,
                ]
            )
            cmd.extend(extra_args)
        else:
            # If no subtitles to burn, we can copy video if no audio re-offset or transcoding needed
            # But normally we re-encode to ensure perfect synchronization of offsets.
            cmd.extend(["-c:v", encoder, "-preset", preset])
            cmd.extend(extra_args)

        cmd.extend(common_args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
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

        # Update cumulative duration
        self._total_duration_emitted += chunk_duration

        # Update HLS manifest
        self._update_manifest()
        self._segment_index += 1

        data.output_hls_path = os.path.join(self._hls_dir, "master.m3u8")

        # Clean up old input chunk to save disk space
        try:
            os.remove(input_path)
        except OSError:
            pass

        logger.debug(f"HLS segment written: {segment_name}")
        return data

    def _update_manifest(self) -> None:
        """
        Write/update the HLS manifests (master and media playlists).
        Uses a sliding window for segments.
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
                    except OSError:
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
            media_lines = [
                "#EXTM3U",
                "#EXT-X-VERSION:3",
                f"#EXT-X-TARGETDURATION:{self._hls_segment_duration + 1}",
                f"#EXT-X-MEDIA-SEQUENCE:{media_seq}",
            ]

            for seg_path in all_segments:
                seg_name = os.path.basename(seg_path)
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
                with open(master_playlist_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(master_lines) + "\n")
            except Exception as e:
                logger.error(f"Failed to write master playlist: {e}")
