/**
 * Effects - DOM updates driven by signal changes.
 *
 * Each effect() block runs whenever its dependencies (read .value) change.
 * These replace the imperative `update*` functions from the old dashboard.ts.
 *
 * Call `startEffects()` once during init() and `stopEffects()` on cleanup.
 */

import { effect, batch } from "@preact/signals-core";
import {
  pipelineStatus,
  pipelineConfig,
  wsConnected,
  throughputHistory,
  throughputAvg,
  pipelineLatency,
  connectionUrls,
  systemMetrics,
  isPipelineRunning,
  connectionMode,
  pipelineLogs,
  cpuHistory,
  gpuHistory,
  cpuAlertActive,
  syncDriftMs,
  syncState,
  syncCorrectionActive,
  emitterAddress,
} from "./signals";
import {
  PipelineState,
  normalizePipelineState,
  getModuleState,
  ModuleState,
} from "../types/state";
import { startClockUpdates } from "../utils/clock";
import { ENCODER_LABELS } from "../utils";
import { addLog as addLogToPanel } from "../modules/logpanel";

// ── Element refs (lazy) ────────────────────────────────────────────────────────

function el<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

// ── effectPipelineIndicator ────────────────────────────────────────────────────

let _efPipelineIndicator: (() => void) | null = null;
let _efModuleIndicators: (() => void) | null = null;
let _efModuleStatusDots: (() => void) | null = null;
let _efStatusCard: (() => void) | null = null;

function startStatusEffects(): void {
  // Status dot + text
  _efStatusCard = effect(() => {
    const status = pipelineStatus.value;
    const dot = el<HTMLSpanElement>("status-dot");
    const text = el<HTMLSpanElement>("status-text");

    if (!dot || !text) return;

    const state = normalizePipelineState(status?.state);

    dot.classList.toggle("running", state === PipelineState.RUNNING);
    dot.classList.toggle("error", state === PipelineState.ERROR);
    text.textContent = state === PipelineState.RUNNING ? "ACTIVO" : "APAGADO";

    // Start/stop buttons
    const btnStart = el<HTMLButtonElement>("btn-start");
    const btnStop = el<HTMLButtonElement>("btn-stop");

    if (btnStart) {
      const isRunningLocal = state === PipelineState.RUNNING;
      btnStart.disabled = isRunningLocal;
      btnStart.style.opacity = isRunningLocal ? "0.5" : "1";
    }
    if (btnStop) {
      const isRunningStop = state === PipelineState.RUNNING;
      btnStop.disabled = !isRunningStop;
      btnStop.style.opacity = isRunningStop ? "1" : "0.5";
    }
  });

  // Module status dots (error / running / degraded / idle)
  _efModuleStatusDots = effect(() => {
    const status = pipelineStatus.value;
    const modules = status?.modules ?? [];
    const moduleStatusIdMap: Record<string, string> = {
      srt_input: "status-input",
      rtmp_input: "status-input",
      file_input: "status-input",
      audio_extractor: "status-audio_extractor",
      transcriber: "status-transcriber",
      translator: "status-translator",
      tts_engine: "status-tts_engine",
      subtitle_generator: "status-subtitle_generator",
      audio_mixer: "status-audio_mixer",
      video_muxer: "status-video_muxer",
      output: "status-output",
    };
    for (const mod of modules) {
      const dotId = moduleStatusIdMap[mod.name];
      if (!dotId) continue;
      const dot = el<HTMLSpanElement>(dotId);
      if (!dot) continue;
      const modState = getModuleState(mod);
      dot.classList.toggle("running", modState === ModuleState.RUNNING);
      dot.classList.toggle("error", modState === ModuleState.ERROR);
      dot.classList.toggle("degraded", modState === ModuleState.DEGRADED);
      dot.classList.toggle("disabled", modState === ModuleState.DISABLED);
    }
  });

  // Module indicators (active state)
  _efModuleIndicators = effect(() => {
    const status = pipelineStatus.value;
    const modules = status?.modules ?? [];
    const running = isPipelineRunning.value;

    const indicatorMap: Record<string, string> = {
      srt_input: "indicator-input",
      rtmp_input: "indicator-input",
      file_input: "indicator-input",
      audio_extractor: "indicator-audio-extractor",
      transcriber: "indicator-whisper",
      translator: "indicator-translate",
      tts_engine: "indicator-tts",
      subtitle_generator: "indicator-subtitle",
      audio_mixer: "indicator-audio-mixer",
      video_muxer: "indicator-video-muxer",
      output: "indicator-video-muxer",
      webplayer_output: "indicator-output",
      srt_output: "indicator-output",
      rtmp_output: "indicator-output",
      file_output: "indicator-output",
    };

    for (const module of modules) {
      const indicatorId = indicatorMap[module.name];
      if (!indicatorId) continue;
      const indicator = el<HTMLSpanElement>(indicatorId);
      if (!indicator) continue;
      const isActive = running && module.enabled;
      indicator.classList.toggle(
        "active",
        isActive && module.state !== "degraded",
      );
      indicator.classList.toggle("degraded", module.state === "degraded");
    }

    // Also update indicator-output for the output module
    const outputIndicator = el<HTMLSpanElement>("indicator-output");
    const outputModule = modules.find((m) => m.name === "output");
    if (outputIndicator && outputModule) {
      outputIndicator.classList.toggle(
        "active",
        running && outputModule.enabled,
      );
    }
  });

  // Pipeline indicator (top-left dot in header)
  _efPipelineIndicator = effect(() => {
    const status = pipelineStatus.value;
    const dot = el<HTMLSpanElement>("pipeline-indicator");
    if (!dot) return;
    dot.classList.toggle("active", status?.state === "running");
  });
}

