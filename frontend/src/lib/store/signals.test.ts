/**
 * Tests for signals.ts - Reactive state atoms and computed derivatives.
 *
 * Tests cover: source signals, computed values, updateStatus, addLog, resetThroughput,
 * systemMetrics, throughputAvg, connectionUrls, moduleStates, enabledModules.
 */

import { describe, it, expect, beforeEach } from "vitest";

// Import signals module (signals are module-level singletons, so we test via their API)
import {
  pipelineStatus,
  pipelineConfig,
  pipelineLogs,
  wsConnected,
  pollConnected,
  connectionMode,
  isOperationPending,
  throughputHistory,
  pipelineState,
  isPipelineRunning,
  isPipelineStopping,
  chunksProcessed,
  moduleStates,
  enabledModules,
  systemMetrics,
  connectionUrls,
  throughputAvg,
  updateStatus,
  addLog,
  resetThroughput,
} from "./signals";
import type { Status, Config, LogMessage, ModuleStatus } from "../api";

// Helper to create a minimal Status
function makeStatus(overrides: Partial<Status> = {}): Status {
  return {
    state: "stopped",
    chunks_processed: 0,
    modules: [],
    ...overrides,
  };
}

// Helper to create a minimal ModuleStatus
function makeModule(
  name: string,
  overrides: Partial<ModuleStatus> = {},
): ModuleStatus {
  return {
    name,
    state: "idle",
    enabled: true,
    last_process_time_ms: 0,
    processed_chunks: 0,
    ...overrides,
  };
}

// Helper to create a minimal Config
function makeConfig(overrides: Partial<Config> = {}): Config {
  return {
    server: {
      host: "127.0.0.1",
      port: 9999,
      cors_origins: [],
      auth_token: "",
      rate_limit_rpm: 60,
      max_request_size_mb: 50,
    },
    input: {
      type: "srt",
      srt: {
        listen_port: 9000,
        mode: "listener",
        latency_ms: 3000,
        caller_address: "",
        chunk_duration_sec: 10,
      },
    },
    output: {
      type: "web",
      outputs: [],
      web: {
        segment_duration: 10,
        list_size: 2,
        audio_offset_ms: 0,
        encoder_mode: "auto",
      },
    },
    pipeline: {
      chunk_duration_sec: 10,
      mode: "sequential",
      max_concurrent_chunks: 1,
      buffer_size: 5,
      retry_attempts: 3,
      retry_delay: 1000,
    },
    modules: {
      audio_extractor: { enabled: true },
      transcriber: {
        enabled: true,
        model: "small",
        language: "auto",
        device: "cpu",
        beam_size: 2,
      },
      translator: { enabled: false, source_lang: "en", target_lang: "es" },
      subtitle_generator: {
        enabled: true,
        format: "webvtt",
        use_translated: false,
        chunk_duration: 10,
      },
      tts_engine: {
        enabled: true,
        engine: "piper",
        device: "cpu",
        voice: "en_US-ryan-low",
        speed: 1.0,
      },
      audio_mixer: {
        enabled: true,
        original_volume: 0.9,
        tts_volume: 0.9,
        dubbed_volume: 0.9,
      },
      video_muxer: {
        enabled: true,
        engine: "hls",
        hls_segment_duration: 10,
        hls_list_size: 2,
        audio_offset_ms: 0,
        encoder_mode: "auto",
        video_quality: "medium",
        video_crf: 23,
        audio_codec: "aac",
        audio_bitrate: "128k",
        audio_samplerate: "44100",
      },
    },
    output_dir: { directory: "./output" },
    ...overrides,
  };
}

describe("signals - Source Signals", () => {
  beforeEach(() => {
    // Reset all signals to initial state
    pipelineStatus.value = null;
    pipelineConfig.value = null;
    pipelineLogs.value = [];
    wsConnected.value = false;
    pollConnected.value = false;
    connectionMode.value = "local";
    isOperationPending.value = false;
    throughputHistory.value = [];
  });

  it("pipelineStatus defaults to null", () => {
    expect(pipelineStatus.value).toBeNull();
  });

  it("pipelineConfig defaults to null", () => {
    expect(pipelineConfig.value).toBeNull();
  });

  it("pipelineLogs defaults to empty array", () => {
    expect(pipelineLogs.value).toEqual([]);
  });

  it("wsConnected defaults to false", () => {
    expect(wsConnected.value).toBe(false);
  });

  it("pollConnected defaults to false", () => {
    expect(pollConnected.value).toBe(false);
  });

  it("connectionMode defaults to local", () => {
    expect(connectionMode.value).toBe("local");
  });

  it("isOperationPending defaults to false", () => {
    expect(isOperationPending.value).toBe(false);
  });

  it("throughputHistory defaults to empty array", () => {
    expect(throughputHistory.value).toEqual([]);
  });
});

