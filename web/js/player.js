/**
 * SRT2Web — HLS Video Player
 * Initializes hls.js to play the live stream.
 */

class StreamPlayer {
    constructor(videoElementId) {
        this.video = document.getElementById(videoElementId);
        this.overlay = document.getElementById('video-overlay');
        this.liveBadge = document.getElementById('live-badge');
        this.hls = null;
        this.streamUrl = '/hls/stream.m3u8'; // Directo sin subtitulos para mayor estabilidad
        this.checkInterval = null;
        this.playing = false;
    }

    /**
     * Called when the pipeline starts. We merely reset state, but DO NOT auto-load the video 
     * to save CPU/Network resources.
     */
    startWatching() {
        this.stopWatching();
    }

    /**
     * Explicitly called by the user to monitor and load the video inside the admin panel.
     */
    requestPreview() {
        if (this.checkInterval) return;
        this.video.muted = true; // ensure it's muted
        
        // Change overlay text to indicate loading
        const btnInternal = document.getElementById('btn-internal-preview');
        if(btnInternal) btnInternal.innerHTML = 'Conectando...';

        this.checkInterval = setInterval(() => this._checkStream(), 2000);
        this._checkStream();
    }

    stopWatching() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
        this._destroyHls();
        this._showOverlay();

        const btnInternal = document.getElementById('btn-internal-preview');
        if(btnInternal) btnInternal.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 5px;"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg> Ver Preview Aqui`;
    }

    async _checkStream() {
        if (this.playing) return;

        try {
            const resp = await fetch(this.streamUrl, { method: 'HEAD' });
            if (resp.ok) {
                this._attachHls();
            }
        } catch {
            // Stream not ready yet
        }
    }

    _attachHls() {
        if (this.playing) return;

        if (Hls.isSupported()) {
            this.hls = new Hls({
                enableWorker: true,
                lowLatencyMode: false,
                backBufferLength: 90,
                liveSyncDurationCount: 8,
                liveMaxLatencyDurationCount: 15,
                liveDurationInfinity: true,
                manifestLoadingMaxRetry: 60,
                manifestLoadingRetryDelay: 1000,
                levelLoadingMaxRetry: 30,
                maxBufferLength: 60,
                maxMaxBufferLength: 120,
                maxBufferSize: 100 * 1000 * 1000,
                maxBufferHole: 0.1,
                highBufferWatchdogPeriod: 5,
                nudgeOffset: 0.1,
                nudgeMaxRetry: 5,
                maxFragLookUpTolerance: 0.2,
                maxStarvationDelay: 15000,
                maxLoadingDelay: 15000,
            });

            this.hls.loadSource(this.streamUrl);
            this.hls.attachMedia(this.video);

            this.hls.on(Hls.Events.MANIFEST_PARSED, () => {
                this.video.play().catch(() => {});
                this._hideOverlay();
                this.playing = true;
                
                // Force subtitles showing
                setTimeout(() => {
                    for (let i = 0; i < this.video.textTracks.length; i++) {
                        this.video.textTracks[i].mode = 'showing';
                    }
                }, 1000);
            });

            this.hls.on(Hls.Events.ERROR, (event, data) => {
                console.log('[HLS] Error:', data.type, data.details);
                if (data.fatal) {
                    switch (data.type) {
                        case Hls.ErrorTypes.NETWORK_ERROR:
                            console.warn('[HLS] Network error, retrying...');
                            this.hls.startLoad();
                            break;
                        case Hls.ErrorTypes.MEDIA_ERROR:
                            console.warn('[HLS] Media error, recovering...');
                            this.hls.recoverMediaError();
                            break;
                        case Hls.ErrorTypes.OTHER_ERROR:
                            // Ignore subtitle errors - they're not fatal
                            if (data.details && data.details.includes('subtitle')) {
                                console.log('[HLS] Subtitle error (ignored)');
                                return;
                            }
                            console.error('[HLS] Fatal error:', data);
                            this._destroyHls();
                            this.playing = false;
                            break;
                        default:
                            console.error('[HLS] Fatal error:', data);
                            this._destroyHls();
                            this.playing = false;
                            break;
                    }
                }
            });

            this.hls.on(Hls.Events.SUBTITLE_TRACKS_UPDATED, (event, data) => {
                if (data.subtitleTracks.length > 0) {
                    this.hls.subtitleTrack = 0;
                    for (let i = 0; i < this.video.textTracks.length; i++) {
                        this.video.textTracks[i].mode = 'showing';
                    }
                }
            });

        } else if (this.video.canPlayType('application/vnd.apple.mpegurl')) {
            // Safari native HLS
            this.video.src = this.streamUrl;
            this.video.addEventListener('loadedmetadata', () => {
                this.video.play().catch(() => {});
                this._hideOverlay();
                this.playing = true;
            });
        }
    }

    _destroyHls() {
        if (this.hls) {
            this.hls.destroy();
            this.hls = null;
        }
        this.playing = false;
    }

    _showOverlay() {
        if (this.overlay) this.overlay.classList.remove('hidden');
        if (this.liveBadge) this.liveBadge.style.display = 'none';
        
        const stopBtn = document.getElementById('btn-stop-preview');
        if (stopBtn) stopBtn.style.display = 'none';
    }

    _hideOverlay() {
        if (this.overlay) this.overlay.classList.add('hidden');
        if (this.liveBadge) this.liveBadge.style.display = 'inline';
        
        const stopBtn = document.getElementById('btn-stop-preview');
        if (stopBtn) stopBtn.style.display = 'block';
    }
}

// Global instance
const streamPlayer = new StreamPlayer('video-player');