function stopStatusEffects(): void {
  _efStatusCard?.();
  _efModuleIndicators?.();
  _efModuleStatusDots?.();
  _efPipelineIndicator?.();
}

// ── effectMetrics ─────────────────────────────────────────────────────────────

let _efMetrics: (() => void) | null = null;

// Get color class for metric bars (.low, .medium, .high)
function getMetricBarClass(value: number): string {
  // Use 80% as threshold for all metrics (normal CPU usage is 20-50%)
  if (value < 40) return "low";
  if (value < 80) return "medium";
  return "high";
}

// Get color class for metric items (.warning, .critical)
function getMetricItemClass(value: number): string {
  if (value < 80) return "warning";
  return "critical";
}

// Track consecutive CPU high for alert
let _cpuHighStartTime: number | null = null;

function startMetricsEffects(): void {
  _efMetrics = effect(() => {
    const metrics = systemMetrics.value;
    const tpAvg = throughputAvg.value;
    const latency = pipelineLatency.value;

    // CPU
    const cpuItem = el<HTMLDivElement>("metric-cpu");
    const cpuBar = el<HTMLDivElement>("metric-cpu-bar");
    const cpuValue = el<HTMLSpanElement>("metric-cpu-value");
    if (cpuBar) {
      cpuBar.style.width = `${metrics.cpu}%`;
      cpuBar.classList.remove("low", "medium", "high");
      cpuBar.classList.add(getMetricBarClass(metrics.cpu));
    }
    if (cpuItem) {
      cpuItem.classList.remove("warning", "critical");
      cpuItem.classList.add(getMetricItemClass(metrics.cpu));
    }
    if (cpuValue) cpuValue.textContent = `${metrics.cpu.toFixed(0)}%`;

    // Memory
    const memBar = el<HTMLDivElement>("metric-memory-bar");
    const memValue = el<HTMLSpanElement>("metric-memory-value");
    const memPercent = el<HTMLSpanElement>("metric-memory-percent");
    if (memBar) {
      memBar.style.width = `${metrics.memoryPercent}%`;
      memBar.classList.remove("low", "medium", "high");
      memBar.classList.add(getMetricBarClass(metrics.memoryPercent));
    }
    if (memValue) memValue.textContent = `${metrics.memoryMb.toFixed(0)} MB`;
    if (memPercent)
      memPercent.textContent = `${metrics.memoryPercent.toFixed(0)}%`;

    // GPU
    const gpuBar = el<HTMLDivElement>("metric-gpu-bar");
    const gpuValue = el<HTMLSpanElement>("metric-gpu-value");
    const gpuMem = el<HTMLSpanElement>("metric-gpu-memory");
    if (gpuBar) {
      gpuBar.style.width = `${metrics.gpuUtil}%`;
      gpuBar.classList.remove("low", "medium", "high");
      gpuBar.classList.add(getMetricBarClass(metrics.gpuUtil));
    }
    if (gpuValue) gpuValue.textContent = `${metrics.gpuUtil.toFixed(0)}%`;
    if (gpuMem)
      gpuMem.textContent =
        metrics.gpuMemMb > 0 ? `${metrics.gpuMemMb.toFixed(0)} MB` : "N/A";

    // Throughput
    const tpBar = el<HTMLDivElement>("metric-throughput-bar");
    const tpValue = el<HTMLSpanElement>("metric-throughput-value");
    if (tpBar) tpBar.style.width = `${Math.min(tpAvg * 10, 100)}%`;
    if (tpValue) tpValue.textContent = `${tpAvg.toFixed(2)}/s`;

    // Latency indicator (F18)
    const latencyEl = el<HTMLSpanElement>("latency-value");
    if (latencyEl) {
      latencyEl.textContent = latency > 0 ? `${latency.toFixed(1)}s` : "0s";
    }

    // CPU Alert (F18): detect >90% for 5+ consecutive seconds
    const now = Date.now();
    if (metrics.cpu > 90) {
      if (_cpuHighStartTime === null) {
        _cpuHighStartTime = now;
      } else if (now - _cpuHighStartTime >= 5000) {
        cpuAlertActive.value = true;
      }
      if (cpuItem) cpuItem.classList.add("critical");
    } else {
      _cpuHighStartTime = null;
      cpuAlertActive.value = false;
    }

    // Chunks failed (F18)
    const chunksFailed = (pipelineStatus.value as any)?.chunks_failed ?? 0;
    const chunksFailedEl = el<HTMLDivElement>("chunks-failed");
    const chunksFailedText = el<HTMLSpanElement>("chunks-failed-text");
    if (chunksFailedEl && chunksFailedText) {
      if (chunksFailed > 0) {
        chunksFailedEl.style.display = "inline-flex";
        chunksFailedText.textContent = `${chunksFailed} failed`;
      } else {
        chunksFailedEl.style.display = "none";
      }
    }
  });
}

