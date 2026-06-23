/**
 * Polling Manager - Handles adaptive HTTP polling for status and file info.
 */

import { apiCall, fetchWithAuth } from "../api";
import type { Status } from "../types";
import { pipelineStatus } from "../store/index";
import { updateStatus } from "../store/index";
import { formatTime } from "../utils/format";
import { logger } from "../utils/logger";
import { INTERVALS } from "../constants";

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

  let consecutiveErrors = 0;

  const poll = async () => {
    try {
      const s = await apiCall<Status>("GET", "api/status");
      updateStatus(s);
      consecutiveErrors = 0;
    } catch (err) {
      consecutiveErrors++;
      if (consecutiveErrors === 1) {
        logger.warn("polling", "Failed to fetch status", err);
      } else if (consecutiveErrors % 5 === 0) {
        logger.error(
          "polling",
          `Status fetch failed ${consecutiveErrors} times in a row`,
        );
      }
    }
  };

  poll();
  statusPollInterval = setInterval(poll, getPollInterval());
}

export function restartPolling(): void {
  if (statusPollInterval) {
    clearInterval(statusPollInterval);
    statusPollInterval = null;
  }
  startPolling();
}

export function enterPostStartMode(): void {
  postStartMode = true;
  restartPolling();
  if (postStartTimeout) clearTimeout(postStartTimeout);
  postStartTimeout = setTimeout(() => {
    postStartMode = false;
    restartPolling();
  }, POST_START_DURATION_MS);
}

export function exitPostStartMode(): void {
  postStartMode = false;
  if (postStartTimeout) clearTimeout(postStartTimeout);
  postStartTimeout = null;
  restartPolling();
}

export function stopStatusPolling(): void {
  if (statusPollInterval) {
    clearInterval(statusPollInterval);
    statusPollInterval = null;
  }
  if (postStartTimeout) {
    clearTimeout(postStartTimeout);
    postStartTimeout = null;
  }
}

// ── File Info Polling ──────────────────────────────────────────────────────

let filePollingInterval: ReturnType<typeof setInterval> | null = null;

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
    fetchFileInfo()
      .then((info) => {
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
      })
      .catch(() => {
        /* ignore file info polling errors */
      });
  }, INTERVALS.FILE_POLL);
}

export function stopFileInfoPolling(): void {
  if (filePollingInterval) {
    clearInterval(filePollingInterval);
    filePollingInterval = null;
  }
}
