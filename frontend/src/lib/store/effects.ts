/**
 * Effects - Signal-driven DOM updates.
 *
 * Centralizes all signal-driven DOM updates so they can be tested
 * independently of Astro component client scripts.
 */

import { effect } from "@preact/signals-core";
import {
  pipelineStatus,
  wsConnected,
  connectionMode,
  pipelineLogs,
  syncDriftMs,
  syncState,
  syncCorrectionActive,
  throughputHistory,
  pipelineConfig,
  inputType,
} from "./signals";
// Log panel integration (LogPanel.astro provides the DOM; logpanel.ts provides addLog)
import { addLog } from "../modules/logpanel";
import { t } from "../i18n";

// ── Element refs (lazy) ────────────────────────────────────────────────────────

function el<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

// ── Effect: Status Card (text, dot, buttons) ────────────────────────────────

function startStatusEffect(): (() => void) | void {
  return effect(() => {
    const status = pipelineStatus.value;
    const dot = el<HTMLSpanElement>("status-dot");
    const text = el<HTMLSpanElement>("status-text");
    const btnStart = el<HTMLButtonElement>("btn-start");
    const btnStop = el<HTMLButtonElement>("btn-stop");

    if (!dot || !text) return;

    const running = status?.state === "running";
    const stopping = status?.state === "stopping";
    const error = status?.state === "error";

    dot.className = "status-dot";
    dot.classList.toggle("running", running);
    dot.classList.toggle("error", error);
    dot.classList.toggle("stopped", !running && !error && !stopping);

    text.textContent = running
      ? t("status_active")
      : error
        ? t("status_error")
        : stopping
          ? t("status_stopping")
          : t("status_off");

    if (btnStart) {
      btnStart.disabled = running;
      btnStart.style.opacity = running ? "0.5" : "1";
    }
    if (btnStop) {
      btnStop.disabled = !running;
      btnStop.style.opacity = running ? "1" : "0.5";
    }
  });
}

// ── Effect: System Metrics ──────────────────────────────────────────────────
// F162: Module indicators, metrics, and GPU badges are handled by
// ProcessGrid.astro which has a more comprehensive version (degraded state,
// MPS, passthrough, encoder labels). Only system-level metrics remain here.

function startMetricsEffect(): (() => void) | void {
  return effect(() => {
    const status = pipelineStatus.value;
    const system = status?.system || status?.system_metrics || {};

    // CPU
    const cpuItem = el<HTMLElement>("metric-cpu");
    const cpuValue = el<HTMLElement>("metric-cpu-value");
    const cpuBar = el<HTMLElement>("metric-cpu-bar");
    const cpuPercent = system.cpu_percent ?? system.cpu_usage ?? 0;
    if (cpuValue) cpuValue.textContent = `${cpuPercent}%`;
    if (cpuBar) cpuBar.style.width = `${cpuPercent}%`;
    if (cpuItem) {
      cpuItem.classList.toggle("warning", cpuPercent > 70 && cpuPercent <= 90);
      cpuItem.classList.toggle("critical", cpuPercent > 90);
    }

    // Memory
    const memValue = el<HTMLElement>("metric-memory-value");
    const memPercentEl = el<HTMLElement>("metric-memory-percent");
    const memBar = el<HTMLElement>("metric-memory-bar");
    const memMb = system.memory_mb ?? 0;
    const memPercent = system.memory_percent ?? system.memory_usage ?? 0;
    if (memValue) memValue.textContent = `${memMb.toFixed(0)} MB`;
    if (memPercentEl) memPercentEl.textContent = `${memPercent}%`;
    if (memBar) memBar.style.width = `${memPercent}%`;

    // GPU
    const gpuValue = el<HTMLElement>("metric-gpu-value");
    const gpuBar = el<HTMLElement>("metric-gpu-bar");
    const gpuPercent = system.gpu_usage ?? 0;
    if (gpuValue) gpuValue.textContent = `${gpuPercent}%`;
    if (gpuBar) gpuBar.style.width = `${gpuPercent}%`;
  });
}

// ── Effect: Throughput Metric ───────────────────────────────────────────────

function startThroughputEffect(): (() => void) | void {
  return effect(() => {
    const history = throughputHistory.value;
    const tpValue = el<HTMLElement>("metric-throughput-value");

    if (tpValue && history.length > 0) {
      const avg = history.reduce((a, b) => a + b, 0) / history.length;
      tpValue.textContent = `${avg.toFixed(2)}/s`;
    } else if (tpValue) {
      tpValue.textContent = "0.00/s";
    }
  });
}