function stopMetricsEffects(): void {
  _efMetrics?.();
}

// ── Sparklines Effect (F18) ───────────────────────────────────────────────

let _efSparklines: (() => void) | null = null;

function startSparklinesEffects(): void {
  _efSparklines = effect(() => {
    const cpu = cpuHistory.value;
    const gpu = gpuHistory.value;
    const tp = throughputHistory.value;

    // Generate sparkline points (60 samples -> SVG coordinates)
    // ViewBox is 60x20, so x = index, y = 20 - (value * 0.2)
    const cpuLine = document.getElementById(
      "cpu-sparkline-line",
    ) as unknown as {
      setAttribute: (k: string, v: string) => void;
      style: { stroke: string };
    };
    const gpuLine = document.getElementById(
      "gpu-sparkline-line",
    ) as unknown as {
      setAttribute: (k: string, v: string) => void;
      style: { stroke: string };
    };
    const tpLine = document.getElementById("tp-sparkline-line") as unknown as {
      setAttribute: (k: string, v: string) => void;
      style: { stroke: string };
    };

    if (cpuLine && cpu.length > 1) {
      const points = cpu
        .map((v, i) => `${i},${20 - Math.min(v * 0.2, 20)}`)
        .join(" ");
      cpuLine.setAttribute("points", points);
      cpuLine.style.stroke = getSparklineColor(cpu[cpu.length - 1] || 0);
    }
    if (gpuLine && gpu.length > 1) {
      const points = gpu
        .map((v, i) => `${i},${20 - Math.min(v * 0.2, 20)}`)
        .join(" ");
      gpuLine.setAttribute("points", points);
      gpuLine.style.stroke = getSparklineColor(gpu[gpu.length - 1] || 0);
    }
    if (tpLine && tp.length > 1) {
      const maxTp = Math.max(...tp, 0.1);
      const points = tp
        .map((v, i) => `${i},${20 - Math.min((v / maxTp) * 20, 20)}`)
        .join(" ");
      tpLine.setAttribute("points", points);
    }
  });
}

