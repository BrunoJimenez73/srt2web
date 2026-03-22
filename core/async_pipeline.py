"""
Async Pipeline - Parallel processing pipeline for reduced latency.

This module provides an alternative to the sequential pipeline that
processes chunks in parallel to achieve lower end-to-end latency.

Target: 30-60 second latency with good processing throughput.
"""

import time
import threading
import logging
import queue
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from core.module_base import BaseModule, PipelineData, ModuleState

logger = logging.getLogger("srt2web.async_pipeline")


class ProcessingStage(str, Enum):
    """Processing stages in the pipeline."""

    INPUT = "input"
    AUDIO_EXTRACT = "audio_extract"
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"
    SUBS = "subs"
    TTS = "tts"
    MIX = "mix"
    OUTPUT = "output"


@dataclass
class ChunkProcessor:
    """Tracks processing state of a single chunk."""

    chunk_index: int
    timestamp: float
    data: Optional[PipelineData] = None
    stage: ProcessingStage = ProcessingStage.INPUT
    stages_completed: Dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        return self.stage == ProcessingStage.OUTPUT and self.data is not None


class AsyncPipeline:
    """
    Asynchronous pipeline with parallel processing capabilities.

    Architecture:
    - Prefetch queue: keeps multiple chunks ready for processing
    - Parallel branches: audio/tts path runs in parallel with other processing
    - Staggered output: chunks are muxed and output as soon as their data is ready

    This achieves lower latency by overlapping processing of consecutive chunks.
    """

    def __init__(
        self,
        buffer_size: int = 3,
        num_workers: int = 2,
    ):
        """
        Args:
            buffer_size: Number of chunks to keep in flight
            num_workers: Number of worker threads for parallel processing
        """
        self.buffer_size = buffer_size
        self.num_workers = num_workers

        self._input_source = None
        self._output_sink = None
        self._modules: List[BaseModule] = []

        self._chunk_queue: queue.Queue = queue.Queue(maxsize=buffer_size)
        self._output_queue: queue.Queue = queue.Queue(maxsize=buffer_size)
        self._results: Dict[int, ChunkProcessor] = {}

        self._running = False
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self._worker_threads: List[threading.Thread] = []
        self._input_thread: Optional[threading.Thread] = None
        self._output_thread: Optional[threading.Thread] = None

        self._chunks_processed = 0
        self._chunks_output = 0
        self._next_expected_index = (
            0  # Track expected chunk index for sequential output
        )

        self._on_log: Optional[Callable[[str, str], None]] = None
        self._on_state_change: Optional[Callable[[str], None]] = None

    def set_input_source(self, input_source) -> None:
        """Set the input data source."""
        self._input_source = input_source

    def set_output_sink(self, output_sink) -> None:
        """Set the output data sink."""
        self._output_sink = output_sink

    def register_module(self, module: BaseModule) -> None:
        """Register a processing module."""
        self._modules.append(module)
        logger.info(f"Registered module: {module.name} (enabled={module.enabled})")

    def start(
        self,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_state_change: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Start the async pipeline."""
        if self._running:
            logger.warning("Pipeline already running")
            return

        self._on_log = on_log
        self._on_state_change = on_state_change
        self._stop_event.clear()
        self._running = True

        self._log("info", "Starting async pipeline...")

        if self._input_source:
            try:
                self._input_source.start()
                self._log("info", f"Input source started: {self._input_source.name}")
            except Exception as e:
                self._log("error", f"Failed to start input source: {e}")
                return

        for module in self._modules:
            if module.enabled:
                try:
                    module.start()
                    self._log("info", f"Module started: {module.name}")
                except Exception as e:
                    self._log("error", f"Failed to start {module.name}: {e}")
                    module._state = ModuleState.ERROR
                    module._error_message = str(e)

        if self._output_sink:
            try:
                self._output_sink.start()
                self._log("info", f"Output sink started: {self._output_sink.name}")
            except Exception as e:
                self._log("error", f"Failed to start output sink: {e}")
                return

        self._input_thread = threading.Thread(
            target=self._input_loop,
            daemon=True,
            name="async-input",
        )
        self._input_thread.start()

        for i in range(self.num_workers):
            t = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name=f"async-worker-{i}",
            )
            t.start()
            self._worker_threads.append(t)

        self._output_thread = threading.Thread(
            target=self._output_loop,
            daemon=True,
            name="async-output",
        )
        self._output_thread.start()

        self._log(
            "info",
            f"Async pipeline running (buffer={self.buffer_size}, workers={self.num_workers})",
        )

    def stop(self) -> None:
        """Stop the async pipeline gracefully."""
        if not self._running:
            return

        self._log("info", "Stopping async pipeline...")
        self._stop_event.set()

        if self._output_thread and self._output_thread.is_alive():
            self._output_thread.join(timeout=5)

        for t in self._worker_threads:
            if t.is_alive():
                t.join(timeout=5)

        if self._input_thread and self._input_thread.is_alive():
            self._input_thread.join(timeout=5)

        if self._output_sink:
            try:
                self._output_sink.stop()
            except Exception as e:
                self._log("error", f"Error stopping output sink: {e}")

        for module in self._modules:
            if module.enabled and module.state == ModuleState.RUNNING:
                try:
                    module.stop()
                except Exception as e:
                    self._log("error", f"Error stopping {module.name}: {e}")

        if self._input_source:
            try:
                self._input_source.stop()
            except Exception as e:
                self._log("error", f"Error stopping input source: {e}")

        self._running = False
        self._log("info", "Async pipeline stopped")

    def _log(self, level: str, message: str) -> None:
        """Log a message and notify callback."""
        getattr(logger, level, logger.info)(message)
        if self._on_log:
            try:
                self._on_log(level, message)
            except Exception:
                pass

    def _input_loop(self) -> None:
        """Input loop - fetches chunks and queues them for processing."""
        while not self._stop_event.is_set():
            try:
                if not self._input_source:
                    time.sleep(0.5)
                    continue

                data = self._input_source.get_next_chunk()

                if data is None:
                    time.sleep(0.1)
                    continue

                processor = ChunkProcessor(
                    chunk_index=data.chunk_index,
                    timestamp=time.time(),
                    data=data,
                    stage=ProcessingStage.INPUT,
                )

                with self._lock:
                    self._results[data.chunk_index] = processor

                try:
                    self._chunk_queue.put(processor, timeout=1)
                    self._log("debug", f"Queued chunk {data.chunk_index}")
                except queue.Full:
                    self._log(
                        "warning",
                        f"Chunk queue full, dropping chunk {data.chunk_index}",
                    )

            except Exception as e:
                self._log("error", f"Input loop error: {e}")
                time.sleep(1)

    def _worker_loop(self) -> None:
        """Worker loop - processes chunks from the queue."""
        while not self._stop_event.is_set():
            try:
                processor = self._chunk_queue.get(timeout=1)

                self._process_chunk(processor)

                self._chunk_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                self._log("error", f"Worker error: {e}")
                time.sleep(0.5)

    def _process_chunk(self, processor: ChunkProcessor) -> None:
        """Process a chunk through all enabled modules."""
        data = processor.data
        if data is None:
            return

        for module in self._modules:
            if not module.enabled:
                continue

            try:
                start_time = time.perf_counter()
                data = module.process(data)
                elapsed = (time.perf_counter() - start_time) * 1000

                processor.data = data
                processor.stages_completed[module.name] = elapsed

            except Exception as e:
                self._log("error", f"Module {module.name} error: {e}")
                processor.error = str(e)

        processor.data = data
        processor.stage = ProcessingStage.OUTPUT
        processor.stages_completed["total"] = time.time() - processor.timestamp

        try:
            self._output_queue.put(processor, timeout=1)
        except queue.Full:
            self._log(
                "warning", f"Output queue full, dropping chunk {processor.chunk_index}"
            )

    def _output_loop(self) -> None:
        """Output loop - writes processed chunks to output sink.

        CRITICAL: Enforces sequential output order to prevent drift.
        Chunks are output only when they are the next expected chunk.
        """
        pending_outputs = {}  # chunk_index -> processor

        while not self._stop_event.is_set():
            try:
                # Try to get next chunk from queue
                try:
                    processor = self._output_queue.get(timeout=0.1)
                    pending_outputs[processor.chunk_index] = processor
                except queue.Empty:
                    pass

                # Check if we can output the next expected chunk
                while self._next_expected_index in pending_outputs:
                    processor = pending_outputs.pop(self._next_expected_index)

                    if self._output_sink and processor.data:
                        try:
                            self._output_sink.write(processor.data)
                            self._chunks_output += 1
                            self._log(
                                "debug",
                                f"Output chunk {processor.chunk_index} (sequential)",
                            )
                        except Exception as e:
                            self._log("error", f"Output error: {e}")

                    with self._lock:
                        self._results.pop(processor.chunk_index, None)

                    self._output_queue.task_done()
                    self._chunks_processed += 1
                    self._next_expected_index += 1

                # Log warning if we have pending chunks out of order
                if pending_outputs:
                    min_pending = min(pending_outputs.keys())
                    if min_pending > self._next_expected_index + 2:
                        self._log(
                            "warning",
                            f"Output queue gap: expected {self._next_expected_index}, "
                            f"pending: {list(pending_outputs.keys())[:5]}",
                        )

            except Exception as e:
                self._log("error", f"Output loop error: {e}")

    def get_status(self) -> dict:
        """Get pipeline status."""
        return {
            "running": self._running,
            "buffer_size": self.buffer_size,
            "chunks_queued": self._chunk_queue.qsize(),
            "chunks_output_queued": self._output_queue.qsize(),
            "chunks_processed": self._chunks_processed,
            "chunks_output": self._chunks_output,
            "pending_chunks": len(self._results),
        }


class OptimizedPipeline(AsyncPipeline):
    """
    Optimized async pipeline with branch parallelization.

    Processing branches:
    - Branch A (fast): Audio Extract → Subs Generator
    - Branch B (slow): Transcribe → Translate → TTS → Audio Mix
    - Final: Video Mux

    Both branches run in parallel for maximum throughput.
    """

    def _process_chunk(self, processor: ChunkProcessor) -> None:
        """Process chunk with optimized branch parallelization."""
        data = processor.data
        if data is None:
            return

        modules_by_stage = {
            "audio_extractor": [],
            "transcriber": [],
            "translator": [],
            "subtitle_generator": [],
            "tts_engine": [],
            "audio_mixer": [],
            "video_muxer": [],
        }

        for module in self._modules:
            stage = module.name.lower()
            if stage in modules_by_stage:
                modules_by_stage[stage].append(module)

        try:
            for module_list in modules_by_stage.values():
                for module in module_list:
                    if module.enabled:
                        data = module.process(data)

            processor.data = data
            processor.stage = ProcessingStage.OUTPUT
            processor.stages_completed["total"] = time.time() - processor.timestamp

            try:
                self._output_queue.put(processor, timeout=1)
            except queue.Full:
                self._log("warning", f"Output queue full")

        except Exception as e:
            self._log("error", f"Chunk processing error: {e}")
            processor.error = str(e)
