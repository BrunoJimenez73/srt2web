/**
 * Signals - Reactive state atoms and computed derivatives.
 *
 * These are the source of truth for all dashboard state.
 * DOM updates happen via effects in effects.ts that subscribe to these signals.
 */

import { signal, computed } from '@preact/signals-core';
import type { Config, Status, LogMessage, ModuleName, PipelineState, ModuleState, ConnectionMode } from '../api';

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
export const connectionMode = signal<ConnectionMode>('local');

/** Whether a pipeline operation is in flight (start/stop) */
export const isOperationPending = signal<boolean>(false);

/** Throughput history for rolling average (video muxer metrics) */
export const throughputHistory = signal<number[]>([]);

/** Input type signal (srt/rtmp/file) - reactive */
export const inputType = signal<'srt' | 'rtmp' | 'file'>('srt');

// ── Computed: Pipeline ────────────────────────────────────────────────────────

export const pipelineState = computed<PipelineState>(() => {
  const s = pipelineStatus.value;
  return s?.state as PipelineState ?? 'stopped';
});

export const isPipelineRunning = computed(() => pipelineStatus.value?.state === 'running');

export const isPipelineStopping = computed(() => pipelineStatus.value?.state === 'stopping');

export const chunksProcessed = computed(() => pipelineStatus.value?.chunks_processed ?? 0);

// ── Computed: Modules ─────────────────────────────────────────────────────────

/** Map of module name → module status */
export const moduleStates = computed(() => {
  const modules = pipelineStatus.value?.modules;
  if (!modules) return {} as Record<string, Status['modules'][number]>;
  return Object.fromEntries(modules.map(m => [m.name, m])) as Record<string, Status['modules'][number]>;
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
  const sys = (s as any)?.system_metrics ?? (s as any)?.system ?? {};
  const uptime = (s as any)?.uptime_seconds ?? 0;
  const chunks = s?.chunks_processed ?? 0;
  const cps = uptime > 0 ? chunks / uptime : 0;
  return {
    cpu: sys.cpu_percent ?? sys.cpu_usage ?? 0,
    memoryMb: sys.memory_mb ?? 0,
    memoryPercent: sys.memory_percent ?? sys.memory_usage ?? 0,
    gpuUtil: sys.gpu_percent ?? sys.gpu_usage ?? 0,
    gpuMemMb: sys.gpu_memory_mb ?? 0,
    gpuMemPercent: sys.gpu_memory_usage ?? 0,
    chunksPerSec: cps,
    totalChunks: chunks,
  };
});

// ── Computed: Connection URLs ────────────────────────────────────────────────

export const connectionUrls = computed(() => {
  const cfg = pipelineConfig.value;
  const host = connectionMode.value === 'remote'
    ? (document.getElementById('emitter-address') as HTMLInputElement)?.value || 'localhost'
    : '127.0.0.1';

  const inputTypeValue = pipelineConfig.value?.input?.type ?? 'srt';
  // Update reactive signal
  inputType.value = inputTypeValue as 'srt' | 'rtmp' | 'file';
  
  const srtPort = cfg?.input?.srt?.port ?? 9000;
  const rtmpPort = cfg?.input?.rtmp?.port ?? 1935;
  const serverPort = cfg?.server?.port ?? 9999;

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
    srtLabel: inputTypeValue === 'rtmp' ? 'RTMP:' : 'SRT:',
    primaryUrl: inputTypeValue === 'rtmp' ? rtmpUrl : srtUrl,
    primaryLabel: inputTypeValue === 'rtmp' ? 'RTMP:' : 'SRT:',
  };
});

// ── Computed: Throughput ─────────────────────────────────────────────────────

export const throughputAvg = computed(() => {
  const hist = throughputHistory.value;
  if (hist.length === 0) return 0;
  return hist.reduce((a, b) => a + b, 0) / hist.length;
});

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Update pipeline status and record throughput snapshot */
export function updateStatus(status: Status): void {
  pipelineStatus.value = status;

  // Calculate chunks_per_second from actual backend fields
  const uptime = (status as any)?.uptime_seconds ?? 0;
  const chunks = status?.chunks_processed ?? 0;
  const avgTimeMs = (status as any)?.avg_processing_time_ms ?? 0;

  // Use avg_processing_time_ms for instant throughput estimate
  const tp = avgTimeMs > 0 ? 1000 / avgTimeMs : (uptime > 0 ? chunks / uptime : 0);
  if (tp > 0) {
    const hist = [...throughputHistory.value, tp];
    // Keep last 10 samples
    throughputHistory.value = hist.slice(-10);
  }
}

/** Append a log message */
export function addLog(level: 'INFO' | 'WARNING' | 'ERROR', message: string): void {
  const entry: LogMessage = {
    timestamp: new Date().toISOString(),
    level,
    message,
  };
  // Keep last 500 logs
  pipelineLogs.value = [...pipelineLogs.value.slice(-499), entry];
}

/** Reset throughput history (called on pipeline stop) */
export function resetThroughput(): void {
  throughputHistory.value = [];
}
