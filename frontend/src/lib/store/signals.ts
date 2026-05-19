/**
 * Signals - Reactive state atoms and computed derivatives.
 *
 * These are the source of truth for all dashboard state.
 * DOM updates happen via effects in effects.ts that subscribe to these signals.
 */

import { signal, computed } from "@preact/signals-core";
import type {
  Config,
  Status,
  LogMessage,
  ModuleName,
  PipelineState,
  ModuleState,
  ConnectionMode,
  MetricsData,
} from "../api";

// ── Source Signals ────────────────────────────────────────────────────────────

/** Pipeline status from backend (modules, state, chunks, etc.) */
export const pipelineStatus = signal<Status | null>(null);

/** Full config from backend */
export const pipelineConfig = signal<Config | null>(null);

/** Log messages received from WebSocket */
export const pipelineLogs = signal<LogMessage[]>([]);

/** WebSocket connection state */
export const wsConnected = signal<boolean>(false);

/** HTTP poll connection state */
export const pollConnected = signal<boolean>(false);

/** Dashboard mode: local or remote */
export const connectionMode = signal<ConnectionMode>("local");

/** Whether a pipeline operation is in flight (start/stop) */
export const isOperationPending = signal<boolean>(false);

/** Throughput history for rolling average (video muxer metrics) */
export const throughputHistory = signal<number[]>([]);

/** Input type signal (srt/rtmp/file) - reactive */
export const inputType = signal<"srt" | "rtmp" | "file">("srt");

/** Emitter address for remote mode */
export const emitterAddress = signal<string>("");

/** Subtitle sync signals (F30) */
export const syncDriftMs = signal<number>(0);
export const syncState = signal<"in_sync" | "drifting" | "correcting">(
  "in_sync",
);
export const syncCorrectionActive = signal<boolean>(false);

// ── Computed: Pipeline ────────────────────────────────────────────────────────

export const pipelineState = computed<PipelineState>(() => {
  const s = pipelineStatus.value;
  return (s?.state as PipelineState) ?? "stopped";
});

export const isPipelineRunning = computed(
  () => pipelineStatus.value?.state === "running",
);

export const isPipelineStopping = computed(
  () => pipelineStatus.value?.state === "stopping",
);

export const chunksProcessed = computed(
  () => pipelineStatus.value?.chunks_processed ?? 0,
);

// ── Computed: Modules ─────────────────────────────────────────────────────────

/** Map of module name → module status */
export const moduleStates = computed(() => {
  const modules = pipelineStatus.value?.modules;
  if (!modules) return {} as Record<string, Status["modules"][number]>;
  return Object.fromEntries(modules.map((m) => [m.name, m])) as Record<
    string,
    Status["modules"][number]
  >;
});

/** List of enabled module names */
export const enabledModules = computed(() => {
  const states = moduleStates.value;
  return Object.entries(states)
    .filter(([, m]) => m.enabled)
    .map(([name]) => name);
});

// ── Computed: Metrics ────────────────────────────────────────────────────────

export const systemMetrics = computed(() => {
  const s = pipelineStatus.value;
  const sys: Partial<MetricsData> = s?.system_metrics ?? s?.system ?? {};
  const uptime = s?.uptime_seconds ?? 0;
  const chunks = s?.chunks_processed ?? 0;
  const cps = uptime > 0 ? chunks / uptime : 0;
  return {
    cpu: sys.cpu_percent ?? sys.cpu_usage ?? 0,
    memoryMb: sys.memory_mb ?? 0,
    memoryPercent: sys.memory_percent ?? sys.memory_usage ?? 0,
    gpuUtil: sys.gpu_percent ?? sys.gpu_usage ?? sys.gpu_util ?? 0,
    gpuMemMb: sys.gpu_memory_mb ?? sys.gpu_memory ?? 0,
    gpuMemPercent: sys.gpu_memory_percent ?? sys.gpu_memory_usage ?? 0,
    chunksPerSec: cps,
    totalChunks: chunks,
  };
});

// ── Computed: Connection URLs ────────────────────────────────────────────────

