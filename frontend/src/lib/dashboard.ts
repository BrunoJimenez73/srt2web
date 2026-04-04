/**
 * Dashboard principal - Punto de entrada para la lógica del dashboard
 * Maneja la inicialización de todos los módulos y la comunicación con el backend
 */

import { store } from './store';
import { initSecurityPanel } from './modules/header';
import { initLogPanel } from './modules/logpanel';
import { showToast } from './modules/toast';
import type { Config, Status } from './types';

// Estado de la conexión WebSocket
let ws: WebSocket | null = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000;

/**
 * Inicializa el dashboard cuando el DOM está listo
 */
function initDashboard(): void {
  console.log('🚀 Inicializando dashboard SRT2Web...');

  // Inicializar módulos UI
  initSecurityPanel();
  initLogPanel();

  // Configurar botones principales
  setupMainButtons();

  // Conectar WebSocket
  connectWebSocket();

  // Cargar configuración inicial
  loadInitialConfig();

  console.log('✅ Dashboard inicializado');
}

/**
 * Configura los botones principales del dashboard
 */
function setupMainButtons(): void {
  // Botón Iniciar
  const btnStart = document.getElementById('btn-start');
  if (btnStart) {
    btnStart.addEventListener('click', startPipeline);
  }

  // Botón Detener
  const btnStop = document.getElementById('btn-stop');
  if (btnStop) {
    btnStop.addEventListener('click', stopPipeline);
  }

  // Botón Guardar Config
  const btnSave = document.getElementById('btn-save-config');
  if (btnSave) {
    btnSave.addEventListener('click', saveConfig);
  }
}

/**
 * Conecta al WebSocket para logs en tiempo real
 */