// ── Effect: WS Status Badge ─────────────────────────────────────────────────

function startWsBadgeEffect(): (() => void) | void {
  return effect(() => {
    const badge = el<HTMLSpanElement>("ws-status-badge");
    if (!badge) return;

    if (wsConnected.value) {
      badge.textContent = t("ws_on");
      badge.classList.add("active");
    } else {
      badge.textContent = t("ws_off");
      badge.classList.remove("active");
    }
  });
}

// ── Effect: Remote Mode Toggle ─────────────────────────────────────────────

function startRemoteModeEffect(): (() => void) | void {
  return effect(() => {
    const mode = connectionMode.value;
    const remoteConfig = el<HTMLDivElement>("remote-config");
    const btnLocal = el<HTMLButtonElement>("btn-mode-local");
    const btnRemote = el<HTMLButtonElement>("btn-mode-remote");

    if (remoteConfig)
      remoteConfig.style.display = mode === "remote" ? "" : "none";
    if (btnLocal) btnLocal.classList.toggle("active", mode === "local");
    if (btnRemote) btnRemote.classList.toggle("active", mode === "remote");
  });
}

// ── Effect: Clock ──────────────────────────────────────────────────────────

let _clockInterval: ReturnType<typeof setInterval> | null = null;

function startClockEffect(): void {
  const update = () => {
    const clock = el<HTMLSpanElement>("live-clock");
    if (clock) {
      clock.textContent = new Date().toLocaleTimeString("en-US", {
        hour12: false,
      });
    }
  };
  update();
  _clockInterval = setInterval(update, 1000);
  effect(() => {
    void pipelineStatus.value;
  });
}

// ── Effect: Sync signals from pipelineStatus (F30) ────────────────────────

function startSyncEffect(): (() => void) | void {
  return effect(() => {
    const s = pipelineStatus.value?.sync;
    if (s) {
      syncDriftMs.value = s.drift_ms ?? 0;
      syncState.value = s.state ?? "in_sync";
      syncCorrectionActive.value = s.correction_active ?? false;
    }
  });
}

// ── Effect: Forward pipeline logs to DOM log panel ────────────────────────

let _lastLogCount = 0;

function startLogsEffect(): (() => void) | void {
  return effect(() => {
    const logs = pipelineLogs.value;
    const newLogs = logs.slice(_lastLogCount);
    for (const log of newLogs) {
      addLog(log.level, log.message, log.timestamp);
    }
    _lastLogCount = logs.length;
  });
}

// ── Effect: Sync inputType from pipelineConfig ──────────────────────────

function startInputTypeEffect(): (() => void) | void {
  return effect(() => {
    const t = pipelineConfig.value?.input?.type;
    if (t === "srt" || t === "rtmp" || t === "file") {
      inputType.value = t;
    }
  });
}

// ── Effect: Pipeline status dot in header ─────────────────────────────────

function startPipelineIndicatorEffect(): (() => void) | void {
  return effect(() => {
    const dot = el<HTMLSpanElement>("pipeline-indicator");
    if (dot)
      dot.classList.toggle("active", pipelineStatus.value?.state === "running");
  });
}

// ── Effect dispose handles ───────────────────────────────────────────────

const _effectDisposers: (() => void)[] = [];

function trackEffect(dispose: (() => void) | void): void {
  if (typeof dispose === "function") {
    _effectDisposers.push(dispose);
  }
}

// ── Public API ────────────────────────────────────────────────────────────

export function startEffects(): void {
  trackEffect(startStatusEffect());
  // F162: Module indicators, metrics, GPU badges handled by ProcessGrid.astro
  trackEffect(startMetricsEffect());
  trackEffect(startThroughputEffect());
  trackEffect(startWsBadgeEffect());
  trackEffect(startRemoteModeEffect());
  startClockEffect();
  trackEffect(startSyncEffect());
  trackEffect(startLogsEffect());
  trackEffect(startPipelineIndicatorEffect());
  trackEffect(startInputTypeEffect());
}

export function stopEffects(): void {
  // Dispose all signal-driven effects to prevent memory leaks
  for (const dispose of _effectDisposers) {
    try {
      dispose();
    } catch {
      /* ignore */
    }
  }
  _effectDisposers.length = 0;

  if (_clockInterval) {
    clearInterval(_clockInterval);
    _clockInterval = null;
  }
  _lastLogCount = 0;
}
