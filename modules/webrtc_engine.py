"""
WebRTC Engine - Streaming via WebRTC using aiortc.

This module provides WebRTC streaming capabilities using the aiortc library.
It handles RTCPeerConnection, tracks, and data channels for subtitles.
"""

import asyncio
import logging
import os
import threading
import time
import json as JSON
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# aiortc imports
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole
from aiortc import VideoStreamTrack, AudioStreamTrack

# av imports for frame handling
from av import VideoFrame, AudioFrame
import numpy as np

logger = logging.getLogger("srt2web.webrtc_engine")


@dataclass
class SubtitleCue:
    """Subtitle cue data structure."""
    start: float
    end: float
    text: str


class WebRTCEngine:
    """
    WebRTC Engine for streaming video/audio and subtitles.
    
    Uses aiortc to handle WebRTC connections with the browser.
    Supports:
    - Video track streaming
    - Audio track streaming  
    - Data channel for subtitles
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # State
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready_event = threading.Event()
        
        # Directory for chunks
        self._output_dir = self.config.get("output_dir", "./output/webrtc")
        os.makedirs(self._output_dir, exist_ok=True)
        
        # Subtitle state
        self._subtitle_vtt_path = os.path.join(self._output_dir, "..", "subtitles", "subs.vtt")
        self._current_subtitles: List[SubtitleCue] = []
        self._last_subtitle_update = 0.0
        
        # Active connections
        self._connections: Dict[str, 'WebRTCConnection'] = {}
        self._connection_lock = threading.Lock()
        
        # Video/Audio settings
        self._video_codec = self.config.get("video_codec", "VP8")
        self._audio_codec = self.config.get("audio_codec", "opus")
        
        logger.info(f"WebRTC Engine initialized (video={self._video_codec}, audio={self._audio_codec})")

    def set_output_dir(self, output_dir: str) -> None:
        """Set the output directory."""
        self._output_dir = output_dir
        self._subtitle_vtt_path = os.path.join(os.path.dirname(output_dir), "subtitles", "subs.vtt")

    @property
    def running(self) -> bool:
        """Check if engine is running."""
        return self._running

    def start(self) -> None:
        """Start the WebRTC engine event loop."""
        if self._running:
            logger.warning("WebRTC engine already running")
            return
            
        self._running = True
        
        # Create asyncio event loop in a separate thread
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            logger.info("WebRTC event loop started")
            self._ready_event.set()
            
            try:
                self._loop.run_forever()
            finally:
                self._loop.close()
                logger.info("WebRTC event loop stopped")
        
        self._thread = threading.Thread(target=run_loop, daemon=True, name="webrtc-loop")
        self._thread.start()
        
        # Wait for the loop to be ready
        if not self._ready_event.wait(timeout=5.0):
            raise RuntimeError("WebRTC event loop failed to start")
            
        logger.info("WebRTC engine started")

    def stop(self) -> None:
        """Stop the WebRTC engine."""
        if not self._running:
            return
            
        self._running = False
        
        # Close all connections
        with self._connection_lock:
            for conn in list(self._connections.values()):
                conn.close()
            self._connections.clear()
        
        # Stop the event loop
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            
        logger.info("WebRTC engine stopped")

    def _load_subtitles(self) -> List[SubtitleCue]:
        """Load current subtitles from VTT file."""
        if not os.path.exists(self._subtitle_vtt_path):
            return []
            
        try:
            # Check if file changed
            mtime = os.path.getmtime(self._subtitle_vtt_path)
            if mtime == self._last_subtitle_update:
                return self._current_subtitles
                
            self._last_subtitle_update = mtime
            
            cues = []
            with open(self._subtitle_vtt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple VTT parsing
            lines = content.split('\n')
            time_regex_pattern = r'(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})'
            import re
            time_regex = re.compile(time_regex_pattern)
            
            i = 0
            while i < len(lines):
                match = time_regex.match(lines[i])
                if match:
                    start = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3)) + int(match.group(4)) / 1000
                    end = int(match.group(5)) * 3600 + int(match.group(6)) * 60 + int(match.group(7)) + int(match.group(8)) / 1000
                    
                    # Get text
                    text_lines = []
                    j = i + 1
                    while j < len(lines) and lines[j].strip():
                        text_lines.append(lines[j].strip())
                        j += 1
                    
                    if text_lines:
                        cues.append(SubtitleCue(start=start, end=end, text='\n'.join(text_lines)))
                    i = j
                else:
                    i += 1
            
            self._current_subtitles = cues
            return cues
            
        except Exception as e:
            logger.warning(f"Error loading subtitles: {e}")
            return []

    async def handle_offer(self, client_id: str, sdp: str, sdp_type: str = "offer") -> str:
        """
        Handle WebRTC offer and return answer SDP.
        
        Args:
            client_id: Unique client identifier
            sdp: SDP offer from client
            sdp_type: SDP type (usually "offer")
            
        Returns:
            SDP answer to send back to client
        """
        from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, AudioStreamTrack
        from aiortc.contrib.media import MediaBlackhole, MediaRecorder
        
        # Create peer connection
        pc = RTCPeerConnection()
        
        # Create connection handler
        conn = WebRTCConnection(
            client_id=client_id,
            pc=pc,
            engine=self
        )
        
        with self._connection_lock:
            self._connections[client_id] = conn
        
        # Set remote description
        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type=sdp_type))
        
        # Create media tracks (from FFmpeg output)
        # For now, we'll use placeholder tracks - in production these would come from the video muxer
        video_track = WebRTCVideoTrack(engine=self, client_id=client_id)
        audio_track = WebRTCAudioTrack(engine=self, client_id=client_id)
        
        # Add tracks to connection
        pc.addTrack(video_track)
        pc.addTrack(audio_track)
        
        # Handle incoming data channels from client
        @pc.on("datachannel")
        def on_datachannel(channel):
            logger.info(f"Data channel received: {channel.label}")
            if channel.label == "subtitles":
                conn.subtitle_channel = channel
                
                @channel.on("message")
                def on_message(message):
                    try:
                        data = JSON.parse(message)
                        logger.info(f"Received from client: {data}")
                    except:
                        pass
        
        # Create answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        # Wait for ICE gathering to complete
        await pc.iceGatheringStateComplete
        
        logger.info(f"WebRTC connection established for client {client_id}")
        
        return pc.localDescription.sdp

    def remove_connection(self, client_id: str) -> None:
        """Remove a client connection."""
        with self._connection_lock:
            if client_id in self._connections:
                self._connections[client_id].close()
                del self._connections[client_id]
                logger.info(f"WebRTC connection removed: {client_id}")


class WebRTCConnection:
    """Handle a single WebRTC connection."""
    
    def __init__(self, client_id: str, pc, engine: WebRTCEngine):
        self.client_id = client_id
        self.pc = pc
        self.engine = engine
        self.subtitle_channel = None
        self._last_subtitle_check = 0.0
        
        # Set up subtitle polling
        self._start_subtitle_polling()
    
    def _start_subtitle_polling(self) -> None:
        """Start polling for subtitle updates."""
        def poll():
            while self.pc.connectionState != "closed":
                time.sleep(0.5)
                self._check_and_send_subtitles()
        
        thread = threading.Thread(target=poll, daemon=True)
        thread.start()
    
    def _check_and_send_subtitles(self) -> None:
        """Check for new subtitles and send via data channel."""
        if not self.subtitle_channel or self.subtitle_channel.readyState != "open":
            return
        
        now = time.time()
        if now - self._last_subtitle_check < 0.5:  # Check every 500ms
            return
            
        self._last_subtitle_check = now
        
        # Get current subtitle based on playback time
        # For simplicity, we'll send the latest available subtitle
        subtitles = self.engine._load_subtitles()
        if subtitles:
            # Find current subtitle based on time
            current_time = time.time() % 3600  # Simplified - use actual timestamp in production
            for cue in subtitles:
                if cue.start <= current_time <= cue.end:
                    import json
                    self.subtitle_channel.send(json.dumps({
                        "type": "subtitle",
                        "text": cue.text,
                        "start": cue.start,
                        "end": cue.end
                    }))
                    break
    
    def close(self) -> None:
        """Close the connection."""
        try:
            self.pc.close()
        except:
            pass
        self.engine.remove_connection(self.client_id)


class WebRTCVideoTrack(VideoStreamTrack):
    """Video track for WebRTC streaming."""
    
    def __init__(self, engine: WebRTCEngine, client_id: str):
        super().__init__()
        self.engine = engine
        self.client_id = client_id
        self._last_frame = None
        
    async def recv(self):
        """Receive next video frame."""
        pts, time_base = await self.next_timestamp()
        
        # Get frame from video muxer output
        # For now, return black frames - in production this would read from the pipeline
        import numpy as np
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        # Create VideoFrame
        from av import VideoFrame
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        
        return video_frame


class WebRTCAudioTrack(AudioStreamTrack):
    """Audio track for WebRTC streaming."""
    
    def __init__(self, engine: WebRTCEngine, client_id: str):
        super().__init__()
        self.engine = engine
        self.client_id = client_id
        
    async def recv(self):
        """Receive next audio frame."""
        pts, time_base = await self.next_timestamp()
        
        # Get audio from video muxer output
        # For now, return silent audio
        import numpy as np
        samples = np.zeros(1024, dtype=np.float32)
        
        from av import AudioFrame
        audio_frame = AudioFrame(samples, layout='mono', rate=48000)
        audio_frame.pts = pts
        audio_frame.time_base = time_base
        
        return audio_frame