function connectWebSocket(): void {
  const wsUrl = getWebSocketUrl();
  console.log('🔌 Conectando WebSocket:', wsUrl);

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('✅ WebSocket conectado');
    reconnectAttempts = 0;
    updateWsStatus(true);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    } catch (error) {
      console.error('Error procesando mensaje WebSocket:', error);
    }
  };

  ws.onclose = () => {
    console.log('🔌 WebSocket desconectado');
    updateWsStatus(false);
    // Reconectar automáticamente
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      reconnectAttempts++;
      console.log(`🔄 Reintentando conexión (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
      setTimeout(connectWebSocket, RECONNECT_DELAY);
    }
  };

  ws.onerror = (error) => {
    console.error('❌ Error WebSocket:', error);
  };
}

/**
 * Obtiene la URL del WebSocket
 */
function getWebSocketUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const token = localStorage.getItem('srt2web_auth_token');
  
  let url = `${protocol}//${host}/ws/logs`;
  if (token) {
    url += `?token=${encodeURIComponent(token)}`;
  }
  return url;
}

/**
 * Maneja los mensajes recibidos por WebSocket
 */
function handleWebSocketMessage(data: any): void {
  if (data.type === 'log') {
    // Agregar log al panel
    addLog(data.level, data.message);
  } else if (data.type === 'status') {
    // Actualizar estado
    updateStatus(data.status);
  }
}

/**
 * Actualiza el indicador de estado WebSocket
 */
function updateWsStatus(connected: boolean): void {
  const wsStatus = document.getElementById('ws-status');
  if (wsStatus) {
    wsStatus.classList.toggle('connected', connected);
    wsStatus.classList.toggle('disconnected', !connected);
    const label = wsStatus.querySelector('.ws-status-label');
    if (label) {
      label.textContent = connected ? 'WS ON' : 'WS OFF';
    }
  }
}

/**
 * Agrega un log al panel
 */
function addLog(level: string, message: string): void {
  const logContent = document.getElementById('log-content');
  if (!logContent) return;

  const logEntry = document.createElement('div');
  logEntry.className = `log-entry log-${level}`;
  
  const timestamp = new Date().toLocaleTimeString();
  logEntry.innerHTML = `<span class="log-time">[${timestamp}]</span> <span class="log-message">${escapeHtml(message)}</span>`;
  
  logContent.appendChild(logEntry);
  
  // Auto-scroll al final
  logContent.scrollTop = logContent.scrollHeight;
  
  // Limitar número de logs
  const maxLogs = 1000;
  while (logContent.children.length > maxLogs) {
    const firstChild = logContent.firstChild;
    if (firstChild) {
      logContent.removeChild(firstChild);
    }
  }
}

/**
 * Escapa HTML para prevenir XSS
 */
function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Carga la configuración inicial del backend
 */
async function loadInitialConfig(): Promise<void> {
  try {
    const response = await fetch('/api/config');
    if (response.ok) {
      const config = await response.json();
      store.setConfig(config);
      applyConfigToUI(config);
    }
  } catch (error) {
    console.error('Error cargando configuración:', error);
  }
}

/**
 * Aplica la configuración a los elementos UI
 */
function applyConfigToUI(config: Config): void {
  // Input type
  const inputType = (config.input as any)?.type || 'srt';
  const inputTypeSelect = document.getElementById('input-type') as HTMLSelectElement;
  if (inputTypeSelect) {
    inputTypeSelect.value = inputType;
  }

  // SRT port
  const srtPort = (config.input as any)?.srt?.listen_port || 9000;
  const srtPortInput = document.getElementById('input-srt-port') as HTMLInputElement;
  if (srtPortInput) {
    srtPortInput.value = srtPort.toString();
  }

  // Whisper model
  const whisperModel = config.modules?.transcriber?.model || 'tiny';
  const whisperModelSelect = document.getElementById('whisper-model') as HTMLSelectElement;
  if (whisperModelSelect) {
    whisperModelSelect.value = whisperModel;
  }

  // Translator enabled
  const translatorEnabled = config.modules?.translator?.enabled || false;
  const translatorCheckbox = document.getElementById('translator-enabled') as HTMLInputElement;
  if (translatorCheckbox) {
    translatorCheckbox.checked = translatorEnabled;
  }

  // TTS enabled
  const ttsEnabled = config.modules?.tts_engine?.enabled || false;
  const ttsCheckbox = document.getElementById('tts-enabled') as HTMLInputElement;
  if (ttsCheckbox) {
    ttsCheckbox.checked = ttsEnabled;
  }

  // Subtitle enabled
  const subtitleEnabled = config.modules?.subtitle_generator?.enabled || false;
  const subtitleCheckbox = document.getElementById('subtitle-enabled') as HTMLInputElement;
  if (subtitleCheckbox) {
    subtitleCheckbox.checked = subtitleEnabled;
  }

  // Audio mixer enabled
  const mixerEnabled = config.modules?.audio_mixer?.enabled || false;
  const mixerCheckbox = document.getElementById('audio-mixer-enabled') as HTMLInputElement;
  if (mixerCheckbox) {
    mixerCheckbox.checked = mixerEnabled;
  }
}

/**
 * Inicia el pipeline
 */
async function startPipeline(): Promise<void> {
  const btnStart = document.getElementById('btn-start') as HTMLButtonElement;
  if (btnStart) {
    btnStart.disabled = true;
    btnStart.classList.add('loading');
  }

  try {
    const response = await fetch('/api/start', { method: 'POST' });
    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }
    const result = await response.json();
    console.log('Pipeline iniciado:', result);
  } catch (error) {
    console.error('Error iniciando pipeline:', error);
    alert(`Error iniciando pipeline: ${error}`);
  } finally {
    if (btnStart) {
      btnStart.disabled = false;
      btnStart.classList.remove('loading');
    }
  }
}

/**
 * Detiene el pipeline
 */
