/**
 * File Input - Maneja el control de entrada de archivos locales.
 *
 * Este módulo centraliza:
 * - Selección de archivos
 * - Controles de reproducción (play/pause/seek)
 * - Polling de información del archivo
 * - Actualización de URL RTMP
 */

import { apiCall, fetchWithAuth } from "../api";
import { showToast } from "../utils";
import { formatTime } from "../utils/format";
import { MESSAGES, INTERVALS } from "../constants";

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

export function copyRtmpUrl(): void {
  const rtmpUrlInput = document.getElementById(
    "input-rtmp-url",
  ) as HTMLInputElement;
  if (!rtmpUrlInput?.value) return;

  navigator.clipboard
    .writeText(rtmpUrlInput.value)
    .then(() => {
      showToast(MESSAGES.URL_COPIED, "success");
    })
    .catch(() => {
      showToast(MESSAGES.URL_COPY_ERROR, "error");
    });
}

// ── File Input Controls ──────────────────────────────────────────────────────

export function handleFileSelect(input: HTMLInputElement): void {
  const filePathInput = document.getElementById(
    "input-file-path",
  ) as HTMLInputElement;
  if (!filePathInput || !input.files?.length) return;

  const fileName = input.files[0].name;
  filePathInput.placeholder = `Ej: C:\\Users\\bruno\\Desktop\\${fileName}`;
  showToast(MESSAGES.INPUT_FILE_SELECTED, "info");
  filePathInput.focus();

  const playerControls = document.getElementById("file-player-controls");
  if (playerControls) playerControls.style.display = "flex";
  setupFilePlayerControls();
}

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
    const response = await fetchWithAuth("/api/input-info", {
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

export function startFileInfoPolling(): void {
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