function stopSparklinesEffects(): void {
  _efSparklines?.();
}

function getSparklineColor(value: number): string {
  if (value < 70) return "#22c55e";
  if (value < 85) return "#f59e0b";
  return "#ef4444";
}

// ── effectModuleMetrics ──────────────────────────────────────────────────────

let _efModuleMetrics: (() => void) | null = null;

function startModuleMetricsEffects(): void {
  _efModuleMetrics = effect(() => {
    const status = pipelineStatus.value;
    const modules = status?.modules ?? [];
    const running = isPipelineRunning.value;
    const tpAvg = throughputAvg.value;
    const moduleMap = Object.fromEntries(
      modules.map((m) => [m.name, m]),
    ) as Record<string, (typeof modules)[number]>;

    const moduleTimeIds = [
      "module-time-audio_extractor",
      "module-time-transcriber",
      "module-time-translator",
      "module-time-tts_engine",
      "module-time-subtitle_generator",
      "module-time-audio_mixer",
      "module-time-video_muxer",
    ];
    const moduleChunksIds = [
      "module-chunks-audio_extractor",
      "module-chunks-transcriber",
      "module-chunks-translator",
      "module-chunks-tts_engine",
      "module-chunks-subtitle_generator",
      "module-chunks-audio_mixer",
      "module-chunks-video_muxer",
    ];
    const moduleEncoderIds = [
      "module-encoder-transcriber",
      "module-encoder-translator",
      "module-encoder-tts_engine",
      "module-encoder-subtitle_generator",
      "module-encoder-audio_mixer",
      "module-encoder-video_muxer",
    ];

    // Per-module time + chunks + memory + encoder + GPU badge
    for (const name of [
      "audio_extractor",
      "transcriber",
      "translator",
      "tts_engine",
      "subtitle_generator",
      "audio_mixer",
    ]) {
      const mod = moduleMap[name];
      const timeEl = el<HTMLSpanElement>(`module-time-${name}`);
      const chunksEl = el<HTMLSpanElement>(`module-chunks-${name}`);
      const memoryEl = el<HTMLSpanElement>(`module-memory-${name}`);
      const encoderEl = el<HTMLSpanElement>(`module-encoder-${name}`);

      if (timeEl) {
        if (
          mod?.last_process_time_ms !== undefined &&
          mod.last_process_time_ms > 0
        ) {
          const ms = mod.last_process_time_ms;
          timeEl.textContent =
            ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
        } else if (running && tpAvg > 0) {
          const avgMs = (1000 / tpAvg).toFixed(0);
          timeEl.textContent = `${avgMs}ms`;
        } else {
          timeEl.textContent = "--";
        }
      }

      if (chunksEl) {
        chunksEl.textContent = String(mod?.processed_chunks ?? 0);
      }

      if (memoryEl) {
        memoryEl.textContent =
          mod?.memory_mb !== undefined
            ? `${Math.round(mod.memory_mb)} MB`
            : "--";
      }

      if (encoderEl && mod?.extra) {
        const label =
          mod.extra.encoder_label || (mod.extra.using_gpu ? "GPU" : "CPU");
        encoderEl.textContent = label;
      }

      // GPU badge
      const badge = el<HTMLSpanElement>(`gpu-badge-${name}`);
      if (badge && mod?.extra) {
        const isActive =
          running && mod.enabled && (mod.processed_chunks ?? 0) > 0;
        if (mod.extra.using_gpu) {
          badge.style.display = "inline";
          badge.classList.toggle("active", isActive);
        } else {
          badge.style.display = "none";
        }
      }
    }

    // Audio extractor device metric
    const audioExtractorModule = moduleMap["audio_extractor"];
    const audioExtractorDeviceEl = el<HTMLSpanElement>(
      "module-device-audio_extractor",
    );
    const audioExtractorGpuBadge = el<HTMLSpanElement>(
      "gpu-badge-audio_extractor",
    );
    if (audioExtractorDeviceEl && audioExtractorModule?.extra) {
      audioExtractorDeviceEl.textContent =
        audioExtractorModule.extra.device ||
        (audioExtractorModule.extra.using_gpu ? "GPU" : "CPU") ||
        "--";
    }
    if (audioExtractorGpuBadge && audioExtractorModule?.extra) {
      const isActive =
        running &&
        audioExtractorModule.enabled &&
        (audioExtractorModule.processed_chunks ?? 0) > 0;
      if (audioExtractorModule.extra.using_gpu) {
        audioExtractorGpuBadge.style.display = "inline";
        audioExtractorGpuBadge.classList.toggle("active", isActive);
      } else {
        audioExtractorGpuBadge.style.display = "none";
      }
    }

    // Input module metrics (input is the SRT/RTMP source)
    const inputModule =
      moduleMap["input"] ??
      moduleMap["srt_input"] ??
      moduleMap["rtmp_input"] ??
      moduleMap["file_input"];
    const inputTimeEl = el<HTMLSpanElement>("module-time-input");
    const inputChunksEl = el<HTMLSpanElement>("module-chunks-input");
    const inputGpuBadge = el<HTMLSpanElement>("gpu-badge-input");
    const inputEncoderEl = el<HTMLSpanElement>("module-encoder-input");

    if (inputTimeEl) {
      if (
        inputModule?.last_process_time_ms !== undefined &&
        inputModule.last_process_time_ms > 0
      ) {
        const ms = inputModule.last_process_time_ms;
        inputTimeEl.textContent =
          ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
      } else if (running && tpAvg > 0) {
        inputTimeEl.textContent = `${(1000 / tpAvg).toFixed(0)}ms`;
      } else if (!inputModule?.enabled) {
        inputTimeEl.textContent = "--";
      } else if (inputModule?.state === "error") {
        inputTimeEl.textContent = "ERROR";
        inputTimeEl.style.color = "var(--error)";
      } else {
        inputTimeEl.textContent = "IDLE";
      }
    }

    if (inputChunksEl && inputModule) {
      inputChunksEl.textContent = String(inputModule.processed_chunks ?? 0);
    }

    if (inputGpuBadge && inputModule) {
      const isGpuActive = inputModule.extra?.using_gpu === true;
      const isActiveProcessing =
        running && (inputModule.processed_chunks ?? 0) > 0;
      if (inputModule.enabled && isGpuActive) {
        inputGpuBadge.style.display = "inline";
        inputGpuBadge.classList.toggle("active", isActiveProcessing);
        inputGpuBadge.textContent = "GPU";
      } else {
        inputGpuBadge.style.display = "none";
      }
    }

    if (inputEncoderEl && inputModule) {
      const label =
        inputModule.extra?.encoder_label ||
        (inputModule.extra?.using_gpu ? "GPU" : "CPU");
      inputEncoderEl.textContent = label;
    }

    // Video muxer module metrics (for HlsCard / VIDEO MUXER)
    const muxerModule = moduleMap["video_muxer"];
    const muxerTimeEl = el<HTMLSpanElement>("module-time-video_muxer");
    const muxerMemoryEl = el<HTMLSpanElement>("module-memory-video_muxer");
    const muxerChunksEl = el<HTMLSpanElement>("module-chunks-video_muxer");
    const muxerEncoderEl = el<HTMLSpanElement>("module-encoder-video_muxer");
    const muxerGpuBadge = el<HTMLSpanElement>("gpu-badge-video_muxer");

    if (muxerTimeEl) {
      if (
        muxerModule?.last_process_time_ms !== undefined &&
        muxerModule.last_process_time_ms > 0
      ) {
        const ms = muxerModule.last_process_time_ms;
        muxerTimeEl.textContent =
          ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
      } else if (running && tpAvg > 0) {
        muxerTimeEl.textContent = `${(1000 / tpAvg).toFixed(0)}ms`;
      } else {
        muxerTimeEl.textContent = "--";
      }
    }
    if (muxerMemoryEl && muxerModule) {
      muxerMemoryEl.textContent =
        muxerModule.memory_mb !== undefined
          ? `${Math.round(muxerModule.memory_mb)} MB`
          : "--";
    }
    if (muxerChunksEl && muxerModule) {
      muxerChunksEl.textContent = String(muxerModule.processed_chunks ?? 0);
    }
    if (muxerEncoderEl && muxerModule?.extra) {
      const label =
        muxerModule.extra.encoder_label ||
        (muxerModule.extra.using_gpu ? "GPU" : "CPU");
      muxerEncoderEl.textContent = label;
    }
    if (muxerGpuBadge) {
      const isActive =
        running &&
        muxerModule?.enabled &&
        (muxerModule.processed_chunks ?? 0) > 0;
      const usingGpu = muxerModule?.extra?.using_gpu ?? false;
      if (usingGpu) {
        muxerGpuBadge.textContent = "GPU";
        muxerGpuBadge.style.display = "inline";
        muxerGpuBadge.classList.toggle("active", isActive);
      } else {
        muxerGpuBadge.textContent = "CPU";
        muxerGpuBadge.style.display = "inline";
        muxerGpuBadge.classList.remove("active");
      }
    }

    // Output module metrics (for OUTPUT card)
    const outputModule = moduleMap["output"];
    const outputTimeEl = el<HTMLSpanElement>("module-time-output");
    const outputMemoryEl = el<HTMLSpanElement>("module-memory-output");
    const outputChunksEl = el<HTMLSpanElement>("module-chunks-output");
    const outputEncoderEl = el<HTMLSpanElement>("module-encoder-output");
    const outputGpuBadge = el<HTMLSpanElement>("gpu-badge-output");

    if (outputTimeEl) {
      if (
        outputModule?.last_process_time_ms !== undefined &&
        outputModule.last_process_time_ms > 0
      ) {
        const ms = outputModule.last_process_time_ms;
        outputTimeEl.textContent =
          ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
      } else if (running && tpAvg > 0) {
        outputTimeEl.textContent = `${(1000 / tpAvg).toFixed(0)}ms`;
      } else {
        outputTimeEl.textContent = "--";
      }
    }
    if (outputMemoryEl && outputModule) {
      outputMemoryEl.textContent =
        outputModule.memory_mb !== undefined
          ? `${Math.round(outputModule.memory_mb)} MB`
          : "--";
    }
    if (outputChunksEl && outputModule) {
      outputChunksEl.textContent = String(outputModule.processed_chunks ?? 0);
    }
    if (outputEncoderEl && outputModule?.extra) {
      const label =
        outputModule.extra.encoder_label ||
        (outputModule.extra.using_gpu ? "GPU" : "CPU");
      outputEncoderEl.textContent = label;
    }
    if (outputGpuBadge) {
      const isActive =
        running &&
        outputModule?.enabled &&
        (outputModule.processed_chunks ?? 0) > 0;
      const usingGpu = outputModule?.extra?.using_gpu ?? false;
      if (usingGpu) {
        outputGpuBadge.textContent = "GPU";
        outputGpuBadge.style.display = "inline";
        outputGpuBadge.classList.toggle("active", isActive);
      } else {
        outputGpuBadge.textContent = "CPU";
        outputGpuBadge.style.display = "inline";
        outputGpuBadge.classList.remove("active");
      }
    }
  });
}

