"""
WebRTC Output - Real-time streaming output using WebRTC.

Provides ultra-low latency streaming (<2s) using WebRTC technology.
Compatible with modern browsers and WebRTC clients.
"""

import asyncio
import json
import logging
import os
import threading
import time
import weakref
from pathlib import Path
from typing import Optional, Dict, Any
from fractions import Fraction

import numpy as np
from av import VideoFrame, AudioFrame

from core.output_sink import OutputSink
from core.module_base import PipelineData

# Import aiortc for WebRTC functionality
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, AudioStreamTrack
    from aiortc.codecs import get_decoder, get_encoder
    from aiortc.mediastreams import MediaStreamError
    from aiortc.rtcrtpsender import RTCRtpSender
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False

logger = logging.getLogger("srt2web.output.webrtc")


class WebRTCVideoTrack(VideoStreamTrack):
    """
    A video track that gets frames from an external source.
    """

    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.queue = queue
        self._start_time = None
        self._frame_count = 0

    async def recv(self):
        """Receive and return the next video frame."""
        try:
            # Get frame data from queue with timeout
            frame_data = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            
            if frame_data is None:  # Shutdown signal
                raise MediaStreamError
            
            if self._start_time is None:
                self._start_time = time.time()
                pts = 0
            else:
                pts = int((time.time() - self._start_time) * 90000)  # 90kHz clock
                
            # For now, generate a test pattern since we're not doing full decode/re-encode
            # In a production implementation, we would decode frame_data and re-encode
            frame = VideoFrame.from_ndarray(
                np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
                format="rgb24"
            )
            
            frame.pts = pts
            frame.time_base = Fraction(1, 90000)
            self._frame_count += 1
            return frame
        except asyncio.TimeoutError:
            # Generate a black frame if no data available
            frame = VideoFrame(width=640, height=480, format="yuv420p")
            if self._start_time is None:
                self._start_time = time.time()
                pts = 0
            else:
                pts = int((time.time() - self._start_time) * 90000)
            frame.pts = pts
            frame.time_base = Fraction(1, 90000)
            return frame


class WebRTCAudioTrack(AudioStreamTrack):
    """
    An audio track that gets frames from an external source.
    """

    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.queue = queue
        self._start_time = None
        self._sample_count = 0

    async def recv(self):
        """Receive and return the next audio frame."""
        try:
            # Get frame data from queue with timeout
            frame_data = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            
            if frame_data is None:  # Shutdown signal
                raise MediaStreamError
            
            if self._start_time is None:
                self._start_time = time.time()
                pts = 0
            else:
                # Calculate pts based on sample rate (48000 Hz)
                pts = int((time.time() - self._start_time) * 48000)
                
            # Generate test audio frame (silence with occasional tone for testing)
            frame = AudioFrame(format="s16", layout="stereo", samples=960)  # 20ms at 48kHz
            
            # Fill with silence
            for p in frame.planes:
                p[:] = b'\x00' * len(p)
                
            # Add a small test tone occasionally to verify audio is working
            if int(time.time() * 10) % 20 < 2:  # 10% of the time
                import math
                samples = frame.samples
                for i in range(samples):
                    t = i / 48000.0
                    value = int(3000 * math.sin(2 * math.pi * 440 * t))  # 440 Hz tone
                    if frame.layout.name == "mono":
                        frame.planes[0][i * 2:i * 2 + 2] = value.to_bytes(2, byteorder='little', signed=True)
                    else:  # stereo
                        sample_bytes = value.to_bytes(2, byteorder='little', signed=True)
                        frame.planes[0][i * 4:i * 4 + 2] = sample_bytes  # left channel
                        frame.planes[1][i * 4:i * 4 + 2] = sample_bytes  # right channel
            
            frame.pts = pts
            frame.time_base = Fraction(1, 48000)
            self._sample_count += frame.samples
            return frame
        except asyncio.TimeoutError:
            # Generate silence if no data available
            frame = AudioFrame(format="s16", layout="stereo", samples=960)  # 20ms at 48kHz
            if self._start_time is None:
                self._start_time = time.time()
                pts = 0
            else:
                pts = int((time.time() - self._start_time) * 48000)
            frame.pts = pts
            frame.time_base = Fraction(1, 48000)
            # Fill with silence
            for p in frame.planes:
                p[:] = b'\x00' * len(p)
            return frame


