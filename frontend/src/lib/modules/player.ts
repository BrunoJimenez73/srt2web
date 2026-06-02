/**
 * Módulo para el reproductor HLS con subtítulos dinámicos
 */

import { logger } from "../utils/logger";

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

interface SubtitleCue {
  start: number;
  end: number;
  text: string;
}

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
  const subtitlesUrl = `${window.location.origin}/subtitles/subs.vtt?_=${_sessionTs}`;
  let hls: HlsInstance | null = null;
  let subtitleInterval: ReturnType<typeof setInterval> | null = null;
  let lastSubtitleContent = "";
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

  // Parse VTT content to extract cues
  function parseVTT(vttContent: string): SubtitleCue[] {
    const cues: SubtitleCue[] = [];
    const lines = vttContent.split("\n");
    // Support both VTT (dot) and SRT (comma) timestamps
    const timeRegex =
      /(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})/;

    for (let i = 0; i < lines.length; i++) {
      const match = lines[i].match(timeRegex);
      if (match) {
        const start =
          parseInt(match[1]) * 3600 +
          parseInt(match[2]) * 60 +
          parseInt(match[3]) +
          parseInt(match[4]) / 1000;
        const end =
          parseInt(match[5]) * 3600 +
          parseInt(match[6]) * 60 +
          parseInt(match[7]) +
          parseInt(match[8]) / 1000;

        let text = "";
        let j = i + 1;
        while (j < lines.length && lines[j].trim() !== "") {
          text += (text ? "\n" : "") + lines[j].trim();
          j++;
        }

        if (text) {
          cues.push({ start, end, text });
        }
      }
    }

    return cues;
  }

  // Load and display subtitles
  async function loadSubtitles() {
    try {
      const ts = Date.now();
      const response = await fetch(
        `${window.location.origin}/subtitles/subs.vtt?_=${ts}`,
        {
          cache: "no-cache",
          headers: { "Cache-Control": "no-cache" },
        },
      );

      if (!response.ok) {
        if (response.status !== 404) {
          logger.warn("player", "Error loading subtitles", response.status);
        }
        return;
      }

      const content = await response.text();

      if (content === lastSubtitleContent) return;
      lastSubtitleContent = content;

      const cues = parseVTT(content);

      if (!cues || cues.length === 0) return;

      let track: TextTrack | null = null;
      if (video.textTracks.length > 0) {
        track = video.textTracks[0];
      } else {
        track = video.addTextTrack("subtitles", "Español", "es");
      }
      if (track) track.mode = "showing";

      if (track && track.cues) {
        const cuesToRemove = Array.from(track.cues);
        for (const cue of cuesToRemove) {
          track.removeCue(cue);
        }
      }

      if (track) {
        for (const cue of cues) {
          const vttCue = new VTTCue(cue.start, cue.end, cue.text);
          track.addCue(vttCue);
        }
      }
    } catch (error) {
      logger.warn("player", "Error loading subtitles", error);
    }
  }

  function startSubtitlePolling() {
    loadSubtitles();
    subtitleInterval = setInterval(loadSubtitles, 2000);
  }

  function stopSubtitlePolling() {
    if (subtitleInterval) {
      clearInterval(subtitleInterval);
      subtitleInterval = null;
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
    lastSubtitleContent = "";

    // Update cache buster for fresh session
    const ts = Date.now();
    const freshStreamUrl = `${window.location.origin}/hls/stream.m3u8?_=${ts}`;
    const freshSubtitlesUrl = `${window.location.origin}/subtitles/subs.vtt?_=${ts}`;

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
        startSubtitlePolling();
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
        startSubtitlePolling();
        startHealthCheck();
      });
      video.addEventListener("error", () => {
        if (isConnected) {
          showError("Stream perdido - reintentando...");
          setTimeout(connect, 3000);
        } else {
          showError("Error cargando el stream");
          stopSubtitlePolling();
          stopHealthCheck();
        }
      });
    } else {
      showError("HLS no es soportado en este navegador");
    }
  }

  function disconnect() {
    stopSubtitlePolling();
    stopHealthCheck();
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
      lastSubtitleContent = "";
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
      // Best-effort: ensure the active SW is the latest one we just registered.
      // If the controller is still null after a short wait, proceed anyway —
      // some browsers (e.g. in dev / no HTTPS) never expose a controller.
      if (reg && reg.active) {
        logger.debug("player", "Service worker ready");
      }
    } catch (err) {
      logger.warn("player", "Service worker not ready, proceeding", err);
    }
  }

  void waitForServiceWorker().finally(() => waitForHlsAndConnect());
}