function stopModuleMetricsEffects(): void {
  _efModuleMetrics?.();
}

// ── effectConnectionUrls ──────────────────────────────────────────────────────

let _efConnectionUrls: (() => void) | null = null;

function startConnectionUrlEffects(): void {
  _efConnectionUrls = effect(() => {
    const urls = connectionUrls.value;

    const emissionLabel = el<HTMLSpanElement>("url-emision-label");
    const emissionValue = el<HTMLSpanElement>("url-emision");
    const streamValue = el<HTMLSpanElement>("url-stream");
    const playerLink = el<HTMLAnchorElement>("url-player");

    if (emissionLabel) emissionLabel.textContent = urls.primaryLabel;
    if (emissionValue) emissionValue.textContent = urls.primaryUrl;
    if (streamValue) streamValue.textContent = urls.streamUrl;
    if (playerLink) {
      playerLink.textContent = urls.playerUrl;
      playerLink.href = urls.playerUrl;
    }
  });
}

function stopConnectionUrlEffects(): void {
  _efConnectionUrls?.();
}

// ── effectWsStatus ────────────────────────────────────────────────────────────

let _efWsStatus: (() => void) | null = null;

function startWsStatusEffect(): void {
  _efWsStatus = effect(() => {
    const connected = wsConnected.value;
    const wsBadge = el<HTMLSpanElement>("ws-status-badge");
    if (wsBadge) {
      wsBadge.textContent = connected ? "WS ON" : "WS OFF";
      wsBadge.classList.toggle("active", connected);
    }
  });
}

