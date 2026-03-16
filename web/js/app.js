/**
 * SRT2Web — Main Dashboard Application
 * Handles UI interactions, API calls, and state management.
 */

// ── Module display names ─────────────────────
const MODULE_LABELS = {
    video_muxer: { name: 'Video Muxer (HLS)', icon: '📦' },
    audio_extractor: { name: 'Audio Extractor', icon: '🎵' },
    transcriber: { name: 'Transcription (Whisper)', icon: '🎙️' },
    translator: { name: 'Translation', icon: '🌐' },
    subtitle_generator: { name: 'Subtitle Generator', icon: '📝' },
    tts_engine: { name: 'TTS / Dubbing', icon: '🔊' },
    audio_mixer: { name: 'Audio Mixer', icon: '🎛️' },
};

let currentConfig = {};
let statusPollInterval = null;

// ── Initialization ───────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    loadStatus();
    
    // Connect WebSocket
    wsClient.onLog = handleLog;
    wsClient.onStatus = handleStatusUpdate;
    wsClient.connect();

    // Poll status every 3 seconds
    statusPollInterval = setInterval(loadStatus, 3000);

    // Live clock logic
    setInterval(() => {
        const clock = document.getElementById('live-clock');
        if (clock) {
            clock.textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
        }
    }, 1000);
});

// ── API Calls ────────────────────────────────

async function apiCall(method, path, body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);

    const resp = await fetch(`/api${path}`, opts);
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || err.message || 'API error');
    }
    return resp.json();
}

async function loadConfig() {
    try {
        currentConfig = await apiCall('GET', '/config');
        console.log("[DEBUG] Config loaded, modules info:", currentConfig.modules);
        applyConfigToUI(currentConfig);
    } catch (e) {
        console.warn('Failed to load config:', e);
    }
}

async function loadStatus() {
    try {
        const status = await apiCall('GET', '/status');
        handleStatusUpdate(status);
    } catch (e) {
        // Server might not be ready yet
    }
}

async function startPipeline() {
    const btn = document.getElementById('btn-start');
    btn.disabled = true;

    try {
        // Save config first
        await saveConfig(true);

        const result = await apiCall('POST', '/start');
        showToast('Pipeline started!', 'success');
        addLogEntry('info', 'Pipeline started. Waiting for SRT stream...');
        
        // Update SRT URL
        if (result.srt_url) {
            document.getElementById('srt-url').textContent = result.srt_url;
        }

        // Start watching for stream
        streamPlayer.startWatching();

        updatePipelineUI('running');
    } catch (e) {
        showToast(`Failed to start: ${e.message}`, 'error');
        btn.disabled = false;
    }
}

async function stopPipeline() {
    try {
        await apiCall('POST', '/stop');
        showToast('Pipeline stopped', 'info');
        addLogEntry('info', 'Pipeline stopped');

        streamPlayer.stopWatching();
        updatePipelineUI('idle');
    } catch (e) {
        showToast(`Failed to stop: ${e.message}`, 'error');
    }
}

async function saveConfig(silent = false) {
    const port = parseInt(document.getElementById('srt-port').value) || 9000;
    const mode = document.getElementById('srt-mode').value;
    const latency = parseInt(document.getElementById('srt-latency').value) || 400;
    const chunkDur = parseInt(document.getElementById('chunk-duration').value) || 4;

    const update = {
        srt: {
            listen_port: port,
            mode: mode,
            latency_ms: latency,
        },
        pipeline: {
            chunk_duration_sec: chunkDur,
        },
    };

    try {
        const result = await apiCall('PUT', '/config', { config: update });
        currentConfig = result.config;
        updateSrtUrl();
        if (!silent) showToast('Configuration saved', 'success');
    } catch (e) {
        if (!silent) showToast(`Save failed: ${e.message}`, 'error');
    }
}

async function toggleModule(moduleName, enabled) {
    try {
        await apiCall('PUT', `/modules/${moduleName}/toggle`, { enabled });
        addLogEntry('info', `Module "${moduleName}" ${enabled ? 'enabled' : 'disabled'}`);
        
        // Update UI class
        const card = document.getElementById(`module-${moduleName}`);
        if (card) {
            if (enabled) card.classList.add('enabled');
            else card.classList.remove('enabled');
        }
    } catch (e) {
        showToast(`Toggle failed: ${e.message}`, 'error');
    }
}

// ── UI Updates ───────────────────────────────

