"""
WebRTC Engine - Streaming via WebRTC using aiortc.

Provides real-time WebRTC streaming with:
- Video track from HLS segments (decoded via PyAV)
- Audio track from mixed audio WAV files
- Data channel for subtitles with proper timing
"""

import asyncio
import contextlib
import json as JSON
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from aiortc import AudioStreamTrack, VideoStreamTrack

logger = logging.getLogger("srt2web.webrtc_engine")


@dataclass
class SubtitleCue:
    """Subtitle cue data structure."""

    start: float
    end: float
    text: str


@dataclass
class MediaBuffer:
    """Shared buffer for video/audio data pushed by the pipeline."""

    current_video_path: str = ""
    current_audio_path: str = ""
    accumulated_duration: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)


class WebRTCEngine:
    """
    WebRTC Engine for streaming video/audio and subtitles.

    Uses aiortc to handle WebRTC connections with the browser.
    Receives real video/audio data via push_video_path/push_audio_path.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}

        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready_event = threading.Event()

        self._output_dir = Path(self.config.get("output_dir", "./output/webrtc"))
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._subtitle_vtt_path = self._output_dir.parent.parent / "subtitles" / "subs.vtt"
        self._current_subtitles: list[SubtitleCue] = []
        self._last_subtitle_update = 0.0

        self._connections: dict[str, "WebRTCConnection"] = {}
        self._connection_lock = threading.Lock()

        self._media_buffer = MediaBuffer()

        self._video_codec = self.config.get("video_codec", "VP8")
        self._audio_codec = self.config.get("audio_codec", "opus")

        logger.info(f"WebRTC Engine initialized (video={self._video_codec}, audio={self._audio_codec})")

    def set_output_dir(self, output_dir: str) -> None:
        """Set the output directory."""
        self._output_dir = Path(output_dir)
        self._subtitle_vtt_path = self._output_dir.parent.parent / "subtitles" / "subs.vtt"

    def push_video_path(self, path: str) -> None:
        """Push video file path for WebRTC tracks to consume."""
        with self._media_buffer.lock:
            self._media_buffer.current_video_path = path

    def push_audio_path(self, path: str) -> None:
        """Push audio file path for WebRTC tracks to consume."""
        with self._media_buffer.lock:
            self._media_buffer.current_audio_path = path

    def update_accumulated_duration(self, duration: float) -> None:
        """Update accumulated stream duration for subtitle timing."""
        with self._media_buffer.lock:
            self._media_buffer.accumulated_duration = duration

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

        def run_loop() -> None:
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

        if not self._ready_event.wait(timeout=5.0):
            raise RuntimeError("WebRTC event loop failed to start")

        logger.info("WebRTC engine started")

    def stop(self) -> None:
        """Stop the WebRTC engine."""
        if not self._running:
            return

        self._running = False

        with self._connection_lock:
            for conn in list(self._connections.values()):
                conn.close()
            self._connections.clear()

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        logger.info("WebRTC engine stopped")

    def _load_subtitles(self) -> list[SubtitleCue]:
        """Load current subtitles from VTT file."""
        if not Path(self._subtitle_vtt_path).exists():
            return []

        try:
            mtime = Path(self._subtitle_vtt_path).stat().st_mtime
            if mtime == self._last_subtitle_update:
                return self._current_subtitles

            self._last_subtitle_update = mtime

            cues = []
            with open(self._subtitle_vtt_path, encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            import re

            time_regex = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})")

            i = 0
            while i < len(lines):
                match = time_regex.match(lines[i])
                if match:
                    start = (
                        int(match.group(1)) * 3600
                        + int(match.group(2)) * 60
                        + int(match.group(3))
                        + int(match.group(4)) / 1000
                    )
                    end = (
                        int(match.group(5)) * 3600
                        + int(match.group(6)) * 60
                        + int(match.group(7))
                        + int(match.group(8)) / 1000
                    )

                    text_lines = []
                    j = i + 1
                    while j < len(lines) and lines[j].strip():
                        text_lines.append(lines[j].strip())
                        j += 1

                    if text_lines:
                        cues.append(SubtitleCue(start=start, end=end, text="\n".join(text_lines)))
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
        """
        from aiortc import RTCPeerConnection, RTCSessionDescription

        pc = RTCPeerConnection()
        conn = WebRTCConnection(client_id=client_id, pc=pc, engine=self)

        with self._connection_lock:
            self._connections[client_id] = conn

        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type=sdp_type))

        video_track = WebRTCVideoTrack(engine=self, client_id=client_id)
        audio_track = WebRTCAudioTrack(engine=self, client_id=client_id)

        pc.addTrack(video_track)
        pc.addTrack(audio_track)

        @pc.on("datachannel")
        def on_datachannel(channel: Any) -> None:
            logger.info(f"Data channel received: {channel.label}")
            if channel.label == "subtitles":
                conn.subtitle_channel = channel

                @channel.on("message")  # type: ignore
                def on_message(message: str) -> None:
                    try:
                        data = JSON.loads(message)  # was JSON.parse (invalid); loads is stdlib equivalent
                        logger.info(f"Received from client: {data}")
                    except Exception:
                        pass

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await pc.iceGatheringStateComplete  # type: ignore[attr-defined]

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

    def __init__(self, client_id: str, pc: Any, engine: WebRTCEngine) -> None:
        self.client_id = client_id
        self.pc = pc
        self.engine = engine
        self.subtitle_channel = None
        self._last_subtitle_check = 0.0

        self._start_subtitle_polling()

    def _start_subtitle_polling(self) -> None:
        """Start polling for subtitle updates."""

        def poll() -> None:
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
        if now - self._last_subtitle_check < 0.5:
            return

        self._last_subtitle_check = now

        subtitles = self.engine._load_subtitles()
        if not subtitles:
            return

        # Use accumulated duration from pipeline for subtitle timing
        with self.engine._media_buffer.lock:
            current_time = self.engine._media_buffer.accumulated_duration

        if current_time <= 0:
            return

        for cue in subtitles:
            if cue.start <= current_time <= cue.end:
                import json

                self.subtitle_channel.send(
                    json.dumps(
                        {
                            "type": "subtitle",
                            "text": cue.text,
                            "start": cue.start,
                            "end": cue.end,
                        }
                    )
                )
                break

    def close(self) -> None:
        """Close the connection."""
        with contextlib.suppress(Exception):
            self.pc.close()
        self.engine.remove_connection(self.client_id)