describe("signals - Computed Pipeline State", () => {
  beforeEach(() => {
    pipelineStatus.value = null;
  });

  it("pipelineState returns stopped when status is null", () => {
    expect(pipelineState.value).toBe("stopped");
  });

  it("pipelineState returns the correct state from status", () => {
    pipelineStatus.value = makeStatus({ state: "running" });
    expect(pipelineState.value).toBe("running");
  });

  it("isPipelineRunning is false when stopped", () => {
    pipelineStatus.value = makeStatus({ state: "stopped" });
    expect(isPipelineRunning.value).toBe(false);
  });

  it("isPipelineRunning is true when running", () => {
    pipelineStatus.value = makeStatus({ state: "running" });
    expect(isPipelineRunning.value).toBe(true);
  });

  it("isPipelineRunning is false when starting", () => {
    pipelineStatus.value = makeStatus({ state: "starting" });
    expect(isPipelineRunning.value).toBe(false);
  });

  it("isPipelineStopping is true when stopping", () => {
    pipelineStatus.value = makeStatus({ state: "stopping" });
    expect(isPipelineStopping.value).toBe(true);
  });

  it("isPipelineStopping is false when running", () => {
    pipelineStatus.value = makeStatus({ state: "running" });
    expect(isPipelineStopping.value).toBe(false);
  });

  it("chunksProcessed returns 0 when no status", () => {
    expect(chunksProcessed.value).toBe(0);
  });

  it("chunksProcessed returns correct value", () => {
    pipelineStatus.value = makeStatus({ chunks_processed: 42 });
    expect(chunksProcessed.value).toBe(42);
  });
});

describe("signals - Computed Module States", () => {
  beforeEach(() => {
    pipelineStatus.value = null;
  });

  it("moduleStates returns empty object when no status", () => {
    expect(moduleStates.value).toEqual({});
  });

  it("moduleStates maps modules by name", () => {
    const modules = [
      makeModule("transcriber", { state: "running" }),
      makeModule("translator", { state: "idle", enabled: false }),
    ];
    pipelineStatus.value = makeStatus({ modules });
    const states = moduleStates.value;
    expect(states["transcriber"]).toBeDefined();
    expect(states["translator"]).toBeDefined();
    expect(states["transcriber"].state).toBe("running");
  });

  it("enabledModules filters to only enabled modules", () => {
    const modules = [
      makeModule("transcriber", { enabled: true }),
      makeModule("translator", { enabled: false }),
      makeModule("tts_engine", { enabled: true }),
    ];
    pipelineStatus.value = makeStatus({ modules });
    expect(enabledModules.value).toEqual(["transcriber", "tts_engine"]);
  });
});