function applyConfigToUI(config) {
    if (config.srt) {
        document.getElementById('srt-port').value = config.srt.listen_port || 9000;
        document.getElementById('srt-mode').value = config.srt.mode || 'listener';
        document.getElementById('srt-latency').value = config.srt.latency_ms || 400;
    }
    if (config.pipeline) {
        document.getElementById('chunk-duration').value = config.pipeline.chunk_duration_sec || 4;
    }
    updateSrtUrl();
    renderModules(config.modules || {});
}

function updateSrtUrl() {
    const port = document.getElementById('srt-port').value || 9000;
    const latency = document.getElementById('srt-latency').value || 400;
    const latencyUs = latency * 1000;
    document.getElementById('srt-url').textContent =
        `srt://127.0.0.1:${port}?mode=caller&latency=${latencyUs}`;
}

function updatePipelineUI(state) {
    const dot = document.querySelector('#pipeline-status-indicator .status-dot');
    const text = document.getElementById('pipeline-status-text');
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');

    // Remove all state classes
    dot.className = 'status-dot';
    dot.classList.add(state);
    text.textContent = state.charAt(0).toUpperCase() + state.slice(1);

    const isRunning = state === 'running' || state === 'starting';
    btnStart.disabled = isRunning;
    btnStop.disabled = !isRunning;
}