async function stopPipeline(): Promise<void> {
  const btnStop = document.getElementById('btn-stop') as HTMLButtonElement;
  if (btnStop) {
    btnStop.disabled = true;
    btnStop.classList.add('loading');
  }

  try {
    const response = await fetch('/api/stop', { method: 'POST' });
    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }
    const result = await response.json();
    console.log('Pipeline detenido:', result);
  } catch (error) {
    console.error('Error deteniendo pipeline:', error);
    alert(`Error deteniendo pipeline: ${error}`);
  } finally {
    if (btnStop) {
      btnStop.disabled = false;
      btnStop.classList.remove('loading');
    }
  }
}

/**
 * Guarda la configuración
 */
async function saveConfig(): Promise<void> {
  const btnSave = document.getElementById('btn-save-config') as HTMLButtonElement;
  if (btnSave) {
    btnSave.disabled = true;
    btnSave.classList.add('loading');
  }

  try {
    // Recopilar configuración actual desde la UI
    const config = collectConfigFromUI();
    
    const response = await fetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config })
    });

    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    console.log('Configuración guardada:', result);
    
    // Mostrar notificación
    showToast('✅ Configuración guardada', 'success');
  } catch (error) {
    console.error('Error guardando configuración:', error);
    showToast(`❌ Error guardando: ${error}`, 'error');
  } finally {
    if (btnSave) {
      btnSave.disabled = false;
      btnSave.classList.remove('loading');
    }
  }
}

/**
 * Recopila la configuración desde la UI
 */
function collectConfigFromUI(): Partial<Config> {
  const config: any = {};

  // Input type
  const inputTypeSelect = document.getElementById('input-type') as HTMLSelectElement;
  if (inputTypeSelect) {
    config.input = { type: inputTypeSelect.value };
  }

  // SRT settings
  const srtPortInput = document.getElementById('input-srt-port') as HTMLInputElement;
  const srtModeSelect = document.getElementById('input-srt-mode') as HTMLSelectElement;
  const srtLatencyInput = document.getElementById('input-srt-latency') as HTMLInputElement;
  
  if (srtPortInput) {
    if (!config.input) config.input = {};
    config.input.srt = {
      listen_port: parseInt(srtPortInput.value) || 9000,
      mode: srtModeSelect?.value || 'listener',
      latency_ms: parseInt(srtLatencyInput.value) || 1000
    };
  }

  // Modules
  config.modules = {};

  // Transcriber
  const whisperModelSelect = document.getElementById('whisper-model') as HTMLSelectElement;
  const whisperLangSelect = document.getElementById('whisper-lang') as HTMLSelectElement;
  const whisperDeviceSelect = document.getElementById('whisper-device') as HTMLSelectElement;
  const whisperEnabled = document.getElementById('whisper-enabled') as HTMLInputElement;
  
  if (whisperModelSelect) {
    config.modules.transcriber = {
      model: whisperModelSelect.value,
      language: whisperLangSelect?.value || 'auto',
      device: whisperDeviceSelect?.value || 'auto',
      enabled: whisperEnabled?.checked ?? true
    };
  }

  // Translator
  const translatorSource = document.getElementById('translator-source') as HTMLSelectElement;
  const translatorTarget = document.getElementById('translator-target') as HTMLSelectElement;
  const translatorEnabled = document.getElementById('translator-enabled') as HTMLInputElement;
  
  if (translatorSource) {
    config.modules.translator = {
      source_lang: translatorSource.value,
      target_lang: translatorTarget?.value || 'es',
      enabled: translatorEnabled?.checked ?? false
    };
  }

  // TTS
  const ttsEngine = document.getElementById('tts-engine') as HTMLSelectElement;
  const ttsVoiceEdge = document.getElementById('tts-voice-edge') as HTMLSelectElement;
  const ttsVoicePiper = document.getElementById('tts-voice-piper') as HTMLSelectElement;
  const ttsSpeed = document.getElementById('tts-speed') as HTMLInputElement;
  const ttsEnabled = document.getElementById('tts-enabled') as HTMLInputElement;
  
  if (ttsEngine) {
    const voice = ttsEngine.value === 'edge-tts' ? ttsVoiceEdge?.value : ttsVoicePiper?.value;
    config.modules.tts_engine = {
      engine: ttsEngine.value,
      voice: voice,
      speed: parseFloat(ttsSpeed?.value || '1.0'),
      enabled: ttsEnabled?.checked ?? false
    };
  }

  // Subtitle generator
  const subtitleFormat = document.getElementById('subtitle-format') as HTMLSelectElement;
  const subtitleUseTranslated = document.getElementById('subtitle-use-translated') as HTMLSelectElement;
  const subtitleEnabled = document.getElementById('subtitle-enabled') as HTMLInputElement;
  
  if (subtitleFormat) {
    config.modules.subtitle_generator = {
      format: subtitleFormat.value,
      use_translated: subtitleUseTranslated?.value === 'true',
      enabled: subtitleEnabled?.checked ?? false
    };
  }

  // Audio mixer
  const mixerOriginalVolume = document.getElementById('audio-mixer-original-volume') as HTMLInputElement;
  const mixerDubbedVolume = document.getElementById('audio-mixer-dubbed-volume') as HTMLInputElement;
  const mixerEnabled = document.getElementById('audio-mixer-enabled') as HTMLInputElement;
  
  if (mixerOriginalVolume) {
    config.modules.audio_mixer = {
      original_volume: parseFloat(mixerOriginalVolume.value) || 0.3,
      tts_volume: parseFloat(mixerDubbedVolume?.value || '1.0'),
      enabled: mixerEnabled?.checked ?? false
    };
  }

  return config;
}

