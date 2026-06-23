/**
 * Pipeline Control - Barrel re-export for backwards compatibility.
 *
 * Core logic has been split into:
 * - ws-manager.ts: WebSocket connection management
 * - polling.ts: Adaptive HTTP polling
 * - config-client.ts: Config save/load/export
 * - presets-client.ts: Preset operations
 *
 * This file re-exports all public API to avoid breaking existing imports.
 */

// Re-export from new modules
export {
  connectWebSocket,
  disconnectWebSocket,
  getWSClient,
} from "./ws-manager";
export {
  restartPolling,
  enterPostStartMode,
  exitPostStartMode,
  stopStatusPolling,
  startFileInfoPolling,
  stopFileInfoPolling,
} from "./polling";
export { handleSaveConfig, exportConfig } from "./config-client";
export { loadPresets, applyPreset, savePreset } from "./presets-client";
export { collectConfigFromUI, applyConfigToUI } from "./config-collector";
import { logger } from "../utils/logger";

// Re-export from api and store for convenience
export {
  apiCall,
  fetchWithAuth,
  getConfig,
  getStatus,
  startPipeline,
  stopPipeline,
  updateChunkDuration,
  getAuthToken,
} from "../api";

import {
  apiCall,
  fetchWithAuth,
  getConfig,
  getStatus,
  startPipeline,
  stopPipeline,
} from "../api";
import { copyToClipboard } from "../utils";
import { showToast } from "./toast";
import { showConfirm } from "./confirm-modal";
import { DEFAULTS } from "../constants";
import { t } from "../i18n";
import { connectionMode, emitterAddress } from "../store/signals";
import {
  pipelineStatus,
  pipelineConfig,
  addLog,
  resetThroughput,
  startEffects,
  stopEffects,
} from "../store/index";
import { initLogPanel } from "./logpanel";
import type { Status } from "../types";
import { collectConfigFromUI, applyConfigToUI } from "./config-collector";
import { connectWebSocket, disconnectWebSocket } from "./ws-manager";
import {
  restartPolling,
  startFileInfoPolling,
  stopFileInfoPolling,
  exitPostStartMode,
  stopStatusPolling,
} from "./polling";

// ── Loading State Helper ────────────────────────────────────────────────────
let _isLoading = false;

function setLoading(loading: boolean, action: string = ""): void {
  _isLoading = loading;
  document.body.classList.toggle("loading", loading);
  if (loading && action) {
    addLog("INFO", `${action}...`);
  }
}

function isLoading(): boolean {
  return _isLoading;
}

// ── Pipeline Control ──────────────────────────────────────────────────────────

export async function handleStart(): Promise<void> {
  if (isLoading()) return;
  setLoading(true, t("pipeline_starting"));
  try {
    addLog("INFO", t("pipeline_starting"));
    await startPipeline();
    const status = await getStatus();
    pipelineStatus.value = status;
    const { enterPostStartMode: enterPost } = await import("./polling");
    enterPost();
    addLog("INFO", t("pipeline_started"));
  } catch (e) {
    addLog("ERROR", `Error: ${(e as Error).message}`);
  } finally {
    setLoading(false);
  }
}

export async function handleStop(): Promise<void> {
  if (!(await showConfirm(t("confirm_stop")))) {
    return;
  }
  if (isLoading()) return;
  setLoading(true, t("pipeline_stopping"));
  try {
    addLog("INFO", t("pipeline_stopping"));
    await stopPipeline();
    const status = await getStatus();
    pipelineStatus.value = status;
    resetThroughput();
    exitPostStartMode();
    restartPolling();
    addLog("INFO", t("pipeline_stopped"));
  } catch (e) {
    addLog("ERROR", `Error: ${(e as Error).message}`);
  } finally {
    setLoading(false);
  }
}

// ── File Input Controls ──────────────────────────────────────────────────────

export async function fileInputPlay(): Promise<void> {
  try {
    await apiCall("POST", "input/control/play");
    showToast(t("input_file_play"), "success");
  } catch (e) {
    showToast(`${t("error")}: ${(e as Error).message}`, "error");
  }
}

export async function fileInputPause(): Promise<void> {
  try {
    await apiCall("POST", "input/control/pause");
    showToast(t("input_file_pause"), "success");
  } catch (e) {
    showToast(`${t("error")}: ${(e as Error).message}`, "error");
  }
}

export async function fileInputSeek(position: number): Promise<void> {
  try {
    await apiCall("POST", "input/control/seek", { position });
  } catch (e) {
    showToast(
      `${t("input_file_seek_error")}: ${(e as Error).message}`,
      "error",
    );
  }
}

