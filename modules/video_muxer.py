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

from core.module_base import BaseModule, PipelineData, ModuleState, ModuleStatus
from core.ffmpeg_utils import ensure_ffmpeg
from core.encoder_config import EncoderConfig

logger = logging.getLogger("srt2web.module.video_muxer")
logger.setLevel(logging.INFO)


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
        # Video quality settings (must be initialized before configure())
        self._video_preset = "medium"
        self._gpu_preset = "p3"
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

    def write(self, data: PipelineData) -> PipelineData:
        """
        Write chunk to HLS stream (called by AsyncPipeline as output_sink).
        Convert input chunk to HLS segment and update manifest.
        """
        self._log("info", f"[VideoMuxer.write] Received data chunk {getattr(data, 'chunk_index', 'None')}")
        self._log("info", f"[VideoMuxer.write] Data type: {type(data)}")
        if hasattr(data, '__dict__'):
            self._log("info", f"[VideoMuxer.write] Data keys: {list(data.__dict__.keys())}")
            for key, value in data.__dict__.items():
                if 'path' in key.lower() or 'chunk' in key.lower():
                    self._log("info", f"[VideoMuxer.write] {key}: {value} (exists: {os.path.exists(value) if isinstance(value, str) and value else 'N/A'})")
        else:
            self._log("info", f"[VideoMuxer.write] No __dict__ attribute")
        
        # Ensure we have a video_chunk_path attribute for compatibility with the process method
        if hasattr(data, 'video_path') and not hasattr(data, 'video_chunk_path'):
            self._log("info", f"[VideoMuxer.write] Copying video_path to video_chunk_path for compatibility")
            data.video_chunk_path = data.video_path
        elif not hasattr(data, 'video_chunk_path'):
            # Try to get it from a dict
            if isinstance(data, dict) and 'video_path' in data:
                self._log("info", f"[VideoMuxer.write] Getting video_path from dict for video_chunk_path")
                data.video_chunk_path = data['video_path']
        
        # If we still don't have a video_chunk_path, we cannot process
        if not hasattr(data, 'video_chunk_path') or not data.video_chunk_path:
            self._log("warning", f"[VideoMuxer.write] No video_chunk_path available for chunk {getattr(data, 'chunk_index', 'None')}")
            return data
        
        # Log the video chunk path for debugging
        self._log("info", f"[VideoMuxer.write] video_chunk_path: {data.video_chunk_path}")
        self._log("info", f"[VideoMuxer.write] video_chunk_path exists: {os.path.exists(data.video_chunk_path)}")
        
        # Process the data through the video muxer's process method
        try:
            result = self.process(data)
            self._log("info", f"[VideoMuxer.write] process() returned: {type(result)}")
            if result is not None:
                self._log("info", f"[VideoMuxer.write] Result has video_chunk_path: {hasattr(result, 'video_chunk_path') and getattr(result, 'video_chunk_path', None)}")
            return result
        except Exception as e:
            self._log("error", f"[VideoMuxer.write] Error in process method: {e}")
            import traceback
            self._log("error", f"[VideoMuxer.write] Traceback: {traceback.format_exc()}")
            return data

        # Update cumulative duration for next segment (for logging/validation)
        expected_next_cumulative = data.cumulative_duration + chunk_duration
        drift = expected_next_cumulative - self._total_duration_emitted
        if abs(drift) > 0.01:  # 10ms threshold
            logger.warning(
                f"[VideoMuxer] Duration drift detected: expected {expected_next_cumulative:.3f}s, "
                f"was {self._total_duration_emitted:.3f}s (drift: {drift * 1000:.1f}ms)"
            )
        self._total_duration_emitted = expected_next_cumulative

        # DEBUG: Log segment timing
        logger.info(
            f"[VideoMuxer] Segment {self._segment_index}: duration={chunk_duration:.3f}s, offset={offset_sec}s, total={self._total_duration_emitted:.3f}s"
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
                f"#EXT-X-TARGETDURATION:{self._hls_segment_duration + 1}",
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

    def get_status(self) -> ModuleStatus:
        """Get current status including GPU encoder info."""
        status = super().get_status()
        # Determine actual encoder being used
        encoder_mode = self._encoder_config.encoder_mode

        # Show what encoder WILL be used based on config (even if not started yet)
        if encoder_mode == "auto":
            # Check if any GPU is available (from config or detected)
            gpu_available = any(self._gpu_info.values())
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

        status.extra["encoder_mode"] = encoder_mode
        status.extra["using_gpu"] = encoder_mode.startswith("gpu_")
        status.extra["gpu_available"] = self._gpu_info
        status.extra["gpu_preset"] = self._encoder_config.gpu_preset
        return status
