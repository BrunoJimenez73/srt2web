/**
 * Constantes globales - Textos, mensajes y valores fijos
 *
 * Todos los strings literales que se muestran en la UI
 * deben definirse aquí para facilitar traducciones y mantenimiento.
 */

// ── Puertos y URLs ─────────────────────────────────────────────────────────────
export const SERVER_PORT = 9999;
export const DEFAULT_SERVER_HOST = '127.0.0.1';

// ── Storage Keys ──────────────────────────────────────────────────────────────
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'srt2web_auth_token',
  THEME: 'srt2web_theme',
  LOG_FILTER: 'srt2web_log_filter',
  LAST_CONFIG: 'srt2web_last_config',
  SHOW_LOGS: 'srt2web_show_logs',
  LANGUAGE: 'srt2web_language'
} as const;

// ── Mensajes de UI ────────────────────────────────────────────────────────────
export const MESSAGES = {
  // Pipeline
  PIPELINE_STARTING: 'Iniciando pipeline...',
  PIPELINE_STARTED: 'Pipeline iniciado correctamente',
  PIPELINE_STOPPING: 'Deteniendo pipeline...',
  PIPELINE_STOPPED: 'Pipeline detenido',
  PIPELINE_CONFIRM_STOP: '¿Está seguro que desea detener el pipeline?',

  // Configuración
  CONFIG_SAVED: 'Configuración guardada correctamente',
  CONFIG_SAVE_ERROR: 'Error al guardar configuración',
  CONFIG_LOAD_ERROR: 'Error al cargar configuración',

  // Inputs
  INPUT_FILE_SELECTED: 'Archivo seleccionado. Ingrese la ruta completa manualmente.',
  INPUT_FILE_PLAY: 'Reproducción reanudada',
  INPUT_FILE_PAUSE: 'Reproducción pausada',
  INPUT_FILE_SEEK_ERROR: 'Error al buscar posición',

  // Copiar URL
  URL_COPIED: 'URL copiada al portapapeles',
  URL_COPY_ERROR: 'Error al copiar URL',

  // WebSocket
  WS_CONNECTED: 'Conectado al servidor',
  WS_DISCONNECTED: 'WebSocket desconectado',
  WS_ERROR: 'Error de conexión WebSocket',

  // General
  LOADING: 'Cargando...',
  ERROR: 'Ha ocurrido un error',
  SUCCESS: 'Operación completada correctamente',
  WARNING: 'Advertencia',
  INFO: 'Información',

  // Notificaciones
  TOAST_DURATION: 3000,

  // Logs
  LOG_PANEL_PLACEHOLDER: 'Esperando logs...',
  LOG_SEARCH_PLACEHOLDER: 'Buscar en logs...',
  LOG_CLEAR: 'Limpiar logs',

  // Outputs
  OUTPUT_CREATED: 'Salida creada correctamente',
  OUTPUT_REMOVED: 'Salida eliminada',
  OUTPUT_TOGGLED: 'Estado de salida actualizado'
} as const;

// ── Valores por defecto ───────────────────────────────────────────────────────
export const DEFAULTS = {
  CHUNK_DURATION: 3,
  SEGMENT_DURATION: 2,
  LIST_SIZE: 2,
  AUDIO_OFFSET: 0,
  CRF: 18,
  AUDIO_BITRATE: '192k',
  AUDIO_SAMPLE_RATE: 48000,
  TTS_SPEED: 1.0,
  ORIGINAL_VOLUME: 0.8,
  TTS_VOLUME: 1.0,
  WHISPER_MODEL: 'tiny',
  WHISPER_LANGUAGE: 'en',
  TRANSLATE_TARGET: 'es',
  SUBTITLE_FORMAT: 'srt'
} as const;

// ── Estados de módulos ────────────────────────────────────────────────────────
export const MODULE_STATES = {
  IDLE: 'idle',
  RUNNING: 'running',
  ERROR: 'error',
  STOPPED: 'stopped'
} as const;

// ── Tipos de Input ────────────────────────────────────────────────────────────
export const INPUT_TYPES = {
  SRT: 'srt',
  RTMP: 'rtmp',
  FILE: 'file'
} as const;

// ── Tipos de Output ───────────────────────────────────────────────────────────
export const OUTPUT_TYPES = {
  HLS: 'hls',
  RTMP: 'rtmp',
  SRT: 'srt',
  FILE: 'file',
  RECORDING: 'recording'
} as const;

// ── Intervalos de tiempo ──────────────────────────────────────────────────────
export const INTERVALS = {
  STATUS_POLL: 5000,
  FILE_POLL: 500,
  SEEK_DEBOUNCE: 100,
  RECONNECT_BASE: 1000,
  MAX_RECONNECT_ATTEMPTS: 5
} as const;

// ── Títulos de módulos ────────────────────────────────────────────────────────
export const MODULE_TITLES = {
  input: '📥 INPUT',
  whisper: '🎙️ WHISPER',
  translator: '🌐 TRANSLATOR',
  tts: '🔊 TTS ENGINE',
  subtitles: '📝 SUBTITLES',
  mixer: '🎚️ AUDIO MIXER',
  muxer: '📼 HLS MUXER',
  outputs: '📤 OUTPUTS'
} as const;

// ── Etiquetas métricas ────────────────────────────────────────────────────────
export const METRIC_LABELS = {
  cpu: 'CPU',
  memory: 'MEMORIA',
  gpu: 'GPU',
  chunks: 'CHUNKS',
  latency: 'LATENCIA'
} as const;

export default {
  SERVER_PORT,
  STORAGE_KEYS,
  MESSAGES,
  DEFAULTS,
  MODULE_STATES,
  INPUT_TYPES,
  OUTPUT_TYPES,
  INTERVALS,
  MODULE_TITLES,
  METRIC_LABELS
};