// showToast is imported from './modules/toast'

/**
 * Actualiza el estado del pipeline
 */
function updateStatus(status: Status): void {
  store.setStatus(status);
  
  // Actualizar UI según estado
  const statusText = document.getElementById('status-text');
  const statusDot = document.getElementById('status-dot');
  const btnStart = document.getElementById('btn-start');
  const btnStop = document.getElementById('btn-stop');
  
  if (statusText && statusDot) {
    if (status.state === 'running') {
      statusText.textContent = 'ENCENDIDO';
      statusDot.classList.add('active');
      if (btnStart) btnStart.style.display = 'none';
      if (btnStop) btnStop.style.display = 'inline-flex';
    } else {
      statusText.textContent = 'APAGADO';
      statusDot.classList.remove('active');
      if (btnStart) btnStart.style.display = 'inline-flex';
      if (btnStop) btnStop.style.display = 'none';
    }
  }
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDashboard);
} else {
  initDashboard();
}

// Exportar funciones globales para uso desde HTML
(window as any).startPipeline = startPipeline;
(window as any).stopPipeline = stopPipeline;
(window as any).saveConfig = saveConfig;
(window as any).toggleModule = async (moduleName: string, enabled: boolean) => {
  try {
    const response = await fetch(`/api/modules/${moduleName}/toggle`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled })
    });
    
    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log(`Módulo ${moduleName} ${enabled ? 'activado' : 'desactivado'}:`, result);
  } catch (error) {
    console.error(`Error toggleando módulo ${moduleName}:`, error);
  }
};

(window as any).handleInputTypeChange = (type: string) => {
  // Mostrar/ocultar configuraciones según tipo de input
  const srtSettings = document.getElementById('input-srt-settings');
  const rtmpSettings = document.getElementById('input-rtmp-settings');
  const fileSettings = document.getElementById('input-file-settings');
  
  if (srtSettings) srtSettings.style.display = type === 'srt' ? 'flex' : 'none';
  if (rtmpSettings) rtmpSettings.style.display = type === 'rtmp' ? 'flex' : 'none';
  if (fileSettings) fileSettings.style.display = type === 'file' ? 'flex' : 'none';
};

(window as any).handleOutputFormatChange = (format: string) => {
  // Mostrar/ocultar configuraciones según formato de output
  const formats = ['web', 'srt', 'rtmp', 'file'];
  formats.forEach(f => {
    const settings = document.getElementById(`${f}-settings`);
    if (settings) settings.style.display = f === format ? 'flex' : 'none';
  });
};