export function setupFilePlayerControls(): void {
  const playBtn = document.getElementById(
    "btn-file-play",
  ) as HTMLButtonElement | null;
  const pauseBtn = document.getElementById(
    "btn-file-pause",
  ) as HTMLButtonElement | null;
  const restartBtn = document.getElementById(
    "btn-file-restart",
  ) as HTMLButtonElement | null;
  const positionSlider = document.getElementById(
    "input-file-position",
  ) as HTMLInputElement | null;

  if (!playBtn || !pauseBtn || !restartBtn || !positionSlider) return;

  playBtn.style.display = "inline";
  pauseBtn.style.display = "none";

  playBtn.addEventListener("click", () => {
    fileInputPlay()
      .then(() => {
        playBtn.style.display = "none";
        pauseBtn.style.display = "inline";
      })
      .catch(() => {
        /* ignore play errors */
      });
  });

  pauseBtn.addEventListener("click", () => {
    fileInputPause()
      .then(() => {
        pauseBtn.style.display = "none";
        playBtn.style.display = "inline";
      })
      .catch(() => {
        /* ignore pause errors */
      });
  });

  restartBtn.addEventListener("click", () => {
    fileInputSeek(0)
      .then(() => {
        positionSlider.value = "0";
        fileInputPlay()
          .then(() => {
            playBtn.style.display = "none";
            pauseBtn.style.display = "inline";
          })
          .catch(() => {
            /* ignore play errors */
          });
      })
      .catch(() => {
        /* ignore seek errors */
      });
  });

  let seekTimeout: ReturnType<typeof setTimeout> | null = null;
  positionSlider.addEventListener("input", () => {
    if (seekTimeout) clearTimeout(seekTimeout);
    const percent = parseInt(positionSlider.value);

    seekTimeout = setTimeout(() => {
      fetchWithAuth(`${window.location.origin}/api/input-info`, {
        headers: { Accept: "application/json" },
      })
        .then((r) => r.json())
        .then((info) => {
          if (info?.duration) {
            fileInputSeek((percent / 100) * info.duration);
          }
        })
        .catch(() => {
          /* ignore seek info errors */
        });
    }, 300);
  });

  startFileInfoPolling();
}

// ── RTMP Helpers ──────────────────────────────────────────────────────────────

export function updateRtmpUrl(): void {
  const rtmpUrlInput = document.getElementById(
    "input-rtmp-url",
  ) as HTMLInputElement;
  if (!rtmpUrlInput) return;

  const portInput = document.getElementById(
    "input-rtmp-port",
  ) as HTMLInputElement;
  const appInput = document.getElementById(
    "input-rtmp-app",
  ) as HTMLInputElement;
  const keyInput = document.getElementById(
    "input-rtmp-key",
  ) as HTMLInputElement;

  const port = portInput?.value || "1935";
  const app = appInput?.value || "live";
  const key = keyInput?.value || "stream";

  rtmpUrlInput.value = `rtmp://127.0.0.1:${port}/${app}/${key}`;
}

// ── Initialization ────────────────────────────────────────────────────────────

export async function initDashboard(): Promise<void> {
  initLogPanel();

  addLog("INFO", t("loading"));

  try {
    const cfg = await getConfig();
    pipelineConfig.value = cfg;
    applyConfigToUI(cfg);

    const inputTypeSelect = document.getElementById(
      "input-type",
    ) as HTMLSelectElement;
    if (inputTypeSelect?.value === "rtmp") updateRtmpUrl();
    if (inputTypeSelect?.value === "file") {
      const filePathInput = document.getElementById(
        "input-file-path",
      ) as HTMLInputElement;
      if (filePathInput?.value) setupFilePlayerControls();
    }

    const initialStatus = await apiCall<Status>("GET", "api/status");
    pipelineStatus.value = initialStatus;

    startEffects();

    connectWebSocket();

    const { restartPolling: restartPoll } = await import("./polling");
    restartPoll();

    addLog("INFO", t("success"));
  } catch (e) {
    addLog("ERROR", `${t("init_error")}: ${(e as Error).message}`);
  }
}

export function cleanup(): void {
  stopStatusPolling();
  stopFileInfoPolling();
  disconnectWebSocket();
  stopEffects();
}

// ── Event Setup ───────────────────────────────────────────────────────────────

