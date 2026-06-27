import { logger } from "../utils/logger";
import {
  activateFirstSubtitleTrack,
  forceSubtitleTrackMode,
} from "./player-subtitles";
import {
  connectFeedbackWs,
  disconnectFeedbackWs,
  sendBufferHealth,
  sendStalled,
  sendBandwidth,
} from "./player-feedback";

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
  off(event: string, callback: (...args: unknown[]) => void): void;
  subtitleTrack: number;
  subtitleDisplay: boolean;
  subtitleTracks: ReadonlyArray<{
    id: number;
    name?: string;
    lang?: string;
    type?: string;
  }>;
  allSubtitleTracks?: ReadonlyArray<{
    id: number;
    name?: string;
    lang?: string;
    type?: string;
  }>;
  levels?: ReadonlyArray<{
    bitrate: number;
    width: number;
    height: number;
  }>;
  currentLevel?: number;
  bandwidthEstimate?: number;
}

interface HlsConfig {
  debug: boolean;
  enableWorker: boolean;
  lowLatencyMode: boolean;
  autoStartLoad: boolean;
  backBufferLength: number;
  maxLoadingDelay: number;
  maxBufferLength: number;
  maxMaxBufferLength: number;
  liveSyncMaxLatency: number;
  liveSyncDuration: number;
  liveDurationInfinity: boolean;
  highBufferWatchdogPeriod: number;
  enableCEA708Captions: boolean;
  fragLoadingTimeOut: number;
  manifestLoadingTimeOut: number;
  levelLoadingTimeOut: number;
  fragLoadingMaxRetry: number;
  manifestLoadingMaxRetry: number;
  levelLoadingMaxRetry: number;
}

const HlsEvents = {
  MANIFEST_PARSED: "hlsManifestParsed",
  ERROR: "hlsError",
  FRAG_BUFFERED: "hlsFragBuffered",
  SUBTITLE_TRACKS_UPDATED: "hlsSubtitleTracksUpdated",
  SUBTITLE_TRACK_LOADED: "hlsSubtitleTrackLoaded",
  STALLED: "hlsStalled",
  LEVEL_UPDATED: "hlsLevelUpdated",
  BUFFER_APPENDED: "hlsBufferAppended",
};

const HlsErrorTypes = {
  NETWORK_ERROR: "networkError",
  MEDIA_ERROR: "mediaError",
};

interface HlsErrorData {
  type: string;
  fatal: boolean;
  details: string;
}

interface HlsLevelUpdatedData {
  level: number;
  details?: {
    bitrate?: number;
    totalduration?: number;
  };
}

let healthCheckInterval: ReturnType<typeof setInterval> | null = null;
let subtitleWatchdog: ReturnType<typeof setInterval> | null = null;
let consecutiveErrors = 0;
const MAX_CONSECUTIVE_ERRORS = 5;

let _hasStartedOnce = false;