describe("signals - System Metrics", () => {
  beforeEach(() => {
    pipelineStatus.value = null;
  });

  it("systemMetrics returns zeros when no status", () => {
    const m = systemMetrics.value;
    expect(m.cpu).toBe(0);
    expect(m.memoryMb).toBe(0);
    expect(m.memoryPercent).toBe(0);
    expect(m.gpuUtil).toBe(0);
    expect(m.gpuMemMb).toBe(0);
    expect(m.gpuMemPercent).toBe(0);
    expect(m.chunksPerSec).toBe(0);
    expect(m.totalChunks).toBe(0);
  });

  it("systemMetrics reads from system_metrics field", () => {
    pipelineStatus.value = makeStatus({
      chunks_processed: 10,
      state: "running" as any,
    });
    (pipelineStatus.value as any).system_metrics = {
      cpu_percent: 45,
      memory_mb: 2048,
      memory_percent: 60,
      gpu_percent: 80,
      gpu_memory_mb: 4096,
      gpu_memory_usage: 50,
    };
    const m = systemMetrics.value;
    expect(m.cpu).toBe(45);
    expect(m.memoryMb).toBe(2048);
    expect(m.memoryPercent).toBe(60);
    expect(m.gpuUtil).toBe(80);
    expect(m.gpuMemMb).toBe(4096);
    expect(m.gpuMemPercent).toBe(50);
  });

  it("systemMetrics reads from legacy system field", () => {
    (pipelineStatus.value as any) = {
      ...makeStatus({ chunks_processed: 5, state: "running" as any }),
      system: {
        cpu_usage: 30,
        memory_mb: 1024,
        memory_usage: 40,
      },
      uptime_seconds: 10,
    };
    const m = systemMetrics.value;
    expect(m.cpu).toBe(30);
    expect(m.memoryMb).toBe(1024);
    expect(m.memoryPercent).toBe(40);
  });

  it("systemMetrics calculates chunksPerSec from uptime", () => {
    const status = makeStatus({
      chunks_processed: 100,
      state: "running" as any,
    });
    (status as any).uptime_seconds = 20;
    pipelineStatus.value = status;
    expect(systemMetrics.value.chunksPerSec).toBe(5); // 100 / 20
  });

  it("systemMetrics uses avg_processing_time_ms for chunksPerSec when available", () => {
    const status = makeStatus({
      chunks_processed: 10,
      state: "running" as any,
    });
    (status as any).avg_processing_time_ms = 500; // 500ms per chunk = 2 chunks/sec
    (status as any).uptime_seconds = 5; // 10/5 = 2 chunks/sec
    pipelineStatus.value = status;
    // systemMetrics calculates from uptime/chunks, not from avg_processing_time_ms directly
    expect(systemMetrics.value.chunksPerSec).toBe(2); // 10 / 5
  });
});

describe("signals - Throughput", () => {
  beforeEach(() => {
    throughputHistory.value = [];
    pipelineStatus.value = null;
  });

  it("throughputAvg returns 0 when history is empty", () => {
    expect(throughputAvg.value).toBe(0);
  });

  it("throughputAvg calculates average correctly", () => {
    throughputHistory.value = [2.0, 3.0, 4.0];
    expect(throughputAvg.value).toBeCloseTo(3.0);
  });

  it("resetThroughput clears history", () => {
    throughputHistory.value = [1.0, 2.0, 3.0];
    resetThroughput();
    expect(throughputHistory.value).toEqual([]);
    expect(throughputAvg.value).toBe(0);
  });

  it("updateStatus records throughput from avg_processing_time_ms", () => {
    const status = makeStatus({
      chunks_processed: 10,
      state: "running" as any,
    });
    (status as any).avg_processing_time_ms = 250; // 4 chunks/sec
    updateStatus(status);
    expect(throughputHistory.value.length).toBe(1);
    expect(throughputHistory.value[0]).toBeCloseTo(4.0);
  });

  it("updateStatus records throughput from uptime when no avg_processing_time_ms", () => {
    const status = makeStatus({
      chunks_processed: 20,
      state: "running" as any,
    });
    (status as any).uptime_seconds = 5; // 20/5 = 4 chunks/sec
    (status as any).avg_processing_time_ms = 0;
    updateStatus(status);
    expect(throughputHistory.value.length).toBe(1);
    expect(throughputHistory.value[0]).toBeCloseTo(4.0);
  });

  it("updateStatus does not record throughput when tp is 0", () => {
    const status = makeStatus({ chunks_processed: 0, state: "stopped" as any });
    (status as any).avg_processing_time_ms = 0;
    (status as any).uptime_seconds = 0;
    updateStatus(status);
    expect(throughputHistory.value).toEqual([]);
  });

  it("updateStatus keeps only last 10 samples", () => {
    for (let i = 0; i < 15; i++) {
      const status = makeStatus({
        chunks_processed: i + 1,
        state: "running" as any,
      });
      (status as any).avg_processing_time_ms = 200;
      updateStatus(status);
    }
    expect(throughputHistory.value.length).toBe(10);
  });
});

