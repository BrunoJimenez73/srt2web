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
} from "./signals";
import { addLog as addLogToPanel } from "../modules/logpanel";
import { t } from "../i18n";

// ── Element refs (lazy) ────────────────────────────────────────────────────────

function el<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

// ── Effect: Status Card (text, dot, buttons) ────────────────────────────────

function startStatusEffect(): void {
  effect(() => {
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

// ── Effect: Module Indicators ───────────────────────────────────────────────

function startModuleIndicatorsEffect(): void {
  effect(() => {
    const status = pipelineStatus.value;
    const modules = status?.modules || [];
    const running = status?.state === "running";

    const indicatorIds = [
      "indicator-input",
      "indicator-whisper",
      "indicator-translate",
      "indicator-tts",
      "indicator-subtitles",
      "indicator-mixer",
      "indicator-muxer",
      "indicator-output",
    ];

    for (const id of indicatorIds) {
      const indicator = el<HTMLSpanElement>(id);
      if (!indicator) continue;

      const moduleName = id.replace("indicator-", "");
      const mod = modules.find(
        (m) =>
          m.name === moduleName ||
          (moduleName === "input" && m.name === "input") ||
          (moduleName === "whisper" && m.name === "transcriber") ||
          (moduleName === "translate" && m.name === "translator") ||
          (moduleName === "tts" && m.name === "tts_engine") ||
          (moduleName === "subtitles" && m.name === "subtitle_generator") ||
          (moduleName === "mixer" && m.name === "audio_mixer") ||
          (moduleName === "muxer" && m.name === "video_muxer") ||
          (moduleName === "output" && m.name === "output"),
      );

      const isActive = running && mod?.enabled;
      indicator.classList.toggle("active", !!isActive);
      indicator.classList.toggle("inactive", !isActive);
    }
  });
}

// ── Effect: System Metrics ──────────────────────────────────────────────────

function startMetricsEffect(): void {
  effect(() => {
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

// ── Effect: Module Time and Chunks ──────────────────────────────────────────

function startModuleMetricsEffect(): void {
  effect(() => {
    const status = pipelineStatus.value;
    const modules = status?.modules || [];

    for (const mod of modules) {
      const timeEl = el<HTMLElement>(`module-time-${mod.name}`);
      const chunksEl = el<HTMLElement>(`module-chunks-${mod.name}`);

      if (timeEl) {
        const ms = mod.last_process_time_ms ?? 0;
        timeEl.textContent =
          ms > 0
            ? ms >= 1000
              ? `${(ms / 1000).toFixed(1)}s`
              : `${ms}ms`
            : "--";
      }
      if (chunksEl) {
        chunksEl.textContent = String(mod.processed_chunks ?? 0);
      }
    }
  });
}

// ── Effect: Throughput Metric ───────────────────────────────────────────────

function startThroughputEffect(): void {
  effect(() => {
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

// ── Effect: GPU Badges (per-module) ─────────────────────────────────────────
// Shows "GPU" when module uses GPU acceleration, "CPU" when explicitly CPU,
// and hides the badge when module state is unknown/not running.

function startGpuBadgesEffect(): void {
  effect(() => {
    const status = pipelineStatus.value;
    const modules = status?.modules || [];
    const running = status?.state === "running";

    // First pass: update badges from module status
    const updatedModules = new Set<string>();
    for (const mod of modules) {
      const badge = el<HTMLElement>(`gpu-badge-${mod.name}`);
      if (!badge) continue;
      updatedModules.add(`gpu-badge-${mod.name}`);

      const usingGpu =
        mod.extra?.using_gpu === true ||
        mod.extra?.device === "cuda" ||
        mod.extra?.device === "mps";

      if (!mod.enabled) {
        badge.style.display = "none";
      } else if (usingGpu) {
        badge.style.display = "inline";
        badge.textContent = "GPU";
        badge.classList.add("active");
      } else {
        badge.style.display = "inline";
        badge.textContent = "CPU";
        badge.classList.remove("active");
      }
    }

    // Second pass: show badges for known static cards not in module status
    // (translator is CPU-only, always visible when pipeline is running)
    if (running && !updatedModules.has("gpu-badge-translator")) {
      const translatorBadge = el<HTMLElement>("gpu-badge-translator");
      if (translatorBadge) {
        translatorBadge.style.display = "inline";
        translatorBadge.textContent = "CPU";
        translatorBadge.classList.remove("active");
      }
    }
  });
}

// ── Effect: WS Status Badge ─────────────────────────────────────────────────

function startWsBadgeEffect(): void {
  effect(() => {
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

function startRemoteModeEffect(): void {
  effect(() => {
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

function startSyncEffect(): void {
  effect(() => {
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

function startLogsEffect(): void {
  effect(() => {
    const logs = pipelineLogs.value;
    const newLogs = logs.slice(_lastLogCount);
    for (const log of newLogs) {
      addLogToPanel(log.level, log.message, log.timestamp);
    }
    _lastLogCount = logs.length;
  });
}

// ── Effect: Pipeline status dot in header ─────────────────────────────────

function startPipelineIndicatorEffect(): void {
  effect(() => {
    const dot = el<HTMLSpanElement>("pipeline-indicator");
    if (dot)
      dot.classList.toggle("active", pipelineStatus.value?.state === "running");
  });
}

// ── Public API ────────────────────────────────────────────────────────────

export function startEffects(): void {
  startStatusEffect();
  startModuleIndicatorsEffect();
  startMetricsEffect();
  startModuleMetricsEffect();
  startThroughputEffect();
  startGpuBadgesEffect();
  startWsBadgeEffect();
  startRemoteModeEffect();
  startClockEffect();
  startSyncEffect();
  startLogsEffect();
  startPipelineIndicatorEffect();
}

export function stopEffects(): void {
  if (_clockInterval) {
    clearInterval(_clockInterval);
    _clockInterval = null;
  }
  _lastLogCount = 0;
}