let retryCount = 0;
const MAX_RETRY_DELAY_MS = 30000;
const BASE_RETRY_DELAY_MS = 2000;

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

  const _sessionTs = Date.now();
  const streamUrl = `${window.location.origin}/hls/master.m3u8?_=${_sessionTs}`;
  let hls: HlsInstance | null = null;
  let isConnected = false;

  function showError(message: string) {
    if (errorOverlay) errorOverlay.style.display = "flex";
    if (errorMessage) errorMessage.textContent = message;
    if (waitingEl) waitingEl.style.display = "none";
    isConnected = false;
  }

  function hideError() {
    if (errorOverlay) errorOverlay.style.display = "none";
  }

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
          if (_hasStartedOnce && !isConnected && hls) {
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

      if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS && hls) {
        stopHealthCheck();
        showError(
          "Stream no disponible. Haz clic en Reintentar para conectar.",
        );
      }
    }, 10000);
  }

  function stopHealthCheck() {
    if (healthCheckInterval) {
      clearInterval(healthCheckInterval);
      healthCheckInterval = null;
    }
  }

  function waitForSegments(attempt: number): void {
    const MAX_ATTEMPTS = 15;

    void (async () => {
      try {
        const segUrl = `${
          window.location.origin
        }/hls/stream.m3u8?_=${Date.now()}`;
        const resp = await fetch(segUrl, { cache: "no-cache" });
        if (!resp.ok) {
          if (attempt < MAX_ATTEMPTS) {
            setTimeout(() => waitForSegments(attempt + 1), 2000);
          }
          return;
        }
        const text = await resp.text();
        if (text.includes("#EXTINF") && hls) {
          _hasStartedOnce = true;
          hls.startLoad();
          startHealthCheck();
          return;
        }
      } catch {
        // connection not ready yet
      }
      if (attempt < MAX_ATTEMPTS) {
        setTimeout(() => waitForSegments(attempt + 1), 2000);
      }
    })();
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

    connectFeedbackWs();

    const ts = Date.now();
    const freshStreamUrl = `${window.location.origin}/hls/master.m3u8?_=${ts}`;

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
        autoStartLoad: false,
        backBufferLength: 45,
        maxLoadingDelay: 8,
        maxBufferLength: 120,
        maxMaxBufferLength: 240,
        liveSyncMaxLatency: 30,
        liveSyncDuration: 25,
        liveDurationInfinity: true,
        highBufferWatchdogPeriod: 2,
        enableCEA708Captions: false,
        fragLoadingTimeOut: 20000,
        manifestLoadingTimeOut: 20000,
        levelLoadingTimeOut: 20000,
        fragLoadingMaxRetry: 6,
        manifestLoadingMaxRetry: 6,
        levelLoadingMaxRetry: 6,
      });

      hls.on(HlsEvents.MANIFEST_PARSED, () => {
        hideError();
        retryCount = 0;

        if (hls) {
          activateFirstSubtitleTrack(hls, {
            preferredLang: "es",
            showSubtitles: true,
            video,
          });
        }

        waitForSegments(0);
      });

      hls.on(HlsEvents.SUBTITLE_TRACKS_UPDATED, () => {
        if (hls) {
          activateFirstSubtitleTrack(hls, {
            preferredLang: "es",
            showSubtitles: true,
            video,
          });
        }
      });

      hls.on(HlsEvents.FRAG_BUFFERED, () => {
        if (!isConnected) {
          isConnected = true;
          if (waitingEl) waitingEl.style.display = "none";
          video.play().catch(handlePlayError);
          startSubtitleWatchdog();
        }
      });

      hls.on(HlsEvents.BUFFER_APPENDED, () => {
        try {
          const bufLen = video.buffered.length;
          let maxBuffered = 0;
          for (let i = 0; i < bufLen; i++) {
            const end = video.buffered.end(i);
            if (end > maxBuffered) maxBuffered = end;
          }
          const targetBuf = hls?.levels?.[0]?.bitrate ? 12000 : 12000;
          sendBufferHealth(maxBuffered * 1000, targetBuf);
        } catch {
          // ignore
        }
      });

      hls.on(HlsEvents.STALLED, () => {
        sendStalled(100);
      });

      hls.on(HlsEvents.LEVEL_UPDATED, (_event, data: unknown) => {
        const d = data as HlsLevelUpdatedData;
        if (d.details?.bitrate) {
          sendBandwidth(d.details.bitrate);
        }
      });

      hls.on(HlsEvents.ERROR, (_event, data: unknown) => {
        const err = data as HlsErrorData;
        logger.warn("player", "HLS Error", err.type, err.fatal, err.details);

        if (err.fatal) {
          switch (err.type) {
            case HlsErrorTypes.NETWORK_ERROR: {
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

      hls.loadSource(freshStreamUrl);
      hls.attachMedia(video);
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = freshStreamUrl;
      video.addEventListener("loadedmetadata", () => {
        if (waitingEl) waitingEl.style.display = "none";
        isConnected = true;
        video.play().catch(handlePlayError);
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

  function startSubtitleWatchdog() {
    stopSubtitleWatchdog();
    subtitleWatchdog = setInterval(() => {
      if (video && isConnected) {
        forceSubtitleTrackMode(video);
      }
    }, 3000);
  }

  function stopSubtitleWatchdog() {
    if (subtitleWatchdog) {
      clearInterval(subtitleWatchdog);
      subtitleWatchdog = null;
    }
  }

  function disconnect() {
    stopHealthCheck();
    stopSubtitleWatchdog();
    disconnectFeedbackWs();
    if (hls) {
      hls.stopLoad();
      hls.destroy();
      hls = null;
    }
    isConnected = false;
    _hasStartedOnce = false;
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
