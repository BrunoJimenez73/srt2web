/**
 * Módulo para el reproductor HLS con subtítulos dinámicos
 */

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
  attachMedia(media: HTMLMediaElement): void;
  startLoad(): void;
  stopLoad(): void;
  recoverMediaError(): void;
  destroy(): void;
  on(event: string, callback: (...args: any[]) => void): void;
  once(event: string, callback: (...args: any[]) => void): void;
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
  MANIFEST_PARSED: 'hlsManifestParsed',
  ERROR: 'hlsError',
  FRAG_BUFFERED: 'hlsFragBuffered',
  LEVEL_SWITCH: 'hlsLevelSwitch',
  FRAG_LOADED: 'hlsFragLoaded',
  FRAG_LOADED_APPENDING: 'hlsFragLoadedAppending',
};

// HLS Error Types enum
const HlsErrorTypes = {
  NETWORK_ERROR: 'networkError',
  MEDIA_ERROR: 'mediaError',
};

interface SubtitleCue {
  start: number;
  end: number;
  text: string;
  chunkStart: number;  // When this chunk started in absolute time
}

// Health check state
let healthCheckInterval: ReturnType<typeof setInterval> | null = null;
let consecutiveErrors = 0;
let initialLoadAttempts = 0;
let hasShownWaiting = false;
let lastFragmentTime = 0;
const INITIAL_LOAD_TIMEOUT = 30000; // 30 seconds to wait for first chunk
const MAX_CONSECUTIVE_ERRORS = 10; // More tolerant
const FRAGMENT_TIMEOUT = 30000; // 30s timeout for fragments (with 4s segments + buffer)