class WebRTCSubtitleTrack(VideoStreamTrack):
    """
    A video track that renders subtitles as text overlays.
    Sends subtitle cues via data channel for client-side rendering.
    """

    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self.queue = queue
        self._start_time = None
        self._current_cue: Optional[dict] = None
        self._width = 640
        self._height = 480

    async def recv(self):
        """Receive and return the next video frame with subtitle overlay."""
        try:
            cue_data = None
            try:
                cue_data = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass

            if cue_data is not None:
                self._current_cue = cue_data

            # Generate frame with current subtitle if available
            frame = VideoFrame(width=self._width, height=self._height, format="rgb24")
            
            if self._current_cue:
                # Draw subtitle on frame (simple text rendering)
                frame = self._render_subtitle_frame(self._current_cue)
            else:
                # Clear frame (black)
                frame = VideoFrame(width=self._width, height=self._height, format="rgb24")
                frame_array = np.zeros((self._height, self._width, 3), dtype=np.uint8)
                frame = frame.from_ndarray(frame_array, format="rgb24")

            if self._start_time is None:
                self._start_time = time.time()
                pts = 0
            else:
                pts = int((time.time() - self._start_time) * 90000)

            frame.pts = pts
            frame.time_base = Fraction(1, 90000)
            return frame

        except Exception as e:
            # Return black frame on error
            frame = VideoFrame(width=self._width, height=self._height, format="rgb24")
            frame_array = np.zeros((self._height, self._width, 3), dtype=np.uint8)
            return frame.from_ndarray(frame_array, format="rgb24")

    def _render_subtitle_frame(self, cue: dict) -> VideoFrame:
        """Render subtitle text onto a video frame."""
        text = cue.get("text", "")
        if not text:
            frame_array = np.zeros((self._height, self._width, 3), dtype=np.uint8)
            return VideoFrame.from_ndarray(frame_array, format="rgb24")

        # Create semi-transparent dark background for text
        frame_array = np.zeros((self._height, self._width, 3), dtype=np.uint8)
        
        # Add background bar at bottom
        bar_height = 80
        bar_y = self._height - bar_height
        frame_array[bar_y:self._height, :] = [0, 0, 0]
        
        # Add text using simple rendering (PIL would be better but keep it simple)
        # For now, just create a dark background - actual text rendering
        # would require PIL or similar library
        
        return VideoFrame.from_ndarray(frame_array, format="rgb24")