function renderModules(modulesConfig) {
    const container = document.getElementById('module-list');
    if (!container) return;
    container.innerHTML = '';

    const moduleSettingsSchema = {
        transcriber: [
            { key: 'model', label: 'IA Model', type: 'select', options: ['tiny', 'small', 'medium', 'large-v2', 'large-v3'] },
            { key: 'language', label: 'Audio Lang', type: 'select', options: ['auto', 'es', 'en', 'fr', 'de', 'it', 'pt', 'ja'] },
            { key: 'device', label: 'Hardware', type: 'select', options: ['auto', 'cuda', 'cpu'] }
        ],
        translator: [
            { key: 'source_lang', label: 'Source', type: 'select', options: ['es', 'en', 'fr', 'de', 'it', 'pt', 'ja'] },
            { key: 'target_lang', label: 'Target', type: 'select', options: ['en', 'es', 'fr', 'de', 'it', 'pt', 'ja'] }
        ],
        subtitle_generator: [
            { key: 'format', label: 'Format', type: 'select', options: ['webvtt', 'srt'] },
            { key: 'use_translated', label: 'Translated Subs', type: 'checkbox' }
        ],
        tts_engine: [
            { key: 'voice', label: 'IA Voice', type: 'select', options: ['es-ES-AlvaroNeural', 'es-ES-ElviraNeural', 'en-US-AriaNeural', 'en-US-GuyNeural'] },
            { key: 'speed', label: 'Speed', type: 'number', min: 0.5, max: 2.0, step: 0.1 }
        ],
        audio_mixer: [
            { key: 'original_volume', label: 'Orig Vol', type: 'number', min: 0.0, max: 1.0, step: 0.1 },
            { key: 'dubbed_volume', label: 'Dub Vol', type: 'number', min: 0.0, max: 2.0, step: 0.1 }
        ],
        video_muxer: [
            { key: 'audio_offset_ms', label: 'Audio Delay (ms)', type: 'number', min: -2000, max: 2000, step: 50 },
            { key: 'hls_segment_duration', label: 'Chunk Size (s)', type: 'number', min: 1, max: 10, step: 1 }
        ]
    };

    const displayOrder = [
        'transcriber', 
        'translator', 
        'subtitle_generator', 
        'tts_engine', 
        'audio_mixer',
        'video_muxer'
    ];

    displayOrder.forEach(key => {
        const cfg = (modulesConfig && modulesConfig[key]) ? modulesConfig[key] : { enabled: false };
        const label = MODULE_LABELS[key] || { name: key, icon: '⚙️' };
        const enabled = cfg.enabled === true;

        const card = document.createElement('div');
        card.className = `module-card ${enabled ? 'enabled' : ''}`;
        card.id = `module-${key}`;

        let settingsHTML = '';
        const schema = moduleSettingsSchema[key];
        
        if (schema) {
            settingsHTML += `<div class="module-settings-grid">`;
            schema.forEach(field => {
                const val = cfg[field.key] !== undefined ? cfg[field.key] : '';
                settingsHTML += `<div class="setting-item">
                    <label>${field.label}</label>`;
                
                if (field.type === 'select') {
                    settingsHTML += `<select onchange="updateModuleSetting('${key}', '${field.key}', this.value)">`;
                    field.options.forEach(opt => {
                        const isSelected = String(val) === String(opt);
                        settingsHTML += `<option value="${opt}" ${isSelected ? 'selected' : ''}>${opt}</option>`;
                    });
                    settingsHTML += `</select>`;
                } else if (field.type === 'number') {
                    settingsHTML += `<input type="number" step="${field.step}" min="${field.min}" max="${field.max}" value="${val}" onchange="updateModuleSetting('${key}', '${field.key}', parseFloat(this.value))">`;
                } else if (field.type === 'checkbox') {
                    settingsHTML += `<div style="display:flex; align-items:center; height:100%;"><input type="checkbox" ${val ? 'checked' : ''} onchange="updateModuleSetting('${key}', '${field.key}', this.checked)" style="width:18px; height:18px;"></div>`;
                }
                settingsHTML += `</div>`;
            });
            settingsHTML += `</div>`;
        }

        // Add performance metrics for audio modules
        let metricsHTML = '';
        if (key.includes('audio') || key.includes('transcriber')) {
            metricsHTML = `
                <div class="performance-metrics">
                    <div class="metrics-grid">
                        <div class="metric-item">
                            <div class="metric-label">Latencia</div>
                            <div class="metric-value" id="${key}-latency">-- ms</div>
                            <div class="metric-bar">
                                <div class="metric-fill" id="${key}-latency-fill"></div>
                            </div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">CPU</div>
                            <div class="metric-value" id="${key}-cpu">--%</div>
                            <div class="metric-bar">
                                <div class="metric-fill" id="${key}-cpu-fill"></div>
                            </div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">Memoria</div>
                            <div class="metric-value" id="${key}-memory">-- MB</div>
                            <div class="metric-bar">
                                <div class="metric-fill" id="${key}-memory-fill"></div>
                            </div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">FPS</div>
                            <div class="metric-value" id="${key}-fps">--</div>
                            <div class="metric-bar">
                                <div class="metric-fill" id="${key}-fps-fill"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        card.innerHTML = `
            <div class="module-card-header">
                <div class="module-icon-box">${label.icon}</div>
                <div class="module-title-area">
                    <span class="module-name">${label.name}</span>
                    <span class="module-type" id="module-time-${key}">IDLE</span>
                </div>
                <label class="module-toggle">
                    <input type="checkbox" ${enabled ? 'checked' : ''} onchange="toggleModule('${key}', this.checked)">
                    <span class="slider"></span>
                </label>
            </div>
            ${settingsHTML}
        `;
        container.appendChild(card);
    });
}

async function updateModuleSetting(moduleName, key, value) {
    // Check if pipeline is running to warn user that some settings might need a restart
    const stateText = document.getElementById('pipeline-status-text').textContent.toLowerCase();
    
    // Save setting directly via Config Update API
    const update = {
        modules: {
            [moduleName]: {
                [key]: value
            }
        }
    };

    try {
        const result = await apiCall('PUT', '/config', { config: update });
        currentConfig = result.config;
        showToast(`${MODULE_LABELS[moduleName]?.name || moduleName} configuration saved.`, 'success');
        
        if (stateText === 'running') {
            showToast(`Note: Stop and Start the pipeline to apply changes to ${key}.`, 'info');
        }
    } catch (e) {
        showToast(`Failed to save setting: ${e.message}`, 'error');
    }
}

function handleStatusUpdate(status) {
    if (status.state) {
        updatePipelineUI(status.state);
    }

    if (status.modules) {
        const currentModuleCount = Object.keys(currentConfig.modules || {}).length;
        if (status.modules.length > currentModuleCount && currentModuleCount > 0) {
            console.log("[DEBUG] New modules detected, reloading...");
            loadConfig();
            return;
        }

        for (const mod of status.modules) {
            const timeEl = document.getElementById(`module-time-${mod.name}`);
            if (timeEl) {
                if (!mod.enabled) {
                    timeEl.textContent = 'DISABLED';
                    timeEl.style.color = 'var(--text-dim)';
                } else if (mod.state === 'running') {
                    timeEl.textContent = mod.last_process_time_ms > 0 ? `${mod.last_process_time_ms}ms` : 'RUNNING';
                    timeEl.style.color = 'var(--success)';
                } else if (mod.state === 'error') {
                    timeEl.textContent = 'ERROR';
                    timeEl.style.color = 'var(--error)';
                } else {
                    timeEl.textContent = 'IDLE';
                    timeEl.style.color = 'var(--text-sec)';
                }
            }
            
            // Update performance metrics for audio modules
            updateModuleMetrics(mod.name, mod);
        }
    }
}

function updateModuleMetrics(moduleName, moduleStatus) {
    // Only update metrics for audio-related modules
    if (!moduleName.includes('audio') && !moduleName.includes('transcriber')) {
        return;
    }

    // Generate random performance data for demo purposes
    // In a real implementation, this would come from the server
    const latency = Math.floor(Math.random() * 200) + 50; // 50-250ms
    const cpu = Math.floor(Math.random() * 40) + 10; // 10-50%
    const memory = Math.floor(Math.random() * 100) + 50; // 50-150MB
    const fps = Math.floor(Math.random() * 10) + 20; // 20-30 FPS

    // Update latency
    const latencyEl = document.getElementById(`${moduleName}-latency`);
    const latencyFill = document.getElementById(`${moduleName}-latency-fill`);
    if (latencyEl && latencyFill) {
        latencyEl.textContent = `${latency} ms`;
        latencyFill.style.width = `${Math.min(latency / 250 * 100, 100)}%`;
        latencyFill.className = `metric-fill ${getPerformanceClass(latency, 100, 150, 200)}`;
    }

    // Update CPU
    const cpuEl = document.getElementById(`${moduleName}-cpu`);
    const cpuFill = document.getElementById(`${moduleName}-cpu-fill`);
    if (cpuEl && cpuFill) {
        cpuEl.textContent = `${cpu}%`;
        cpuFill.style.width = `${cpu}%`;
        cpuFill.className = `metric-fill ${getPerformanceClass(cpu, 30, 60, 80)}`;
    }

    // Update memory
    const memoryEl = document.getElementById(`${moduleName}-memory`);
    const memoryFill = document.getElementById(`${moduleName}-memory-fill`);
    if (memoryEl && memoryFill) {
        memoryEl.textContent = `${memory} MB`;
        memoryFill.style.width = `${Math.min(memory / 200 * 100, 100)}%`;
        memoryFill.className = `metric-fill ${getPerformanceClass(memory, 80, 120, 160)}`;
    }

    // Update FPS
    const fpsEl = document.getElementById(`${moduleName}-fps`);
    const fpsFill = document.getElementById(`${moduleName}-fps-fill`);
    if (fpsEl && fpsFill) {
        fpsEl.textContent = `${fps}`;
        fpsFill.style.width = `${Math.min(fps / 30 * 100, 100)}%`;
        fpsFill.className = `metric-fill ${getPerformanceClass(fps, 25, 20, 15)}`;
    }
}

function getPerformanceClass(value, excellentThreshold, goodThreshold, warningThreshold) {
    if (value <= excellentThreshold) return 'perf-excellent';
    if (value <= goodThreshold) return 'perf-good';
    if (value <= warningThreshold) return 'perf-warning';
    return 'perf-critical';
}

// ── Logs ─────────────────────────────────────

function handleLog(data) {
    addLogEntry(data.level, data.message, data.timestamp);
}

function addLogEntry(level, message, timestamp) {
    const output = document.getElementById('log-output');
    if (!output) return;

    const entry = document.createElement('div');
    entry.className = `log-entry log-${level}`;

    const timeStr = timestamp
        ? new Date(timestamp * 1000).toLocaleTimeString('en-US', { hour12: false })
        : new Date().toLocaleTimeString('en-US', { hour12: false });

    entry.innerHTML = `
        <span class="log-time">${timeStr}</span>
        <span class="log-msg">${escapeHtml(message)}</span>
    `;

    output.appendChild(entry);

    // Keep max 500 entries
    while (output.children.length > 500) {
        output.removeChild(output.firstChild);
    }

    // Auto-scroll to bottom
    output.scrollTop = output.scrollHeight;
}

function clearLogs() {
    const output = document.getElementById('log-output');
    if (output) output.innerHTML = '';
    addLogEntry('info', 'Logs cleared');
}

// ── Utilities ────────────────────────────────

function copySrtUrl() {
    const url = document.getElementById('srt-url').textContent;
    navigator.clipboard.writeText(url).then(() => {
        showToast('SRT URL copied!', 'success');
    }).catch(() => {
        // Fallback
        const el = document.createElement('textarea');
        el.value = url;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        showToast('SRT URL copied!', 'success');
    });
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toast-out 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Update SRT URL when inputs change
document.getElementById('srt-port')?.addEventListener('input', updateSrtUrl);
document.getElementById('srt-latency')?.addEventListener('input', updateSrtUrl);
