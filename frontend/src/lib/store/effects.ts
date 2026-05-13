/**
 * Effects - Signal-driven DOM updates.
 *
 * Kept minimal: only cross-cutting concerns that can't live inside
 * individual component <script> blocks.
 *
 * Component-specific DOM updates (MetricsCard, StatusCard, Header)
 * now live in their own .astro <script> blocks.
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
} from "./signals";
import { addLog as addLogToPanel } from "../modules/logpanel";

// ── Element refs (lazy) ────────────────────────────────────────────────────────

function el<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
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
