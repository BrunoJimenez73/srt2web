/**
 * Pipeline Control - Maneja el control del pipeline y operaciones relacionadas.
 *
 * Este módulo centraliza:
 * - Inicio/detención del pipeline
 * - Guardado de configuración
 * - Presets (F19)
 * - Inicialización del dashboard
 * - Manejo de WebSocket y polling
 */

import {
  apiCall,
  getConfig,
  getStatus,
  startPipeline,
  stopPipeline,
  WSClient,
  getWebSocketUrl,
  updateChunkDuration,
  getAuthToken,
} from "../api";
import { showToast, copyToClipboard } from "../utils";
import { formatTime } from "../utils/format";
import { MESSAGES, DEFAULTS, INTERVALS } from "../constants";
import {
  pipelineStatus,
  pipelineConfig,
  wsConnected,
  updateStatus,
  addLog,
  resetThroughput,
  startEffects,
  stopEffects,
  presets,
  selectedPreset,
} from "../store/index";
import { initLogPanel } from "./logpanel";
import type { Config, Status } from "../types";
import type { WebSocketMessage } from "../api";
import { collectConfigFromUI, applyConfigToUI } from "./config-collector";

// Re-export config functions for backwards compatibility
export { collectConfigFromUI, applyConfigToUI };

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
  setLoading(true, "Iniciando pipeline");
  try {
    addLog("INFO", MESSAGES.PIPELINE_STARTING);
    await startPipeline();
    const status = await getStatus();
    updateStatus(status);
    enterPostStartMode();
    addLog("INFO", MESSAGES.PIPELINE_STARTED);
  } catch (e) {
    addLog("ERROR", `Error: ${(e as Error).message}`);
  } finally {
    setLoading(false);
  }
}

export async function handleStop(): Promise<void> {
  if (!confirm(MESSAGES.PIPELINE_CONFIRM_STOP)) {
    return;
  }
  if (isLoading()) return;
  setLoading(true, "Deteniendo pipeline");
  try {
    addLog("INFO", MESSAGES.PIPELINE_STOPPING);
    await stopPipeline();
    const status = await getStatus();
    updateStatus(status);
    resetThroughput();
    postStartMode = false;
    if (postStartTimeout) clearTimeout(postStartTimeout);
    restartPolling();
    addLog("INFO", MESSAGES.PIPELINE_STOPPED);
  } catch (e) {
    addLog("ERROR", `Error: ${(e as Error).message}`);
  } finally {
    setLoading(false);
  }
}

export async function handleSaveConfig(): Promise<void> {
  if (isLoading()) return;
  setLoading(true, "Guardando config");
  try {
    const newConfig = collectConfigFromUI();

    // Extract chunk duration for sync endpoint
    const chunkDuration = parseInt(
      (document.getElementById("input-chunk-duration") as HTMLInputElement)
        ?.value ||
        (document.getElementById("input-rtmp-chunk") as HTMLInputElement)
          ?.value ||
        (document.getElementById("input-file-chunk") as HTMLInputElement)
          ?.value ||
        String(DEFAULTS.CHUNK_DURATION),
    );

    await apiCall("PUT", "/api/config", { config: newConfig });

    // Sync chunk duration to all pipeline modules
    try {
      await updateChunkDuration(chunkDuration);
      addLog("INFO", `Chunk synced: ${chunkDuration}s`);
    } catch (chunkError) {
      addLog("WARNING", `Chunk sync failed: ${(chunkError as Error).message}`);
    }

    const cfg = await getConfig();
    pipelineConfig.value = cfg;
    applyConfigToUI(cfg);
    showToast(MESSAGES.CONFIG_SAVED, "success");
    addLog("INFO", "Configuración guardada");
  } catch (e) {
    const msg = (e as Error).message;
    showToast(`${MESSAGES.CONFIG_SAVE_ERROR}: ${msg}`, "error");
    addLog("ERROR", `Error al guardar: ${msg}`);
  } finally {
    setLoading(false);
  }
}

// ── File Input Controls ──────────────────────────────────────────────────────

export async function fileInputPlay(): Promise<void> {
  try {
    await apiCall("POST", "input/control/play");
    showToast(MESSAGES.INPUT_FILE_PLAY, "success");
  } catch (e) {
    showToast(`Error al reproducir: ${(e as Error).message}`, "error");
  }
}