function stopWsStatusEffect(): void {
  _efWsStatus?.();
}

// ── effectClock ───────────────────────────────────────────────────────────────

let _efClock: (() => void) | null = null;

function startClockEffect(): void {
  _efClock = effect(() => {
    // Signal dependency to re-run on pipeline changes (clock doesn't depend on it,
    // but the effect is tracked to ensure proper lifecycle)
    void pipelineStatus.value;
    const clock = el<HTMLSpanElement>("live-clock");
    if (clock) {
      clock.textContent = new Date().toLocaleTimeString("en-US", {
        hour12: false,
      });
    }
  });
  startClockUpdates();
}

function stopClockEffect(): void {
  _efClock?.();
}

// ── effectRemoteMode ──────────────────────────────────────────────────────────

let _efRemoteMode: (() => void) | null = null;

function startRemoteModeEffect(): void {
  _efRemoteMode = effect(() => {
    const mode = connectionMode.value;
    const remoteConfig = el<HTMLDivElement>("remote-config");
    const btnLocal = el<HTMLButtonElement>("btn-mode-local");
    const btnRemote = el<HTMLButtonElement>("btn-mode-remote");

    if (remoteConfig) {
      remoteConfig.style.display = mode === "remote" ? "" : "none";
    }
    if (btnLocal) btnLocal.classList.toggle("active", mode === "local");
    if (btnRemote) btnRemote.classList.toggle("active", mode === "remote");

  });
}