export function setupEventListeners(): void {
  document.getElementById("btn-start")?.addEventListener("click", handleStart);
  document.getElementById("btn-stop")?.addEventListener("click", handleStop);

  document.getElementById("btn-mode-local")?.addEventListener("click", () => {
    connectionMode.value = "local";
  });
  document.getElementById("btn-mode-remote")?.addEventListener("click", () => {
    connectionMode.value = "remote";
    (async () => {
      try {
        const res = await fetchWithAuth("/api/network/info");
        const info = await res.json();
        if (info.public_ip) {
          emitterAddress.value = info.public_ip;
          const input = document.getElementById(
            "emitter-address",
          ) as HTMLInputElement;
          if (input) input.value = info.public_ip;
        }
      } catch {}
    })();
  });

  document.getElementById("emitter-address")?.addEventListener("input", (e) => {
    emitterAddress.value = (e.target as HTMLInputElement).value;
  });

  document.getElementById("tts-engine")?.addEventListener("change", (e) => {
    handleTtsEngineChange((e.target as HTMLSelectElement).value);
  });

  // Expose for legacy inline onchange="window.handleTtsEngineChange(this.value)"
  (
    window as unknown as { handleTtsEngineChange: (v: string) => void }
  ).handleTtsEngineChange = handleTtsEngineChange;
}

export function handleTtsEngineChange(engine: string): void {
  const isEdge = engine === "edge-tts";
  const edgeGroup = document.getElementById(
    "tts-voice-edge-group",
  ) as HTMLDivElement | null;
  const piperGroup = document.getElementById(
    "tts-voice-piper-group",
  ) as HTMLDivElement | null;
  if (edgeGroup) edgeGroup.style.display = isEdge ? "block" : "none";
  if (piperGroup) piperGroup.style.display = isEdge ? "none" : "block";
}

// ── Metrics Refresh ───────────────────────────────────────────────────────────

export async function refreshMetrics(): Promise<void> {
  try {
    const res = await fetchWithAuth("/api/status");
    const status = await res.json();
    const s = status.system || {};

    const cpuEl = document.getElementById("metric-cpu-value");
    const cpuBar = document.getElementById("metric-cpu-bar");
    const memEl = document.getElementById("metric-memory-value");
    const memPercent = document.getElementById("metric-memory-percent");
    const memBar = document.getElementById("metric-memory-bar");
    const gpuEl = document.getElementById("metric-gpu-value");
    const gpuBar = document.getElementById("metric-gpu-bar");

    if (cpuEl) cpuEl.textContent = (s.cpu_percent || s.cpu_usage || 0) + "%";
    if (cpuBar) cpuBar.style.width = (s.cpu_percent || s.cpu_usage || 0) + "%";
    if (memEl) memEl.textContent = (s.memory_mb || 0).toFixed(0) + " MB";
    if (memPercent)
      memPercent.textContent = (s.memory_percent || s.memory_usage || 0) + "%";
    if (memBar)
      memBar.style.width = (s.memory_percent || s.memory_usage || 0) + "%";
    if (gpuEl) gpuEl.textContent = (s.gpu_usage || 0) + "%";
    if (gpuBar) gpuBar.style.width = (s.gpu_usage || 0) + "%";
  } catch (e) {
    logger.error("pipeline-control", "Metrics refresh failed", e);
  }
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

function setupCopyButtons(): void {
  document.getElementById("btn-copy-emision")?.addEventListener("click", () => {
    const urlEl = document.getElementById("url-emision");
    if (urlEl?.textContent) {
      copyToClipboard(urlEl.textContent)
        .then(() => showToast(t("url_copied"), "success"))
        .catch(() => showToast(t("url_copy_error"), "error"));
    }
  });

  document.getElementById("btn-copy-stream")?.addEventListener("click", () => {
    const urlEl = document.getElementById("url-stream");
    if (urlEl?.textContent) {
      copyToClipboard(urlEl.textContent)
        .then(() => showToast(t("url_copied"), "success"))
        .catch(() => showToast(t("url_copy_error"), "error"));
    }
  });

  document.getElementById("btn-copy-player")?.addEventListener("click", () => {
    const urlEl = document.getElementById("url-player");
    if (urlEl) {
      const url = urlEl.getAttribute("href") || urlEl.textContent;
      if (url)
        copyToClipboard(url)
          .then(() => showToast(t("url_copied"), "success"))
          .catch(() => showToast(t("url_copy_error"), "error"));
    }
  });
}

let _bootstrapped = false;

export function bootstrap(): void {
  if (_bootstrapped) return;
  _bootstrapped = true;

  setupEventListeners();
  setupCopyButtons();
  setTimeout(() => {
    initDashboard();
    refreshMetrics();
  }, 100);
}

window.addEventListener("beforeunload", cleanup);

// Expose functions globally for HTML onclick / component event handlers
import { handleSaveConfig } from "./config-client";
(window as unknown as Record<string, unknown>).saveConfig = handleSaveConfig;
(window as unknown as Record<string, unknown>).startPipeline = handleStart;
(window as unknown as Record<string, unknown>).stopPipeline = handleStop;