export async function fileInputPause(): Promise<void> {
  try {
    await apiCall("POST", "input/control/pause");
    showToast(MESSAGES.INPUT_FILE_PAUSE, "success");
  } catch (e) {
    showToast(`Error al pausar: ${(e as Error).message}`, "error");
  }
}

export async function fileInputSeek(position: number): Promise<void> {
  try {
    await apiCall("POST", "input/control/seek", { position });
  } catch (e) {
    showToast(`Error al buscar posición: ${(e as Error).message}`, "error");
  }
}

async function fetchFileInfo(): Promise<{
  duration: number;
  position: number;
  is_playing: boolean;
} | null> {
  try {
    const response = await fetch(`${window.location.origin}/api/input-info`, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return null;
    const data = await response.json();
    if (data.type === "file") {
      return {
        duration: data.duration || 0,
        position: data.position || 0,
        is_playing: data.is_playing || false,
      };
    }
    return null;
  } catch {
    return null;
  }
}

let filePollingInterval: ReturnType<typeof setInterval> | null = null;

function startFileInfoPolling(): void {
  if (filePollingInterval) clearInterval(filePollingInterval);

  const positionSlider = document.getElementById(
    "input-file-position",
  ) as HTMLInputElement | null;
  const currentDisplay = document.getElementById(
    "file-time-current",
  ) as HTMLSpanElement | null;
  const totalDisplay = document.getElementById(
    "file-time-total",
  ) as HTMLSpanElement | null;
  const playBtn = document.getElementById(
    "btn-file-play",
  ) as HTMLButtonElement | null;
  const pauseBtn = document.getElementById(
    "btn-file-pause",
  ) as HTMLButtonElement | null;

  filePollingInterval = setInterval(() => {
    fetchFileInfo().then((info) => {
      if (!info) return;

      if (positionSlider && info.duration > 0) {
        positionSlider.value = (
          (info.position / info.duration) *
          100
        ).toString();
      }
      if (currentDisplay)
        currentDisplay.textContent = formatTime(info.position);
      if (totalDisplay) totalDisplay.textContent = formatTime(info.duration);

      if (playBtn && pauseBtn) {
        if (info.is_playing) {
          playBtn.style.display = "none";
          pauseBtn.style.display = "inline";
        } else {
          playBtn.style.display = "inline";
          pauseBtn.style.display = "none";
        }
      }
    });
  }, INTERVALS.FILE_POLL);
}

export function stopFileInfoPolling(): void {
  if (filePollingInterval) {
    clearInterval(filePollingInterval);
    filePollingInterval = null;
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
    fileInputPlay().then(() => {
      playBtn.style.display = "none";
      pauseBtn.style.display = "inline";
    });
  });

  pauseBtn.addEventListener("click", () => {
    fileInputPause().then(() => {
      pauseBtn.style.display = "none";
      playBtn.style.display = "inline";
    });
  });

  restartBtn.addEventListener("click", () => {
    fileInputSeek(0).then(() => {
      positionSlider.value = "0";
      fileInputPlay().then(() => {
        playBtn.style.display = "none";
        pauseBtn.style.display = "inline";
      });
    });
  });

  let seekTimeout: ReturnType<typeof setTimeout> | null = null;
  positionSlider.addEventListener("input", () => {
    if (seekTimeout) clearTimeout(seekTimeout);
    const percent = parseInt(positionSlider.value);

    seekTimeout = setTimeout(() => {
      fetchFileInfo().then((info) => {
        if (info?.duration) {
          fileInputSeek((percent / 100) * info.duration);
        }
      });
    }, INTERVALS.SEEK_DEBOUNCE);
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

// ── Polling Configuration ───────────────────────────────────────────────────

const POLL_INTERVALS = {
  RUNNING: 3000,
  STOPPED: 10000,
  POST_START: 1000,
} as const;

const POST_START_DURATION_MS = 5000;

let statusPollInterval: ReturnType<typeof setInterval> | null = null;
let postStartMode = false;
let postStartTimeout: ReturnType<typeof setTimeout> | null = null;

function getPollInterval(): number {
  const state = pipelineStatus.value?.state;
  if (postStartMode) return POLL_INTERVALS.POST_START;
  if (state === "running") return POLL_INTERVALS.RUNNING;
  return POLL_INTERVALS.STOPPED;
}

function startPolling(): void {
  if (statusPollInterval) clearInterval(statusPollInterval);

  const poll = async () => {
    try {
      const s = await apiCall<Status>("GET", "api/status");
      updateStatus(s);
    } catch {
      // Silently fail on poll errors
    }
  };

  poll();
  statusPollInterval = setInterval(poll, getPollInterval());
}

function restartPolling(): void {
  if (statusPollInterval) {
    clearInterval(statusPollInterval);
    statusPollInterval = null;
  }
  startPolling();
}

function enterPostStartMode(): void {
  postStartMode = true;
  restartPolling();
  if (postStartTimeout) clearTimeout(postStartTimeout);
  postStartTimeout = setTimeout(() => {
    postStartMode = false;
    restartPolling();
  }, POST_START_DURATION_MS);
}

// ── Initialization ────────────────────────────────────────────────────────────

let wsClient: WSClient | null = null;

export async function initDashboard(): Promise<void> {
  // Initialize log panel first so logs can be displayed
  initLogPanel();

  addLog("INFO", MESSAGES.LOADING);

  try {
    // Load config and apply to UI
    const cfg = await getConfig();
    pipelineConfig.value = cfg;
    applyConfigToUI(cfg);

    // Initialize RTMP URL if needed
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

    // Load initial status
    const initialStatus = await apiCall<Status>("GET", "api/status");
    updateStatus(initialStatus);

    // Start effects (reactive DOM updates)
    startEffects();

    // WebSocket connection for logs + status
    const wsUrl = getWebSocketUrl("/ws/logs");
    const token = getAuthToken();
    wsClient = new WSClient(wsUrl, {
      maxReconnectAttempts: 5,
      backoffBase: 1000,
      authToken: token,
    });
    wsClient.onMessage((data: WebSocketMessage) => {
      if (data.type === "log") {
        addLog(data.level ?? "INFO", data.message ?? "");
      } else if (data.type === "status" && data.status) {
        updateStatus(data.status);
        // Check if pipeline started to adjust polling
        if (data.status.state === "running" && !postStartMode) {
          enterPostStartMode();
        }
      }
    });
    wsClient.onError(() => {
      addLog("ERROR", MESSAGES.WS_ERROR);
    });
    wsClient.onClose((wasFirstAttempt: boolean) => {
      wsConnected.value = false;
      if (wasFirstAttempt) {
        addLog("WARNING", "WebSocket connection failed");
      } else {
        addLog("ERROR", MESSAGES.WS_DISCONNECTED);
      }
    });
    wsClient.connect();

    // Start adaptive HTTP polling
    startPolling();

    addLog("INFO", MESSAGES.SUCCESS);
  } catch (e) {
    addLog("ERROR", `Error de inicialización: ${(e as Error).message}`);
  }
}

export function cleanup(): void {
  if (statusPollInterval) {
    clearInterval(statusPollInterval);
    statusPollInterval = null;
  }
  if (postStartTimeout) {
    clearTimeout(postStartTimeout);
    postStartTimeout = null;
  }
  if (wsClient) {
    wsClient.close();
    wsClient = null;
  }
  stopEffects();
  stopFileInfoPolling();
}

// ── Event Setup ───────────────────────────────────────────────────────────────

export function setupEventListeners(): void {
  document.getElementById("btn-start")?.addEventListener("click", handleStart);
  document.getElementById("btn-stop")?.addEventListener("click", handleStop);

  // TTS engine change → toggle voice dropdowns
  document.getElementById("tts-engine")?.addEventListener("change", (e) => {
    const isEdge = (e.target as HTMLSelectElement).value === "edge-tts";
    const edgeGroup = document.getElementById(
      "tts-voice-edge-group",
    ) as HTMLDivElement;
    const piperGroup = document.getElementById(
      "tts-voice-piper-group",
    ) as HTMLDivElement;
    if (edgeGroup) edgeGroup.style.display = isEdge ? "block" : "none";
    if (piperGroup) piperGroup.style.display = isEdge ? "none" : "block";
  });
}

// ── Metrics Refresh ───────────────────────────────────────────────────────────

export async function refreshMetrics(): Promise<void> {
  try {
    const res = await fetch("/api/status");
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
    console.error("Metrics refresh failed:", e);
  }
}

// ── Preset Functions (F19) ───────────────────────────────────────────────────

/** Fetch and populate the presets list */
export async function loadPresets(): Promise<void> {
  try {
    const response = await fetch("/api/presets");
    if (!response.ok) return;
    const data = await response.json();
    presets.value = data.presets || [];
  } catch (e) {
    addLog("ERROR", `Error loading presets: ${(e as Error).message}`);
  }
}

/** Apply a preset by name (built-in or saved) */
export async function applyPreset(name: string): Promise<void> {
  try {
    setLoading(true, `Applying preset: ${name}`);
    const response = await fetch(`/api/presets/${encodeURIComponent(name)}/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) {
      const err = await response.text();
      throw new Error(err || `Failed to apply preset: ${name}`);
    }
    const data = await response.json();
    pipelineConfig.value = data.config;
    applyConfigToUI(data.config);
    selectedPreset.value = name;
    showToast(`Preset applied: ${name}`, "success");
    addLog("INFO", `Preset applied: ${name}`);
  } catch (e) {
    showToast(`Error applying preset: ${(e as Error).message}`, "error");
    addLog("ERROR", `Error applying preset: ${(e as Error).message}`);
  } finally {
    setLoading(false);
  }
}

/** Save current config as a named preset */
export async function savePreset(name: string): Promise<void> {
  try {
    setLoading(true, `Saving preset: ${name}`);
    const response = await fetch("/api/presets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description: "" }),
    });
    if (!response.ok) {
      const err = await response.text();
      throw new Error(err || `Failed to save preset: ${name}`);
    }
    await loadPresets(); // Refresh list
    showToast(`Preset saved: ${name}`, "success");
    addLog("INFO", `Preset saved: ${name}`);
  } catch (e) {
    showToast(`Error saving preset: ${(e as Error).message}`, "error");
    addLog("ERROR", `Error saving preset: ${(e as Error).message}`);
  } finally {
    setLoading(false);
  }
}

/** Export current config as YAML file */
export function exportConfig(): void {
  try {
    const cfg = pipelineConfig.value;
    if (!cfg) {
      showToast("No config to export", "error");
      return;
    }
    const yamlStr = dumpConfig(cfg);
    const blob = new Blob([yamlStr], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `srt2web-config-${new Date().toISOString().slice(0, 10)}.yaml`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Config exported", "success");
  } catch (e) {
    showToast(`Export failed: ${(e as Error).message}`, "error");
  }
}

/** Minimal YAML serializer for config export (no external deps) */
function dumpConfig(obj: unknown, indent = 0): string {
  const pad = "  ".repeat(indent);
  if (obj === null || obj === undefined) return "null";
  if (typeof obj === "string") return `"${obj}"`;
  if (typeof obj === "number" || typeof obj === "boolean") return String(obj);
  if (Array.isArray(obj)) {
    if (obj.length === 0) return "[]";
    return obj.map((v) => `${pad}- ${dumpConfig(v, indent + 1)}`).join("\n");
  }
  if (typeof obj === "object") {
    const entries = Object.entries(obj);
    if (entries.length === 0) return "{}";
    return entries
      .map(([k, v]) => `${pad}${k}:\n${dumpConfig(v, indent + 1)}`)
      .join("\n");
  }
  return String(obj);
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

function setupCopyButtons(): void {
  document.getElementById("btn-copy-emision")?.addEventListener("click", () => {
    const urlEl = document.getElementById("url-emision");
    if (urlEl?.textContent) {
      copyToClipboard(urlEl.textContent)
        .then(() => showToast("URL de emisión copiada", "success"))
        .catch(() => showToast("Error al copiar URL", "error"));
    }
  });

  document.getElementById("btn-copy-stream")?.addEventListener("click", () => {
    const urlEl = document.getElementById("url-stream");
    if (urlEl?.textContent) {
      copyToClipboard(urlEl.textContent)
        .then(() => showToast("URL del stream copiada", "success"))
        .catch(() => showToast("Error al copiar URL", "error"));
    }
  });

  document.getElementById("btn-copy-player")?.addEventListener("click", () => {
    const urlEl = document.getElementById("url-player");
    if (urlEl) {
      const url = urlEl.getAttribute("href") || urlEl.textContent;
      if (url)
        copyToClipboard(url)
          .then(() => showToast("URL del player copiada", "success"))
          .catch(() => showToast("Error al copiar URL", "error"));
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

// Expose saveConfig globally for HTML onclick handlers
window.saveConfig = handleSaveConfig;