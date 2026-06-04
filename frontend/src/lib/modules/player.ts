/**
 * Módulo para el reproductor HLS con subtítulos nativos.
 *
 * F108: Subtitles are loaded natively by HLS.js via the subtitle media
 * playlist declared in the video master playlist
 * (`EXT-X-MEDIA:TYPE=SUBTITLES,URI="/subtitles/subs.m3u8"`). The
 * `player-subtitles.ts` helper activates the first track after
 * MANIFEST_PARSED. There is no polling and no manual VTTCue management
 * here anymore — hls.js handles the per-chunk fragment download, the
 * VTTCue parsing, and the timing relative to `currentTime`.
 */

import { logger } from "../utils/logger";
import {
  activateFirstSubtitleTrack,
  disableSubtitles,
  onSubtitleTrackListChange,
} from "./player-subtitles";
import type { HlsLike } from "./player-subtitles";

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
  subtitleTrack: number;
  subtitleDisplay: boolean;
  subtitleTracks: ReadonlyArray<{
    id: number;
    name?: string;
    lang?: string;
    type?: string;
  }>;
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
}

// HLS Events enum
const HlsEvents = {
  MANIFEST_PARSED: "hlsManifestParsed",
  ERROR: "hlsError",
  FRAG_BUFFERED: "hlsFragBuffered",
  LEVEL_SWITCH: "hlsLevelSwitch",
  SUBTITLE_TRACKS_UPDATED: "hlsSubtitleTracksUpdated",
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

export function initHlsPlayer(): void {
  const video = document.getElementById("video-player") as HTMLVideoElement;
  const waitingEl = document.getElementById("waiting");
  const errorOverlay = document.getElementById("error-overlay");
  const errorMessage = document.getElementById("error-message");
  const btnRetry = document.getElementById("btn-retry");

  if (!video) {
    logger.error("player", "Video element not found");
    return;
  }

  // Cache buster to prevent loading stale HLS segments from previous sessions
  const _sessionTs = Date.now();
  const streamUrl = `${window.location.origin}/hls/stream.m3u8?_=${_sessionTs}`;
  let hls: HlsInstance | null = null;
  let unsubscribeSubtitleUpdates: (() => void) | null = null;
  let isConnected = false;
  let lastManifestTime = 0;

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

      // If too many consecutive errors, show reconnect option
      if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS && hls) {
        showError(
          "Stream no disponible. Haz clic en Reintentar para conectar.",
        );
        consecutiveErrors = 0;
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

    // Update cache buster for fresh session
    const ts = Date.now();
    const freshStreamUrl = `${window.location.origin}/hls/stream.m3u8?_=${ts}`;

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
      });

      // Subscribe to subtitle track updates so we re-activate when the
      // manifest is re-parsed (e.g. after a reconnect). The unsubscribe
      // function is stored and called on disconnect so we don't leak.
      unsubscribeSubtitleUpdates = onSubtitleTrackListChange(
        hls as unknown as HlsLike,
        (tracks) => {
          logger.debug(
            "player",
            "Subtitle tracks updated",
            tracks.length,
            tracks.map((t) => t.lang ?? "?").join(","),
          );
          // Re-activate the first track after each list refresh so the
          // user doesn't end up with no subtitles if the manifest is
          // re-parsed mid-session.
          activateFirstSubtitleTrack(hls as unknown as HlsLike, {
            preferredLang: "es",
            showSubtitles: true,
          });
        },
      );

      // IMPORTANT: register handlers BEFORE loadSource/attachMedia.
      // HLS.js emits MANIFEST_PARSED synchronously after parsing the manifest
      // (which can happen very fast for a small playlist). If the handler is
      // registered after loadSource, the event is missed and the player stays
      // stuck on the "waiting" overlay forever.
      hls.on(HlsEvents.MANIFEST_PARSED, () => {
        if (waitingEl) waitingEl.style.display = "none";
        isConnected = true;
        lastManifestTime = Date.now();
        video.play().catch(handlePlayError);

        // F108: activate the first subtitle track declared in the
        // master playlist. HLS.js will load subs.m3u8 natively, parse
        // per-chunk fragments, and render cues at the right currentTime.
        const trackId = activateFirstSubtitleTrack(hls as unknown as HlsLike, {
          preferredLang: "es",
          showSubtitles: true,
        });
        logger.info("player", "Subtitle track activation result", trackId);

        startHealthCheck();
      });

      hls.on(HlsEvents.ERROR, (_event, data: unknown) => {
        const err = data as HlsErrorData;
        logger.warn("player", "HLS Error", err.type, err.fatal, err.details);

        if (err.fatal) {
          switch (err.type) {
            case HlsErrorTypes.NETWORK_ERROR:
              showError("Error de red - intentando reconectar...");
              hls?.startLoad();
              break;
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

  function disconnect() {
    stopHealthCheck();
    if (unsubscribeSubtitleUpdates) {
      unsubscribeSubtitleUpdates();
      unsubscribeSubtitleUpdates = null;
    }
    if (hls) {
      disableSubtitles(hls as unknown as HlsLike);
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