export function initHlsPlayer(): void {
  const video = document.getElementById('video-player') as HTMLVideoElement;
  const waitingEl = document.getElementById('waiting');
  const errorOverlay = document.getElementById('error-overlay');
  const errorMessage = document.getElementById('error-message');
  const btnRetry = document.getElementById('btn-retry');

  if (!video) {
    console.error('Video element not found');
    return;
  }

  const streamUrl = `${window.location.origin}/hls/stream.m3u8`;
  const subtitlesUrl = `${window.location.origin}/subtitles/subs.vtt`;
  let hls: HlsInstance | null = null;
  let subtitleInterval: ReturnType<typeof setInterval> | null = null;
  let lastSubtitleContent = '';
  let isConnected = false;
  let lastManifestTime = 0;

  function showError(message: string, showRetry = true) {
    if (errorOverlay) errorOverlay.style.display = 'flex';
    if (errorMessage) errorMessage.textContent = message;
    if (waitingEl) waitingEl.style.display = 'none';
    if (btnRetry) btnRetry.style.display = showRetry ? 'block' : 'none';
    isConnected = false;
  }

  function hideError() {
    if (errorOverlay) errorOverlay.style.display = 'none';
    if (btnRetry) btnRetry.style.display = 'none';
  }

  // Health check - monitor stream availability
  function startHealthCheck() {
    stopHealthCheck();
    consecutiveErrors = 0;
    
    healthCheckInterval = setInterval(async () => {
      const now = Date.now();
      
      // Check for fragment stall (no new fragment in FRAGMENT_TIMEOUT ms)
      if (isConnected && lastFragmentTime > 0 && (now - lastFragmentTime) > FRAGMENT_TIMEOUT) {
        console.warn('[Health] Fragment stall detected, last fragment was', (now - lastFragmentTime) / 1000, 'seconds ago');
        consecutiveErrors++;
        lastFragmentTime = now; // Reset to avoid spam
        
        if (consecutiveErrors >= 3) {
          console.log('[Health] Multiple stalls, attempting stream recovery...');
          try {
            hls?.startLoad();
          } catch (e) {
            console.error('[Health] Failed to restart load:', e);
          }
          consecutiveErrors = 0;
        }
      }
      
      try {
        const response = await fetch(streamUrl, { method: 'HEAD', cache: 'no-cache' });
        
        if (response.ok) {
          consecutiveErrors = 0;
          if (!isConnected && hls) {
            // Stream is back, try to recover
            console.log('[Health] Stream recovered, attempting reconnect...');
            hls.startLoad();
          }
        } else {
          consecutiveErrors++;
          console.warn('[Health] Stream not available:', response.status, 'Errors:', consecutiveErrors);
        }
      } catch {
        consecutiveErrors++;
        console.warn('[Health] Stream check failed, Errors:', consecutiveErrors);
      }
      
      // If too many consecutive errors, show reconnect option
      if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS && hls) {
        showError('Stream no disponible. Haz clic en Reintentar para conectar.');
        consecutiveErrors = 0;
      }
    }, 5000); // Check every 5 seconds for better responsiveness
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
    const lines = vttContent.split('\n');
    const timeRegex = /(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})/;
    const chunkStartRegex = /chunk_start:\s*([\d.]+)/;
    
    let currentChunkStart = 0;
    
    for (let i = 0; i < lines.length; i++) {
      // Check for chunk_start NOTE
      const chunkMatch = lines[i].match(chunkStartRegex);
      if (chunkMatch) {
        currentChunkStart = parseFloat(chunkMatch[1]);
        continue;
      }
      
      const match = lines[i].match(timeRegex);
      if (match) {
        // Relative timestamps from VTT
        const relStart = parseInt(match[1]) * 3600 + parseInt(match[2]) * 60 + 
                     parseInt(match[3]) + parseInt(match[4]) / 1000;
        const relEnd = parseInt(match[5]) * 3600 + parseInt(match[6]) * 60 + 
                   parseInt(match[7]) + parseInt(match[8]) / 1000;
        
        let text = '';
        let j = i + 1;
        while (j < lines.length && lines[j].trim() !== '') {
          // Skip NOTE lines in text
          if (!lines[j].startsWith('NOTE')) {
            text += (text ? '\n' : '') + lines[j].trim();
          }
          j++;
        }
        
        if (text && currentChunkStart > 0) {
          // Store relative time + chunk start for dynamic offset calculation
          cues.push({ 
            start: relStart, 
            end: relEnd, 
            text: text,
            chunkStart: currentChunkStart 
          });
        }
      }
    }
    
    return cues;
  }

  // Load and display subtitles
  async function loadSubtitles() {
    try {
      const response = await fetch(subtitlesUrl, { 
        cache: 'no-cache',
        headers: { 'Cache-Control': 'no-cache' }
      });
      
      if (!response.ok) {
        if (response.status !== 404) {
          console.warn('Error loading subtitles:', response.status);
        }
        return;
      }
      
      const content = await response.text();
      
      // Don't skip if content looks similar - always parse and update
      // This ensures we catch all changes from the rolling window
      if (!content || content.length < 10) return;
      
      // Check if we have new content by comparing cue count
      const cues = parseVTT(content);
      
      if (!cues || cues.length === 0) {
        // Clear existing track if no cues available
        if (video.textTracks.length > 0) {
          const track = video.textTracks[0];
          if (track.cues) {
            const cuesToRemove = Array.from(track.cues);
            for (const cue of cuesToRemove) {
              track.removeCue(cue);
            }
          }
        }
        return;
      }
      
      // Get current video time for dynamic offset calculation
      const videoTime = video.currentTime;
      
      let track: TextTrack | null = null;
      if (video.textTracks.length > 0) {
        track = video.textTracks[0];
      } else {
        track = video.addTextTrack('subtitles', 'Español', 'es');
        track.mode = 'showing';
      }
      
      if (track && track.cues) {
        const cuesToRemove = Array.from(track.cues);
        for (const cue of cuesToRemove) {
          track.removeCue(cue);
        }
      }
      
      if (track) {
        for (const cue of cues) {
          // VTT has relative timestamp times (0-based within each chunk)
          // Just use them directly - HLS player handles the sync
          const startTime = cue.start;
          const endTime = cue.end;
          
          // Only add cues that should be visible now
          // Use simplified range check
          if (endTime >= videoTime - 5 && startTime <= videoTime + 60) {
            const vttCue = new VTTCue(startTime, endTime, cue.text);
            track.addCue(vttCue);
          }
        }
      }
      
      // Update last content to avoid duplicate logs
      lastSubtitleContent = content.substring(0, 500);
      console.log(`Loaded ${cues.length} subtitle cues`);
    } catch (error) {
      console.warn('Error loading subtitles:', error);
    }
  }

  function startSubtitlePolling() {
    loadSubtitles();
    subtitleInterval = setInterval(loadSubtitles, 1000); // Poll every 1s for faster updates
    // Also poll for input state to pause/resume video
    startInputStatePolling();
  }

  function stopSubtitlePolling() {
    if (subtitleInterval) {
      clearInterval(subtitleInterval);
      subtitleInterval = null;
    }
    stopInputStatePolling();
  }

  // Poll input state to pause/resume video when user pauses input
  let inputStateInterval: ReturnType<typeof setInterval> | null = null;
  let lastInputPaused = false;

  async function checkInputState() {
    try {
      const response = await fetch(`${window.location.origin}/api/input-info`, {
        headers: { 'Accept': 'application/json' }
      });
      if (!response.ok) return;
      const data = await response.json();
      
      if (data.type === 'file') {
        const isPaused = data.is_paused === true;
        
        // If input paused state changed, update video
        if (isPaused !== lastInputPaused) {
          lastInputPaused = isPaused;
          if (isPaused && !video.paused) {
            console.log('[Player] Input paused - pausing video');
            video.pause();
          } else if (!isPaused && video.paused) {
            console.log('[Player] Input resumed - resuming video');
            video.play().catch(console.error);
          }
        }
      }
    } catch {
      // Ignore errors
    }
  }

  function startInputStatePolling() {
    checkInputState(); // Check immediately
    inputStateInterval = setInterval(checkInputState, 1000);
  }

  function stopInputStatePolling() {
    if (inputStateInterval) {
      clearInterval(inputStateInterval);
      inputStateInterval = null;
    }
  }

  function connect() {
    hideError();
    if (waitingEl) {
      waitingEl.style.display = 'block';
      waitingEl.textContent = 'Esperando stream...';
    }
    isConnected = false;
    consecutiveErrors = 0;
    initialLoadAttempts = 0;

    // If we already showed waiting, don't show error immediately
    hasShownWaiting = false;

    if (typeof Hls !== 'undefined' && Hls.isSupported()) {
      if (hls) {
        hls.destroy();
      }
      
      hls = new Hls({
        debug: false,
        enableWorker: true,
        lowLatencyMode: false, // Disable low latency for smoother playback
        backBufferLength: 60, // 60s buffer
        maxLoadingDelay: 8, // Allow up to 8s delay for segments
        maxBufferLength: 30, // 30s buffer before pausing load
        maxMaxBufferLength: 60, // Max 60s buffer
        liveSyncMaxLatency: 10, // Allow up to 10s latency
        liveDurationInfinity: true,
      });

      hls.loadSource(streamUrl);
      hls.attachMedia(video);

      hls.on(HlsEvents.MANIFEST_PARSED, () => {
        if (waitingEl) waitingEl.style.display = 'none';
        hasShownWaiting = true;
        isConnected = true;
        lastManifestTime = Date.now();
        lastFragmentTime = Date.now();
        // Don't autoplay - user controls playback
        startSubtitlePolling();
        startHealthCheck();
      });

      // Track fragment loading to detect stalls
      hls.on(HlsEvents.FRAG_LOADED, () => {
        lastFragmentTime = Date.now();
        consecutiveErrors = 0; // Reset errors on successful fragment
      });

      hls.on(HlsEvents.FRAG_LOADED_APPENDING, () => {
        lastFragmentTime = Date.now();
      });

      hls.on(HlsEvents.ERROR, (_event, data) => {
        console.warn('[HLS Error]', data.type, data.fatal, data.details);
        
        // Don't show error immediately - just retry
        if (data.fatal) {
          switch (data.type) {
            case HlsErrorTypes.NETWORK_ERROR:
              if (isConnected) {
                // Was connected, lost stream - reconnect attempt
                console.log('[HLS] Lost stream, attempting reconnect...');
                hls?.startLoad();
              } else {
                // First connect - show waiting, not error
                if (waitingEl) {
                  waitingEl.textContent = 'Esperando stream...';
                  waitingEl.style.display = 'block';
                }
                // Auto-retry without showing error
                initialLoadAttempts++;
                if (initialLoadAttempts > 3) {
                  showError('No se puede conectar al stream. Haz clic en Reintentar.');
                } else {
                  setTimeout(() => hls?.startLoad(), 2000);
                }
              }
              break;
            case HlsErrorTypes.MEDIA_ERROR:
              hls?.recoverMediaError();
              break;
            default:
              showError('Error fatal - recargando...');
              setTimeout(connect, 3000);
              break;
          }
        }
      });

      hls.once(HlsEvents.FRAG_BUFFERED, () => {
        console.log('[HLS] First fragment buffered');
        startHealthCheck();
      });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = streamUrl;
      video.addEventListener('loadedmetadata', () => {
        if (waitingEl) waitingEl.style.display = 'none';
        isConnected = true;
        video.play().catch(console.error);
        startSubtitlePolling();
        startHealthCheck();
      });
      video.addEventListener('error', () => {
        if (isConnected) {
          showError('Stream perdido - reintentando...');
          setTimeout(connect, 3000);
        } else {
          showError('Error cargando el stream');
          stopSubtitlePolling();
          stopHealthCheck();
        }
      });
    } else {
      showError('HLS no es soportado en este navegador');
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
    btnRetry.addEventListener('click', () => {
      disconnect();
      lastSubtitleContent = '';
      connect();
    });
  }

  window.addEventListener('beforeunload', () => {
    disconnect();
  });

  function waitForHlsAndConnect(): void {
    if (typeof Hls === 'undefined') {
      console.log('Waiting for HLS library to load...');
      setTimeout(waitForHlsAndConnect, 100);
      return;
    }
    connect();
  }

  waitForHlsAndConnect();
}