class WebRTCVideoTrack(VideoStreamTrack):
    """Video track for WebRTC streaming using real HLS segment frames."""

    def __init__(self, engine: WebRTCEngine, client_id: str):
        super().__init__()
        self.engine = engine
        self.client_id = client_id
        self._frame_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=300)
        self._current_path = ""
        self._load_lock = asyncio.Lock()

    async def recv(self) -> Any:
        """Receive next video frame from decoded HLS segments."""
        pts, time_base = await self.next_timestamp()

        frame = await self._get_cached_frame()
        if frame is None:
            from av import VideoFrame

            frame = VideoFrame.from_ndarray(np.zeros((720, 1280, 3), dtype=np.uint8), format="bgr24")

        frame.pts = pts
        frame.time_base = time_base
        return frame

    async def _get_cached_frame(self) -> Any | None:
        """Get next frame from cache, loading more if needed."""
        if not self._frame_queue.empty():
            return await self._frame_queue.get()

        await self._load_frames()

        if not self._frame_queue.empty():
            return await self._frame_queue.get()
        return None

    async def _load_frames(self) -> None:
        """Load frames from current video path into queue."""
        async with self._load_lock:
            if not self._frame_queue.empty():
                return

            engine_path = ""
            with self.engine._media_buffer.lock:
                engine_path = self.engine._media_buffer.current_video_path

            if not engine_path or engine_path == self._current_path:
                return

            self._current_path = engine_path

            loop = asyncio.get_event_loop()
            frames = await loop.run_in_executor(None, self._decode_frames, engine_path)

            for frame in frames:
                try:
                    self._frame_queue.put_nowait(frame)
                except asyncio.QueueFull:
                    break

    @staticmethod
    def _decode_frames(path: str) -> list[Any]:
        """Decode all video frames from a file (runs in executor thread)."""
        import av

        frames = []
        try:
            container = av.open(path)
            stream = container.streams.video[0]
            for packet in container.demux(stream):
                for frame in packet.decode():
                    frames.append(frame)
                    if len(frames) >= 300:
                        break
                if len(frames) >= 300:
                    break
            container.close()
        except Exception as e:
            logger.warning(f"WebRTC video decode error: {e}")
        return frames


class WebRTCAudioTrack(AudioStreamTrack):
    """Audio track for WebRTC streaming using real mixed audio samples."""

    def __init__(self, engine: WebRTCEngine, client_id: str):
        super().__init__()
        self.engine = engine
        self.client_id = client_id
        self._sample_buffer = np.array([], dtype=np.float32)
        self._sample_rate = 48000
        self._current_path = ""

    async def recv(self) -> Any:
        """Receive next audio frame from mixed audio files."""
        pts, time_base = await self.next_timestamp()  # type: ignore[attr-defined]

        samples = await self._get_samples(960)

        from av import AudioFrame

        frame = AudioFrame(samples, layout="mono", rate=self._sample_rate)  # type: ignore[call-arg,arg-type]
        frame.pts = pts
        frame.time_base = time_base
        return frame

    async def _get_samples(self, n: int) -> np.ndarray:
        """Get n audio samples, refilling from file if needed."""
        if len(self._sample_buffer) < n:
            await self._refill_buffer()

        if len(self._sample_buffer) >= n:
            result = self._sample_buffer[:n].copy()
            self._sample_buffer = self._sample_buffer[n:]
            return result
        else:
            result = self._sample_buffer.copy()
            self._sample_buffer = np.array([], dtype=np.float32)
            return np.pad(result, (0, n - len(result)))

    async def _refill_buffer(self) -> None:
        """Refill audio buffer from the latest mixed audio file."""
        engine_path = ""
        with self.engine._media_buffer.lock:
            engine_path = self.engine._media_buffer.current_audio_path

        if not engine_path or engine_path == self._current_path:
            return

        self._current_path = engine_path

        loop = asyncio.get_event_loop()
        samples, rate = await loop.run_in_executor(None, self._read_audio, engine_path)

        if rate != self._sample_rate:
            new_len = int(len(samples) * self._sample_rate / rate)
            indices = np.linspace(0, len(samples) - 1, new_len)
            samples = np.interp(indices, np.arange(len(samples)), samples)

        self._sample_buffer = np.concatenate([self._sample_buffer, samples])

    @staticmethod
    def _read_audio(path: str) -> tuple[np.ndarray, int]:
        """Read WAV audio file and return (samples as float32, sample_rate)."""
        import wave

        try:
            with wave.open(str(path), "rb") as wf:
                rate = wf.getframerate()
                data = wf.readframes(wf.getnframes())
                samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            return samples, rate
        except Exception as e:
            logger.warning(f"WebRTC audio read error: {e}")
            return np.array([], dtype=np.float32), 48000