class WebRTCOutput(OutputSink):
    """
    WebRTC output for ultra-low latency streaming.
    
    Uses aiortc to establish WebRTC connections and stream encoded video/audio.
    Target latency: <2 seconds end-to-end.
    """

    def __init__(self, config: Optional[dict] = None):
        if not WEBRTC_AVAILABLE:
            raise ImportError("aiortc is required for WebRTC output. Install with: pip install aiortc")
            
        super().__init__("webrtc", config or {})
        
        # WebRTC configuration
        self._pcs: Dict[str, RTCPeerConnection] = {}  # Peer connections by client ID
        self._video_queues: Dict[str, asyncio.Queue] = {}
        self._audio_queues: Dict[str, asyncio.Queue] = {}
        self._video_tracks: Dict[str, WebRTCVideoTrack] = {}
        self._audio_tracks: Dict[str, WebRTCAudioTrack] = {}
        
        # Streaming configuration
        self._video_width = config.get("video_width", 640) if config else 640
        self._video_height = config.get("video_height", 480) if config else 480
        self._video_fps = config.get("video_fps", 30) if config else 30
        self._video_bitrate = config.get("video_bitrate", "1000k") if config else "1000k"
        
        self._audio_sample_rate = config.get("audio_sample_rate", 48000) if config else 48000
        self._audio_channels = config.get("audio_channels", 2) if config else 2
        self._audio_bitrate = config.get("audio_bitrate", "128k") if config else "128k"
        
        # Codec preferences
        self._video_codec = config.get("video_codec", "vp8") if config else "vp8"  # vp8, vp9, h264
        self._audio_codec = config.get("audio_codec", "opus") if config else "opus"  # opus, vorbis
        
        # STUN/TURN servers
        self._stun_servers = config.get("stun_servers", []) if config else []
        self._turn_servers = config.get("turn_servers", []) if config else []
        
        # Background tasks
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        
        # Statistics
        self._frames_encoded = 0
        self._bytes_sent = 0
        self._start_time = None
        # Timing tracking for frontend metrics
        self._last_process_time_ms: float = 0.0
        
        # Subtitles support via data channel
        self._subtitle_data_channels: Dict[str, asyncio.Queue] = {}
        self._subtitle_queues: Dict[str, asyncio.Queue] = {}
        self._subtitle_tracks: Dict[str, 'WebRTCSubtitleTrack'] = {}
        self._current_subtitles: Dict[str, dict] = {}  # Current active subtitle cues by client
        
        logger.info(f"WebRTC output initialized with {self._video_codec}/{self._audio_codec}")

    def configure(self, config: dict) -> None:
        """Apply configuration."""
        super().configure(config)
        
        self._video_width = config.get("video_width", self._video_width)
        self._video_height = config.get("video_height", self._video_height)
        self._video_fps = config.get("video_fps", self._video_fps)
        self._video_bitrate = config.get("video_bitrate", self._video_bitrate)
        
        self._audio_sample_rate = config.get("audio_sample_rate", self._audio_sample_rate)
        self._audio_channels = config.get("audio_channels", self._audio_channels)
        self._audio_bitrate = config.get("audio_bitrate", self._audio_bitrate)
        
        self._video_codec = config.get("video_codec", self._video_codec)
        self._audio_codec = config.get("audio_codec", self._audio_codec)
        
        self._stun_servers = config.get("stun_servers", self._stun_servers)
        self._turn_servers = config.get("turn_servers", self._turn_servers)
        
        logger.info(f"WebRTC output reconfigured: {self._video_codec}@{self._video_bitrate}, "
                   f"{self._audio_codec}@{self._audio_bitrate}")

    async def _initialize_peer_connection(self, client_id: str) -> RTCPeerConnection:
        """Initialize a new PeerConnection for a client."""
        # Create peer connection
        pc = RTCPeerConnection()
        self._pcs[client_id] = pc
        
        # Create queues for this client
        video_queue = asyncio.Queue(maxsize=10)
        audio_queue = asyncio.Queue(maxsize=10)
        subtitle_queue = asyncio.Queue(maxsize=10)
        self._video_queues[client_id] = video_queue
        self._audio_queues[client_id] = audio_queue
        self._subtitle_queues[client_id] = subtitle_queue
        
        # Create and add tracks
        video_track = WebRTCVideoTrack(video_queue)
        audio_track = WebRTCAudioTrack(audio_queue)
        subtitle_track = WebRTCSubtitleTrack(subtitle_queue)
        
        self._video_tracks[client_id] = video_track
        self._audio_tracks[client_id] = audio_track
        self._subtitle_tracks[client_id] = subtitle_track
        
        # Add tracks to peer connection
        video_sender = pc.addTrack(video_track)
        audio_sender = pc.addTrack(audio_track)
        
        # Create data channel for subtitles
        subtitle_channel = pc.createDataChannel("subtitles", ordered=False, maxRetransmits=0)
        self._subtitle_data_channels[client_id] = subtitle_channel
        
        # Set up data channel message handler
        @subtitle_channel.on("onmessage")
        def on_subtitle_message(event):
            logger.debug(f"Received message from client {client_id}: {event}")
        
        logger.debug(f"WebRTC peer connection created for client {client_id} with subtitle channel")
        return pc

    def _cleanup_peer_connection(self, client_id: str):
        """Clean up a peer connection and its associated resources."""
        if client_id in self._pcs:
            del self._pcs[client_id]
        if client_id in self._video_queues:
            del self._video_queues[client_id]
        if client_id in self._audio_queues:
            del self._audio_queues[client_id]
        if client_id in self._video_tracks:
            del self._video_tracks[client_id]
        if client_id in self._audio_tracks:
            del self._audio_tracks[client_id]

    async def handle_offer(self, client_id: str, offer_sdp: str, offer_type: str = "offer") -> str:
        """
        Handle WebRTC offer from client and return answer.
        
        Args:
            client_id: Unique identifier for the client
            offer_sdp: SDP offer from client
            offer_type: Type of SDP (usually "offer")
            
        Returns:
            SDP answer string
        """
        try:
            # Create or get peer connection
            if client_id not in self._pcs:
                pc = await self._initialize_peer_connection(client_id)
            else:
                pc = self._pcs[client_id]
            
            # Set remote description (the offer)
            offer = RTCSessionDescription(sdp=offer_sdp, type=offer_type)
            await pc.setRemoteDescription(offer)
            
            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            logger.info(f"WebRTC offer handled for client {client_id}")
            return pc.localDescription.sdp
            
        except Exception as e:
            logger.error(f"Error handling WebRTC offer for {client_id}: {e}")
            # Clean up on error
            self._cleanup_peer_connection(client_id)
            raise

    def start(self) -> None:
        """Start the WebRTC output."""
        if self._running:
            logger.warning("WebRTC output is already running")
            return
            
        logger.info("Starting WebRTC output...")
        self._running = True
        self._start_time = time.time()
        
        logger.info("WebRTC output started")

    def stop(self) -> None:
        """Stop the WebRTC output."""
        if not self._running:
            logger.warning("WebRTC output is not running")
            return
            
        logger.info("Stopping WebRTC output...")
        
        # Close all peer connections
        for client_id in list(self._pcs.keys()):
            try:
                # Note: Actual async closing would need event loop
                # For now, we just clean up references
                self._cleanup_peer_connection(client_id)
            except Exception as e:
                logger.error(f"Error cleaning up peer connection for {client_id}: {e}")
        
        self._running = False
        logger.info("WebRTC output stopped")

    def write(self, data: PipelineData) -> None:
        """
        Write encoded video/audio data to WebRTC clients.
        
        Expects PipelineData with:
        - video_chunk_path: Path to encoded video file 
        - audio_chunk_path: Path to encoded audio file
        OR
        - mixed_audio_path: Path to mixed audio (original + TTS)
        - dubbed_audio_path: Path to TTS-only audio
        
        Also handles subtitles:
        - subtitles_path: Path to .vtt subtitle file
        - cumulative_duration: For subtitle timing sync
        
        For now, this implementation queues placeholder data since full
        decode/re-encode is complex. In production, this would:
        1. Decode the input frames (H.264/AAC/etc)
        2. Re-encode to WebRTC-preferred formats (VP8/VP9 + Opus)
        3. Send to all connected clients
        """
        start_time = time.perf_counter()
        
        if not self._running:
            logger.debug("WebRTC output not running, dropping frame")
            return
        
        # Get subtitle data if available
        subtitle_cue = None
        if data.subtitles_path and os.path.exists(data.subtitles_path):
            try:
                # Read the latest subtitle data
                with open(data.subtitles_path, 'r', encoding='utf-8') as f:
                    vtt_content = f.read()
                
                # Parse the most recent subtitle entry
                subtitle_cue = self._parse_latest_subtitle(vtt_content, data.cumulative_duration or 0.0)
            except Exception as e:
                logger.debug(f"Error reading subtitles: {e}")
        
        # In a full implementation, we would process the actual media data
        # For now, we just signal that new data is available by putting
        # placeholder data in the queues to trigger frame generation
        
        # Notify all connected clients that new data is available
        for client_id in list(self._video_queues.keys()):
            try:
                # Put a placeholder to trigger frame generation
                if not self._video_queues[client_id].full():
                    self._video_queues[client_id].put_nowait(b"placeholder")
                if not self._audio_queues[client_id].full():
                    self._audio_queues[client_id].put_nowait(b"placeholder")
                
                # Send subtitle cue via data channel if available
                if subtitle_cue:
                    self._send_subtitle_cue(client_id, subtitle_cue)
                    # Also queue for subtitle track
                    if not self._subtitle_queues[client_id].full():
                        self._subtitle_queues[client_id].put_nowait(subtitle_cue)
                        
            except asyncio.QueueFull:
                # Drop if queue is full
                pass
            except Exception as e:
                logger.debug(f"Error queuing data for client {client_id}: {e}")
        
        # Track processing time for frontend metrics
        elapsed = (time.perf_counter() - start_time) * 1000
        self._last_process_time_ms = elapsed

    def _parse_latest_subtitle(self, vtt_content: str, base_time: float) -> Optional[dict]:
        """
        Parse VTT content and return the latest subtitle cue.
        
        Args:
            vtt_content: Full VTT file content
            base_time: Base timestamp for the current chunk
            
        Returns:
            Dict with 'text', 'start', 'end' or None
        """
        try:
            lines = vtt_content.strip().split('\n')
            current_cue = None
            cue_start = None
            cue_end = None
            cue_text_lines = []
            in_cue = False
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('WEBVTT') or line.startswith('NOTE'):
                    continue
                    
                # Check for timestamp line
                if '-->' in line:
                    if current_cue is not None:
                        # Save previous cue
                        pass
                    
                    # Parse timestamps
                    parts = line.split('-->')
                    if len(parts) == 2:
                        start_str = parts[0].strip()
                        end_str = parts[1].strip().split()[0]  # Ignore any additional info
                        
                        # Convert to seconds
                        cue_start = self._parse_vtt_timestamp(start_str)
                        cue_end = self._parse_vtt_timestamp(end_str)
                        
                        in_cue = True
                        cue_text_lines = []
                    continue
                
                # If in cue, collect text
                if in_cue and line:
                    cue_text_lines.append(line)
            
            # Return the last complete cue
            if cue_text_lines and cue_start is not None:
                return {
                    'text': ' '.join(cue_text_lines),
                    'start': base_time + cue_start,
                    'end': base_time + cue_end,
                    'base_time': base_time
                }
                
        except Exception as e:
            logger.debug(f"Error parsing VTT: {e}")
        
        return None

    def _parse_vtt_timestamp(self, timestamp: str) -> float:
        """
        Parse VTT timestamp (HH:MM:SS.mmm or MM:SS.mmm) to seconds.
        """
        try:
            parts = timestamp.replace(',', '.').split(':')
            if len(parts) == 3:  # HH:MM:SS.mmm
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:  # MM:SS.mmm
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                return float(timestamp)
        except:
            return 0.0

    def _send_subtitle_cue(self, client_id: str, cue: dict) -> None:
        """
        Send subtitle cue to client via data channel.
        
        Args:
            client_id: The client ID to send to
            cue: Dict with 'text', 'start', 'end' keys
        """
        try:
            if client_id in self._subtitle_data_channels:
                channel = self._subtitle_data_channels[client_id]
                if channel.readyState == 'open':
                    # Send as JSON
                    message = json.dumps({
                        'type': 'subtitle',
                        'text': cue.get('text', ''),
                        'start': cue.get('start', 0),
                        'end': cue.get('end', 0)
                    })
                    channel.send(message)
                    logger.debug(f"Sent subtitle cue to {client_id}: {cue.get('text', '')[:50]}...")
        except Exception as e:
            logger.debug(f"Error sending subtitle cue: {e}")

    def get_stream_info(self) -> dict:
        """Get stream information for clients."""
        return {
            "type": "webrtc",
            "webrtc_available": WEBRTC_AVAILABLE,
            "signaling_method": "HTTP POST /webrtc/offer",
            "video_codec": self._video_codec,
            "audio_codec": self._audio_codec,
            "video_resolution": f"{self._video_width}x{self._video_height}",
            "video_fps": self._video_fps,
            "audio_sample_rate": self._audio_sample_rate,
            "audio_channels": self._audio_channels,
            "subtitle_available": True,
            "subtitle_format": "webvtt",
            "subtitle_delivery": "data_channel",
            "stun_servers": self._stun_servers,
            "turn_servers": self._turn_servers,
            "active_connections": len(self._pcs)
        }

    def get_engine_status(self) -> dict:
        """Get detailed engine status."""
        return {
            "current_engine": "webrtc",
            "available": WEBRTC_AVAILABLE,
            "active_connections": len(self._pcs),
            "video_track_count": len(self._video_tracks),
            "audio_track_count": len(self._audio_tracks),
            "frames_encoded": self._frames_encoded,
            "bytes_sent": self._bytes_sent,
            "uptime_seconds": time.time() - self._start_time if self._start_time else 0,
            "configuration": {
                "video_codec": self._video_codec,
                "video_bitrate": self._video_bitrate,
                "video_resolution": f"{self._video_width}x{self._video_height}",
                "video_fps": self._video_fps,
                "audio_codec": self._audio_codec,
                "audio_bitrate": self._audio_bitrate,
                "audio_sample_rate": self._audio_sample_rate,
                "audio_channels": self._audio_channels
            }
        }


# Auto-registration
def _register():
    """Auto-register this output module."""
    try:
        from core.io_factory import OutputFactory
        OutputFactory.register("webrtc", WebRTCOutput)
        logger.info("WebRTC output registered successfully")
    except ImportError as e:
        logger.warning(f"Could not register WebRTC output: {e}")

_register()