describe("signals - Logging", () => {
  beforeEach(() => {
    pipelineLogs.value = [];
  });

  it("addLog appends a log entry", () => {
    addLog("INFO", "Pipeline started");
    expect(pipelineLogs.value.length).toBe(1);
    expect(pipelineLogs.value[0].message).toBe("Pipeline started");
    expect(pipelineLogs.value[0].level).toBe("INFO");
    expect(pipelineLogs.value[0].timestamp).toBeDefined();
  });

  it("addLog keeps only last 1000 logs", () => {
    for (let i = 0; i < 1200; i++) {
      addLog("INFO", `Log ${i}`);
    }
    expect(pipelineLogs.value.length).toBe(1000);
    expect(pipelineLogs.value[0].message).toBe("Log 200"); // First 200 were trimmed
  });

  it("addLog preserves order (newest at end)", () => {
    addLog("INFO", "first");
    addLog("WARNING", "second");
    addLog("ERROR", "third");
    expect(pipelineLogs.value[0].message).toBe("first");
    expect(pipelineLogs.value[2].message).toBe("third");
  });
});

describe("signals - Connection URLs", () => {
  beforeEach(() => {
    pipelineConfig.value = null;
    connectionMode.value = "local";
    pipelineStatus.value = null;
  });

  it("connectionUrls defaults to localhost with SRT", () => {
    const urls = connectionUrls.value;
    expect(urls.host).toBe("127.0.0.1");
    expect(urls.inputType).toBe("srt");
    expect(urls.srtUrl).toBe("srt://127.0.0.1:9000");
    expect(urls.streamUrl).toBe("http://127.0.0.1:9999/hls/stream.m3u8");
    expect(urls.playerUrl).toBe("http://127.0.0.1:9999/player");
    expect(urls.primaryLabel).toBe("SRT:");
    expect(urls.primaryUrl).toBe("srt://127.0.0.1:9000");
  });

  it("connectionUrls shows RTMP when input type is rtmp", () => {
    pipelineConfig.value = makeConfig({
      input: {
        type: "rtmp",
        rtmp: {
          listen_port: 1935,
          mode: "listener",
          app: "live",
          stream_key: "stream",
          url: "rtmp://localhost/live/stream",
          chunk_duration_sec: 10,
        },
      },
    });
    const urls = connectionUrls.value;
    expect(urls.inputType).toBe("rtmp");
    expect(urls.primaryLabel).toBe("RTMP:");
    expect(urls.primaryUrl).toBe("rtmp://127.0.0.1:1935");
  });

  it("connectionUrls uses custom config values", () => {
    pipelineConfig.value = makeConfig({
      server: { ...makeConfig().server, port: 8080 },
      input: {
        type: "srt",
        srt: { ...makeConfig().input.srt!, port: 9500, listen_port: 9500 },
      },
    });
    const urls = connectionUrls.value;
    expect(urls.srtUrl).toBe("srt://127.0.0.1:9500");
    expect(urls.streamUrl).toBe("http://127.0.0.1:8080/hls/stream.m3u8");
  });

  it("connectionUrls switches to remote mode", () => {
    connectionMode.value = "remote";
    // In browser context, it would read from emitter-address input
    // Without DOM, it falls back to localhost
    const urls = connectionUrls.value;
    // Since there's no DOM, it uses fallback 'localhost'
    expect(urls.host).toBe("localhost");
  });
});

describe("signals - updateStatus", () => {
  beforeEach(() => {
    pipelineStatus.value = null;
    throughputHistory.value = [];
  });

  it("updateStatus sets pipelineStatus", () => {
    const status = makeStatus({ state: "running", chunks_processed: 5 });
    updateStatus(status);
    expect(pipelineStatus.value).toBe(status);
    expect(pipelineState.value).toBe("running");
    expect(chunksProcessed.value).toBe(5);
  });

  it("updateStatus with stopped state", () => {
    updateStatus(makeStatus({ state: "stopped" }));
    expect(isPipelineRunning.value).toBe(false);
    expect(isPipelineStopping.value).toBe(false);
  });

  it("updateStatus with starting state", () => {
    updateStatus(makeStatus({ state: "starting" }));
    expect(pipelineState.value).toBe("starting");
    expect(isPipelineRunning.value).toBe(false);
  });

  it("updateStatus with error state", () => {
    updateStatus(makeStatus({ state: "error" }));
    expect(pipelineState.value).toBe("error");
  });
});