function stopRemoteModeEffect(): void {
  _efRemoteMode?.();
}

// ── effectThroughputHistory ───────────────────────────────────────────────────

let _efThroughputHistory: (() => void) | null = null;

function startThroughputEffect(): void {
  _efThroughputHistory = effect(() => {
    // Read throughputHistory to subscribe
    const hist = throughputHistory.value;
    // Also read config for segment/list_size
    void pipelineConfig.value;
    // Re-renders throughput display in module metrics
  });
}

function stopThroughputEffect(): void {
  _efThroughputHistory?.();
}

// ── Sync Effects (F30) ────────────────────────────────────────────────────────

let _efSync: (() => void) | null = null;

function startSyncEffects(): void {
  _efSync = effect(() => {
    // Subscribe to websocket messages for sync status
    // In a real implementation, this would handle incoming WS messages
    // For now, we'll simulate by reading from pipelineStatus
    const status = pipelineStatus.value;
    if (status && status.sync) {
      syncDriftMs.value = status.sync.drift_ms ?? 0;
      syncState.value = status.sync.state ?? "in_sync";
      syncCorrectionActive.value = status.sync.correction_active ?? false;
    }
  });
}

function stopSyncEffects(): void {
  _efSync?.();
}

// ── Pipeline Logs Effect ───────────────────────────────────────────────────────

let _efPipelineLogs: (() => void) | null = null;
let _lastLogCount = 0;

function startLogsEffect(): void {
  _efPipelineLogs = effect(() => {
    const logs = pipelineLogs.value;
    // Only process new logs since last render
    const newLogs = logs.slice(_lastLogCount);
    for (const log of newLogs) {
      addLogToPanel(log.level, log.message, log.timestamp);
    }
    _lastLogCount = logs.length;
  });
}

function stopLogsEffect(): void {
  _efPipelineLogs?.();
  _lastLogCount = 0;
}

// ── Public API ────────────────────────────────────────────────────────────────

export function startEffects(): void {
  startStatusEffects();
  startMetricsEffects();
  startSparklinesEffects();
  startModuleMetricsEffects();
  startConnectionUrlEffects();
  startWsStatusEffect();
  startClockEffect();
  startRemoteModeEffect();
  startThroughputEffect();
  startLogsEffect();
  startSyncEffects();
}

export function stopEffects(): void {
  stopStatusEffects();
  stopMetricsEffects();
  stopSparklinesEffects();
  stopModuleMetricsEffects();
  stopConnectionUrlEffects();
  stopWsStatusEffect();
  stopClockEffect();
  stopRemoteModeEffect();
  stopThroughputEffect();
  stopLogsEffect();
}
