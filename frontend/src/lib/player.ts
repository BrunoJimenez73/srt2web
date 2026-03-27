declare const Hls: typeof import('hls.js');
import { PLAYER_CONFIG } from './constants';

let hls: InstanceType<typeof Hls> | null = null;
let userPreference: boolean | null = null;
let subtitleTrackElement: HTMLTrackElement | null = null;
let subtitleLanguageName = '';
let lastVTTContent = '';
let playerInitialized = false;

const video = document.getElementById('video-player') as HTMLVideoElement;
const waiting = document.getElementById('waiting') as HTMLDivElement;

export async function loadVTT(): Promise<void> {
    try {
        const response = await fetch(`/hls/subs.vtt?_=${Date.now()}`);
        if (!response.ok) return;

        const vttContent = await response.text();

        if (lastVTTContent === vttContent) return;
        lastVTTContent = vttContent;

        const vttBlob = new Blob([vttContent], { type: 'text/vtt; charset=utf-8' });
        const vttUrl = URL.createObjectURL(vttBlob);

        if (subtitleTrackElement) {
            const oldSrc = subtitleTrackElement.src;
            subtitleTrackElement.src = vttUrl;

            if (!document.contains(subtitleTrackElement)) {
                video.appendChild(subtitleTrackElement);
            }

            if (oldSrc && oldSrc.startsWith('blob:')) {
                URL.revokeObjectURL(oldSrc);
            }
        } else {
            subtitleTrackElement = document.createElement('track');
            subtitleTrackElement.kind = 'subtitles';
            subtitleTrackElement.label = subtitleLanguageName || 'Spanish';
            subtitleTrackElement.srclang = 'es';
            subtitleTrackElement.src = vttUrl;
            subtitleTrackElement.default = true;

            video.appendChild(subtitleTrackElement);

            subtitleTrackElement.addEventListener('load', () => {
                const shouldShow = userPreference !== null ? userPreference : true;

                if (shouldShow) {
                    for (let i = 0; i < video.textTracks.length; i++) {
                        if (video.textTracks[i].kind === 'subtitles') {
                            video.textTracks[i].mode = (i === 0) ? 'showing' : 'disabled';
                        }
                    }
                }
            });
        }

    } catch(e) {
        // Silent fail for VTT loading
    }
}

export function destroyPlayer(): void {
    if (hls) {
        try {
            hls.destroy();
        } catch(e) {
            // Silent fail on destroy
        }
        hls = null;
    }
    playerInitialized = false;
}

export function initPlayer(): void {
    destroyPlayer();

    if (Hls.isSupported()) {
        hls = new Hls({
            enableWorker: PLAYER_CONFIG.HLS.enableWorker,
            lowLatencyMode: PLAYER_CONFIG.HLS.lowLatencyMode,
            backBufferLength: PLAYER_CONFIG.HLS.backBufferLength,
            subtitlesEnabled: PLAYER_CONFIG.HLS.subtitlesEnabled,
            manifestLoadingTimeOut: PLAYER_CONFIG.HLS.manifestLoadingTimeOut,
            manifestLoadingMaxRetry: PLAYER_CONFIG.HLS.manifestLoadingMaxRetry,
            manifestLoadingRetryDelay: PLAYER_CONFIG.HLS.manifestLoadingRetryDelay,
            levelLoadingTimeOut: PLAYER_CONFIG.HLS.levelLoadingTimeOut,
            levelLoadingMaxRetry: PLAYER_CONFIG.HLS.levelLoadingMaxRetry,
            levelLoadingRetryDelay: PLAYER_CONFIG.HLS.levelLoadingRetryDelay,
            fragLoadingTimeOut: PLAYER_CONFIG.HLS.fragLoadingTimeOut,
            fragLoadingMaxRetry: PLAYER_CONFIG.HLS.fragLoadingMaxRetry,
            fragLoadingRetryDelay: PLAYER_CONFIG.HLS.fragLoadingRetryDelay,
        });

        const errorOverlay = document.getElementById('error-overlay') as HTMLDivElement;
        const errorMessage = document.getElementById('error-message') as HTMLSpanElement;
        const btnRetry = document.getElementById('btn-retry') as HTMLButtonElement;
        let errorCount = 0;

        function showError(message: string): void {
            if (errorOverlay && errorMessage) {
                errorMessage.textContent = message;
                errorOverlay.style.display = 'flex';
                waiting.style.display = 'none';
            }
        }

        function hideError(): void {
            if (errorOverlay) {
                errorOverlay.style.display = 'none';
            }
        }

        btnRetry?.addEventListener('click', () => {
            hideError();
            errorCount = 0;
            initPlayer();
        });

        hls.on(Hls.Events.MANIFEST_PARSED, () => {
            waiting.style.display = 'none';
            playerInitialized = true;
            video.play().catch(() => {});
        });

        hls.on(Hls.Events.ERROR, (_e, data) => {
            if (data.fatal) {
                errorCount++;

switch (data.type) {
                     case Hls.ErrorTypes.NETWORK_ERROR:
                         if (errorCount < PLAYER_CONFIG.ERROR_THRESHOLDS.networkErrorRetry) {
                             hls?.startLoad();
                         } else {
                             showError('No se puede conectar al stream. Verifique que el servidor est\xe9 en ejecuci\xf3n.');
                         }
                         break;
                     case Hls.ErrorTypes.MEDIA_ERROR:
                         hls?.recoverMediaError();
                         break;
                     case Hls.ErrorTypes.MANIFEST_LOAD_ERROR:
                         if (errorCount >= PLAYER_CONFIG.ERROR_THRESHOLDS.manifestLoadErrorRetry) {
                             showError('No se pudo cargar el manifiesto del stream.');
                         }
                         break;
                     case Hls.ErrorTypes.MANIFEST_PARSE_ERROR:
                         showError('Error al\u89e3\u6790 el stream.');
                         break;
                     default:
                         if (errorCount >= PLAYER_CONFIG.ERROR_THRESHOLDS.genericErrorRetry) {
                             showError(`Error: ${data.details || data.type}`);
                         }
                }
            } else {
                errorCount = 0;
            }
        });

        hls.on(Hls.Events.SUBTITLE_TRACKS_UPDATED, (_event, _data) => {
            if (hls && hls.subtitleTracks.length > 0) {
                const firstTrack = hls.subtitleTracks[0];
                if (firstTrack.name) {
                    subtitleLanguageName = firstTrack.name;
                }
                if (subtitleTrackElement) {
                    subtitleTrackElement.label = subtitleLanguageName;
                }
            }
        });

        hls.loadSource('/hls/master.m3u8');
        hls.attachMedia(video);

    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = '/hls/master.m3u8';
    }
}

export function setupSubtitleChangeListener(): void {
    const handleModeChange = (event: Event): void => {
        const track = event.target as TextTrack;
        if (track.kind === 'subtitles') {
            userPreference = track.mode === 'showing';
        }
    };

    const setupTrackListeners = (): void => {
        for (let i = 0; i < video.textTracks.length; i++) {
            const track = video.textTracks[i];
            if (track.kind === 'subtitles') {
                track.removeEventListener('modechange', handleModeChange);
                track.addEventListener('modechange', handleModeChange);
            }
        }
    };

    if (video.textTracks.length > 0) {
        setupTrackListeners();
    } else {
        video.addEventListener('loadedmetadata', setupTrackListeners);
    }
}

export function init(): void {
    initPlayer();
    loadVTT();
    setupSubtitleChangeListener();
    setInterval(loadVTT, PLAYER_CONFIG.VTT_REFRESH_INTERVAL);
}

document.addEventListener('DOMContentLoaded', init);