export const connectionUrls = computed(() => {
  const cfg = pipelineConfig.value;
  const status = pipelineStatus.value;
  const publicIp = status?.network?.public_ip;
  const remAddr = emitterAddress.value || publicIp || "";
  const host =
    connectionMode.value === "remote" ? remAddr || "localhost" : "127.0.0.1";

  const inputTypeValue = pipelineConfig.value?.input?.type ?? "srt";
  // Update reactive signal
  inputType.value = inputTypeValue;

  const srtPort = cfg?.input?.srt?.port ?? 9000;
  const srtMode = cfg?.input?.srt?.mode ?? "listener";
  const srtLatency = cfg?.input?.srt?.latency_ms ?? 200;
  const rtmpPort = cfg?.input?.rtmp?.port ?? 1935;
  const serverPort = cfg?.server?.port ?? 9999;

  // The URL is for the CLIENT to connect to us.
  // If we listen, client must be caller. If we call, client must be listener.
  const clientMode = srtMode === "listener" ? "caller" : "listener";
  const srtUrl = `srt://${host}:${srtPort}`;
  const rtmpUrl = `rtmp://${host}:${rtmpPort}`;
  const streamUrl = `http://${host}:${serverPort}/hls/stream.m3u8`;
  const playerUrl = `http://${host}:${serverPort}/player`;

  return {
    host,
    inputType: inputTypeValue,
    srtUrl,
    rtmpUrl,
    streamUrl,
    playerUrl,
    srtLabel: inputTypeValue === "rtmp" ? "RTMP:" : "SRT:",
    primaryUrl: inputTypeValue === "rtmp" ? rtmpUrl : srtUrl,
    primaryLabel: inputTypeValue === "rtmp" ? "RTMP:" : "SRT:",
  };
});

// ── Computed: Throughput ─────────────────────────────────────────────────────

export const throughputAvg = computed(() => {
  const hist = throughputHistory.value;
  if (hist.length === 0) return 0;
  return hist.reduce((a, b) => a + b, 0) / hist.length;
});

// ── Computed: Per-module latency breakdown ───────────────────────────────────

export const moduleLatencyBreakdown = computed(() => {
  const status = pipelineStatus.value;
  const moduleAvgs = status?.module_avg_time_ms;
  if (!moduleAvgs || Object.keys(moduleAvgs).length === 0) return [];
  return Object.entries(moduleAvgs)
    .map(([name, avgMs]) => ({ name, avgMs }))
    .sort((a, b) => b.avgMs - a.avgMs);
});

// ── Computed: Latency ────────────────────────────────────────────────────────

export const pipelineLatency = computed(() => {
  const breakdown = moduleLatencyBreakdown.value;
  // Use actual per-module timing when available (F84)
  if (breakdown.length > 0) {
    return breakdown.reduce((sum, m) => sum + m.avgMs, 0) / 1000;
  }
  // Fallback estimate: avg_processing_time_ms * 6 stages
  const avgTimeMs = pipelineStatus.value?.avg_processing_time_ms ?? 0;
  return avgTimeMs > 0 ? (avgTimeMs * 6) / 1000 : 0;
});

// ── Computed: Metrics History for Sparklines ────────────────────────────────

export const cpuHistory = signal<number[]>([]);
export const gpuHistory = signal<number[]>([]);

export const cpuAlertActive = signal<boolean>(false);

// ── i18n (F34) ────────────────────────────────────────────────────

/** Current UI language */
export const currentLanguage = signal<"en" | "es">("en");

/** Current UI theme */
export const currentTheme = signal<"dark" | "light">("dark");

// ── Presets (F19) ─────────────────────────────────────────────────

/** List of available presets (built-in + saved) */
export const presets = signal<
  Array<{
    name: string;
    description: string;
    built_in?: boolean;
    config_keys?: string[];
  }>
>([]);

/** Currently selected preset name */
export const selectedPreset = signal<string>("");

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Update pipeline status and record throughput snapshot */
export function updateStatus(status: Status): void {
  pipelineStatus.value = status;

  // Calculate chunks_per_second from actual backend fields
  const uptime = status?.uptime_seconds ?? 0;
  const chunks = status?.chunks_processed ?? 0;
  const avgTimeMs = status?.avg_processing_time_ms ?? 0;

  // Use avg_processing_time_ms for instant throughput estimate
  const tp =
    avgTimeMs > 0 ? 1000 / avgTimeMs : uptime > 0 ? chunks / uptime : 0;
  if (tp > 0) {
    const hist = [...throughputHistory.value, tp];
    // Keep last 60 samples (increased for F18 sparklines)
    throughputHistory.value = hist.slice(-60);
  }

  // Update CPU/GPU history for sparklines (F18)
  const sys: Partial<MetricsData> =
    status.system_metrics ?? status.system ?? {};
  const cpu = sys.cpu_percent ?? sys.cpu_usage ?? 0;
  const gpu = sys.gpu_percent ?? sys.gpu_usage ?? sys.gpu_util ?? 0;

  if (cpu > 0) {
    cpuHistory.value = [...cpuHistory.value, cpu].slice(-60);
  }
  if (gpu > 0) {
    gpuHistory.value = [...gpuHistory.value, gpu].slice(-60);
  }
}

/** Append a log message */
export function addLog(
  level: "INFO" | "WARNING" | "ERROR",
  message: string,
): void {
  const entry: LogMessage = {
    timestamp: new Date().toISOString(),
    level,
    message,
  };
  // Keep last 1000 logs (increased from 500 for F16)
  pipelineLogs.value = [...pipelineLogs.value.slice(-999), entry];
}

/** Reset throughput history (called on pipeline stop) */
export function resetThroughput(): void {
  throughputHistory.value = [];
}
