/**
 * Módulo para el reproductor HLS con subtítulos dinámicos
 */

interface SubtitleCue {
  start: number;
  end: number;
  text: string;
}

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
  let hls: Hls | null = null;
  let subtitleInterval: number | null = null;
  let lastSubtitleContent = '';

  function showError(message: string) {
    if (errorOverlay) errorOverlay.style.display = 'flex';
    if (errorMessage) errorMessage.textContent = message;
    if (waitingEl) waitingEl.style.display = 'none';
  }

  function hideError() {
    if (errorOverlay) errorOverlay.style.display = 'none';
  }

  // Parse VTT content to extract cues
  function parseVTT(vttContent: string): SubtitleCue[] {
    const cues: SubtitleCue[] = [];
    const lines = vttContent.split('\n');
    const timeRegex = /(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})/;
    
    for (let i = 0; i < lines.length; i++) {
      const match = lines[i].match(timeRegex);
      if (match) {
        const start = parseInt(match[1]) * 3600 + parseInt(match[2]) * 60 + 
                     parseInt(match[3]) + parseInt(match[4]) / 1000;
        const end = parseInt(match[5]) * 3600 + parseInt(match[6]) * 60 + 
                   parseInt(match[7]) + parseInt(match[8]) / 1000;
        
        // Get text (next line(s) until empty line)
        let text = '';
        let j = i + 1;
        while (j < lines.length && lines[j].trim() !== '') {
          text += (text ? '\n' : '') + lines[j].trim();
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
      const response = await fetch(subtitlesUrl, { 
        cache: 'no-cache',
        headers: { 'Cache-Control': 'no-cache' }
      });
      
      if (!response.ok) {
        // 404 is expected when no subtitles exist yet
        if (response.status !== 404) {
          console.warn('Error loading subtitles:', response.status);
        }
        return;
      }
      
      const content = await response.text();
      
      // Only update if content changed
      if (content === lastSubtitleContent) return;
      lastSubtitleContent = content;
      
      const cues = parseVTT(content);
      
      if (!cues || cues.length === 0) {
        return; // No cues to display
      }
      
      // Get or create track
      let track: TextTrack | null = null;
      if (video.textTracks.length > 0) {
        track = video.textTracks[0];
      } else {
        track = video.addTextTrack('subtitles', 'Español', 'es');
        track.mode = 'showing';
      }
      
      // Clear existing cues
      if (track && track.cues) {
        const cuesToRemove = Array.from(track.cues);
        for (const cue of cuesToRemove) {
          track.removeCue(cue);
        }
      }
      
      // Add new cues
      if (track) {
        for (const cue of cues) {
          const vttCue = new VTTCue(cue.start, cue.end, cue.text);
          track.addCue(vttCue);
        }
      }
      
      console.log(`Loaded ${cues.length} subtitle cues`);
    } catch (error) {
      console.warn('Error loading subtitles:', error);
    }
  }

  // Start subtitle polling
  function startSubtitlePolling() {
    // Load immediately
    loadSubtitles();
    
    // Poll every 2 seconds
    subtitleInterval = window.setInterval(loadSubtitles, 2000);
  }

  // Stop subtitle polling
  function stopSubtitlePolling() {
    if (subtitleInterval !== null) {
      clearInterval(subtitleInterval);
      subtitleInterval = null;
    }
  }

  function connect() {
    hideError();
    if (waitingEl) waitingEl.style.display = 'block';

    if (typeof Hls !== 'undefined' && Hls.isSupported()) {
      hls = new Hls({
        debug: false,
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 90,
      });

      hls.loadSource(streamUrl);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        if (waitingEl) waitingEl.style.display = 'none';
        video.play().catch(console.error);
        // Start loading subtitles once video is ready
        startSubtitlePolling();
      });

      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          showError('Error de conexión con el stream');
          stopSubtitlePolling();
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              hls?.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              hls?.recoverMediaError();
              break;
            default:
              showError('Error fatal - recargando...');
              setTimeout(connect, 3000);
              break;
          }
        }
      });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = streamUrl;
      video.addEventListener('loadedmetadata', () => {
        if (waitingEl) waitingEl.style.display = 'none';
        video.play().catch(console.error);
        startSubtitlePolling();
      });
      video.addEventListener('error', () => {
        showError('Error cargando el stream');
        stopSubtitlePolling();
      });
    } else {
      showError('HLS no es soportado en este navegador');
    }
  }

  if (btnRetry) {
    btnRetry.addEventListener('click', () => {
      stopSubtitlePolling();
      lastSubtitleContent = '';
      if (hls) {
        hls.destroy();
        hls = null;
      }
      connect();
    });
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    stopSubtitlePolling();
  });

  // Wait for HLS library to be loaded before connecting
  function waitForHlsAndConnect(): void {
    // Check if HLS script has loaded
    if (typeof Hls === 'undefined') {
      console.log('Waiting for HLS library to load...');
      setTimeout(waitForHlsAndConnect, 100);
      return;
    }
    connect();
  }

  // Start connection after HLS is ready
  waitForHlsAndConnect();
}

declare global {
  interface Window {
    Hls: typeof Hls;
  }
}

interface Hls {
  new (config?: Partial<HlsConfig>): Hls;
  isSupported(): boolean;
  loadSource(url: string): void;
  attachMedia(media: HTMLMediaElement): void;
  startLoad(): void;
  recoverMediaError(): void;
  destroy(): void;
  on(event: string, callback: (...args: any[]) => void): void;
}

interface HlsConfig {
  debug: boolean;
  enableWorker: boolean;
  lowLatencyMode: boolean;
  backBufferLength: number;
}