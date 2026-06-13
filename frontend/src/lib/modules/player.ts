/**
 * Módulo para el reproductor HLS.
 *
 * Subtitles are rendered by SubtitleRenderer (custom VTT polling +
 * positioned div) instead of relying on HLS.js native track support,
 * which is unreliable with live rolling-window playlists.
 */

import { logger } from "../utils/logger";
import { SubtitleRenderer } from "./subtitle-renderer";

// HLS.js type declarations - must be before usage
declare const Hls: HlsStatic | undefined;

interface HlsStatic {
  new (config?: Partial<HlsConfig>): HlsInstance;
  isSupported(): boolean;
  Events: typeof HlsEvents;
  ErrorTypes: typeof HlsErrorTypes;
}

interface HlsInstance {
  loadSource(url: string): void;
  attachMedia(media: HTMLVideoElement): void;
  startLoad(): void;
  stopLoad(): void;
  recoverMediaError(): void;
  destroy(): void;
  on(event: string, callback: (...args: unknown[]) => void): void;
  once(event: string, callback: (...args: unknown[]) => void): void;
}

interface HlsConfig {
  debug: boolean;
  enableWorker: boolean;
  lowLatencyMode: boolean;
  backBufferLength: number;
  maxLoadingDelay: number;
  maxBufferLength: number;
  maxMaxBufferLength: number;
  liveSyncMaxLatency: number;
  liveDurationInfinity: boolean;
  enableCEA708Captions: boolean;
}

// HLS Events enum
const HlsEvents = {
  MANIFEST_PARSED: "hlsManifestParsed",
  ERROR: "hlsError",
  FRAG_BUFFERED: "hlsFragBuffered",
  LEVEL_SWITCH: "hlsLevelSwitch",
};

// HLS Error Types enum
const HlsErrorTypes = {
  NETWORK_ERROR: "networkError",
  MEDIA_ERROR: "mediaError",
};

interface HlsErrorData {
  type: string;
  fatal: boolean;
  details: string;
}

// Health check state
let healthCheckInterval: ReturnType<typeof setInterval> | null = null;
let consecutiveErrors = 0;
const MAX_CONSECUTIVE_ERRORS = 5;

// Retry backoff state
let retryCount = 0;
const MAX_RETRY_DELAY_MS = 30000;
const BASE_RETRY_DELAY_MS = 2000;

