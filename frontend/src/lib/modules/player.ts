/**
 * Módulo para el reproductor HLS
 * Maneja la reproducción de video vía HLS.js
 */

import Hls from 'hls.js';

export interface PlayerConfig {
  videoElement: HTMLVideoElement;
  streamUrl: string;
  autoPlay?: boolean;
  onError?: (error: Error) => void;
  onReady?: () => void;
}

/**
 * Inicializa el reproductor HLS
 */
export function initPlayer(config: PlayerConfig): Hls | null {
  const { videoElement, streamUrl, autoPlay = true, onError, onReady } = config;
  
  let hls: Hls | null = null;
  
  if (Hls.isSupported()) {
    hls = new Hls({
      debug: false,
      enableWorker: true,
      lowLatencyMode: true,
      backBufferLength: 90,
    });
    
    hls.loadSource(streamUrl);
    hls.attachMedia(videoElement);
    
    hls.on(Hls.Events.MANIFEST_PARSED, () => {
      console.log('✅ HLS manifest loaded');
      if (onReady) onReady();
      if (autoPlay) {
        videoElement.play().catch(err => {
          console.warn('Auto-play prevented:', err);
        });
      }
    });
    
    hls.on(Hls.Events.ERROR, (event, data) => {
      console.error('HLS error:', data);
      
      if (data.fatal) {
        switch (data.type) {
          case Hls.ErrorTypes.NETWORK_ERROR:
            console.error('Network error, trying to recover...');
            hls?.startLoad();
            break;
          case Hls.ErrorTypes.MEDIA_ERROR:
            console.error('Media error, trying to recover...');
            hls?.recoverMediaError();
            break;
          default:
            console.error('Fatal error, cannot recover');
            if (onError) {
              onError(new Error(`HLS fatal error: ${data.type}`));
            }
            break;
        }
      }
    });
    
  } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
    // Native HLS support (Safari)
    videoElement.src = streamUrl;
    videoElement.addEventListener('loadedmetadata', () => {
      console.log('✅ Native HLS loaded');
      if (onReady) onReady();
      if (autoPlay) {
        videoElement.play().catch(err => {
          console.warn('Auto-play prevented:', err);
        });
      }
    });
  } else {
    const error = new Error('HLS is not supported in this browser');
    console.error(error);
    if (onError) onError(error);
    return null;
  }
  
  return hls;
}

/**
 * Destruye el reproductor HLS
 */
export function destroyPlayer(hls: Hls | null): void {
  if (hls) {
    hls.destroy();
  }
}

/**
 * Alias for initPlayer - compatibility with player.astro
 */
export function initHlsPlayer(config: PlayerConfig): Hls | null {
  return initPlayer(config);
}