export function initHlsPlayer(): void {
  const video = document.getElementById("video-player") as HTMLVideoElement;
  const container = document.getElementById("video-container") as HTMLElement;
  const waitingEl = document.getElementById("waiting");
  const errorOverlay = document.getElementById("error-overlay");
  const errorMessage = document.getElementById("error-message");
  const btnRetry = document.getElementById("btn-retry");
  const btnCC = document.getElementById("btn-cc") as HTMLButtonElement;

  if (!video) {
    logger.error("player", "Video element not found");
    return;
  }

  // Cache buster to prevent loading stale HLS segments from previous sessions
  const _sessionTs = Date.now();
  const streamUrl = `${window.location.origin}/hls/master.m3u8?_=${_sessionTs}`;
  let hls: HlsInstance | null = null;
  let renderer: SubtitleRenderer | null = null;
  let isConnected = false;
  let subtitlesEnabled = true;
  let nativeTrackCheck: ReturnType<typeof setInterval> | null = null;

  function showError(message: string) {
    if (errorOverlay) errorOverlay.style.display = "flex";
    if (errorMessage) errorMessage.textContent = message;
    if (waitingEl) waitingEl.style.display = "none";
    isConnected = false;
  }

  function hideError() {
    if (errorOverlay) errorOverlay.style.display = "none";
  }

  // Health check - monitor stream availability
  function startHealthCheck() {
    stopHealthCheck();
    consecutiveErrors = 0;

    healthCheckInterval = setInterval(async () => {
      try {
        const response = await fetch(streamUrl, {
          method: "HEAD",
          cache: "no-cache",
        });

        if (response.ok) {
          consecutiveErrors = 0;
          if (!isConnected && hls) {
            hls.startLoad();
          }
        } else {
          consecutiveErrors++;
          logger.warn(
            "player",
            "Stream not available",
            response.status,
            consecutiveErrors,
          );
        }
      } catch {
        consecutiveErrors++;
        logger.warn("player", "Stream check failed", consecutiveErrors);
      }

      // If too many consecutive errors, stop checking and show reconnect
      if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS && hls) {
        stopHealthCheck();
        showError(
          "Stream no disponible. Haz clic en Reintentar para conectar.",
        );
      }
    }, 10000); // Check every 10 seconds
  }

  function stopHealthCheck() {
    if (healthCheckInterval) {
      clearInterval(healthCheckInterval);
      healthCheckInterval = null;
    }
  }

  function handlePlayError(err: unknown) {
    if (err instanceof DOMException && err.name === "NotAllowedError") {
      showError(
        "Haz clic en el reproductor o presiona Reintentar para reproducir",
      );
    } else {
      logger.error("player", "play() failed", err);
    }
  }

  function connect() {
    hideError();
    if (waitingEl) waitingEl.style.display = "block";
    isConnected = false;
    consecutiveErrors = 0;
    retryCount = 0;

    // Update cache buster for fresh session
    const ts = Date.now();
    const freshStreamUrl = `${window.location.origin}/hls/master.m3u8?_=${ts}`;

    // Best-effort: ask the service worker to drop any previously cached live content
    // so a stale segment from a prior pipeline session cannot leak into the new one.
    if ("serviceWorker" in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: "CLEAR_CACHES" });
    }

    if (typeof Hls !== "undefined" && Hls.isSupported()) {
      if (hls) {
        hls.destroy();
      }

      hls = new Hls({
        debug: false,
        enableWorker: true,
        lowLatencyMode: false,
        backBufferLength: 30,
        maxLoadingDelay: 3,
        maxBufferLength: 30,
        maxMaxBufferLength: 60,
        liveSyncMaxLatency: 10,
        liveDurationInfinity: true,
        // Disable CEA-708 caption parsing so embedded closed captions from the
        // MPEG-TS stream don't create native subtitle tracks. These would show
        // a CC button/label and "Spanish" in the player menu regardless of the
        // actual language. Our custom SubtitleRenderer handles subtitles instead.
        enableCEA708Captions: false,
      });

      // Subtitle renderer polls /subtitles/subs.m3u8 independently of
      // HLS.js — no native track management required.
      renderer = new SubtitleRenderer();
      renderer.start(video, container);

      // IMPORTANT: register handlers BEFORE loadSource/attachMedia.
      // HLS.js emits MANIFEST_PARSED synchronously after parsing the manifest
      // (which can happen very fast for a small playlist). If the handler is
      // registered after loadSource, the event is missed and the player stays
      // stuck on the "waiting" overlay forever.
      hls.on(HlsEvents.MANIFEST_PARSED, () => {
        if (waitingEl) waitingEl.style.display = "none";
        hideError();
        isConnected = true;
        retryCount = 0;
        video.play().catch(handlePlayError);

        updateSubtitleUI(0);
        startHealthCheck();
      });

      hls.on(HlsEvents.ERROR, (_event, data: unknown) => {
        const err = data as HlsErrorData;
        logger.warn("player", "HLS Error", err.type, err.fatal, err.details);

        if (err.fatal) {
          switch (err.type) {
            case HlsErrorTypes.NETWORK_ERROR: {
              // Exponential backoff: 2s, 4s, 8s, 16s, 30s max
              const delay = Math.min(
                BASE_RETRY_DELAY_MS * Math.pow(2, retryCount),
                MAX_RETRY_DELAY_MS,
              );
              retryCount++;
              showError(
                `Error de red - reconectando en ${Math.round(
                  delay / 1000,
                )}s...`,
              );
              setTimeout(() => {
                if (hls) hls.startLoad();
              }, delay);
              break;
            }
            case HlsErrorTypes.MEDIA_ERROR:
              hls?.recoverMediaError();
              break;
            default:
              showError("Error fatal - recargando...");
              setTimeout(connect, 3000);
              break;
          }
        }
      });

      hls.once(HlsEvents.FRAG_BUFFERED, () => {
        startHealthCheck();
        startNativeTrackSync();
      });

      hls.loadSource(freshStreamUrl);
      hls.attachMedia(video);
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = freshStreamUrl;
      video.addEventListener("loadedmetadata", () => {
        if (waitingEl) waitingEl.style.display = "none";
        isConnected = true;
        video.play().catch(handlePlayError);
        // Native HLS path: the browser handles <track> elements
        // attached to the <video>, but our hls.js path is the supported
        // one. For Safari we still want subtitles; rely on the
        // master.m3u8 SUBTITLES attribute being picked up by the
        // browser's native HLS implementation.
        startHealthCheck();
      });
      video.addEventListener("error", () => {
        if (isConnected) {
          showError("Stream perdido - reintentando...");
          setTimeout(connect, 3000);
        } else {
          showError("Error cargando el stream");
          stopHealthCheck();
        }
      });
    } else {
      showError("HLS no es soportado en este navegador");
    }
  }

  /** Monitor native text track mode changes from the "..." menu.
   *  When the user activates the native subtitle track, disable our
   *  SubtitleRenderer to avoid double-rendering. When deactivated, re-enable it. */
  function startNativeTrackSync(): void {
    stopNativeTrackSync();
    nativeTrackCheck = setInterval(() => {
      if (!video || !renderer) return;
      const tracks = video.textTracks;
      let nativeShowing = false;
      for (let i = 0; i < tracks.length; i++) {
        const t = tracks[i];
        if (
          (t.kind === "subtitles" || t.kind === "captions") &&
          t.mode === "showing"
        ) {
          nativeShowing = true;
          break;
        }
      }
      if (nativeShowing && subtitlesEnabled) {
        subtitlesEnabled = false;
        renderer.setEnabled(false);
        if (btnCC) btnCC.classList.remove("active");
      } else if (!nativeShowing && !subtitlesEnabled) {
        subtitlesEnabled = true;
        renderer.setEnabled(true);
        if (btnCC) btnCC.classList.add("active");
      }
    }, 1000);
  }

  function stopNativeTrackSync(): void {
    if (nativeTrackCheck) {
      clearInterval(nativeTrackCheck);
      nativeTrackCheck = null;
    }
  }

  function disconnect() {
    stopHealthCheck();
    stopNativeTrackSync();
    if (renderer) {
      renderer.stop();
      renderer = null;
    }
    if (hls) {
      hls.stopLoad();
      hls.destroy();
      hls = null;
    }
    isConnected = false;
  }

  if (btnRetry) {
    btnRetry.addEventListener("click", () => {
      disconnect();
      connect();
    });
  }

  function toggleSubtitles() {
    if (!renderer) return;
    subtitlesEnabled = !subtitlesEnabled;
    renderer.setEnabled(subtitlesEnabled);
    if (btnCC) btnCC.classList.toggle("active", subtitlesEnabled);
    logger.info(
      "player",
      "Subtitles",
      subtitlesEnabled ? "enabled" : "disabled",
    );
  }

  if (btnCC) {
    btnCC.addEventListener("click", toggleSubtitles);
  }

  function updateSubtitleUI(tracksCount: number) {
    if (!btnCC) return;
    if (tracksCount > 0) {
      btnCC.classList.add("visible");
      if (subtitlesEnabled) btnCC.classList.add("active");
      else btnCC.classList.remove("active");
    } else {
      btnCC.classList.remove("visible", "active");
    }
  }

  window.addEventListener("beforeunload", () => {
    disconnect();
  });

  function waitForHlsAndConnect(): void {
    const HLS_LOAD_TIMEOUT_MS = 10000;
    const startedAt = Date.now();

    function tryConnect(): void {
      if (typeof Hls !== "undefined") {
        connect();
        return;
      }
      if (Date.now() - startedAt > HLS_LOAD_TIMEOUT_MS) {
        logger.error(
          "player",
          `HLS.js no se cargo despues de ${HLS_LOAD_TIMEOUT_MS}ms. Revisa la conexion a cdn.jsdelivr.net.`,
        );
        showError(
          "No se pudo cargar la libreria HLS. Verifica la conexion a internet.",
        );
        return;
      }
      setTimeout(tryConnect, 100);
    }

    tryConnect();
  }

  // Wait for the new service worker (if any) to take control before starting
  // playback. Without this, the first page load after the SW is updated can
  // race with the old SW and replay stale cached segments.
  async function waitForServiceWorker(): Promise<void> {
    if (!("serviceWorker" in navigator)) return;
    try {
      const reg = await navigator.serviceWorker.ready;
      if (reg && reg.active) {
        logger.debug("player", "Service worker ready");
      }
    } catch (err) {
      logger.warn("player", "Service worker not ready, proceeding", err);
    }
  }

  void waitForServiceWorker().finally(() => waitForHlsAndConnect());
}
