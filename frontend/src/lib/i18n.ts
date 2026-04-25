/**
 * SRT2Web Internationalization (i18n) System
 * Supports multiple languages for UI labels and messages.
 */

import { STORAGE_KEYS } from './constants';

// Supported Languages
export const SUPPORTED_LANGUAGES = ['en', 'es'] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

// Translation type
export type TranslationKey = keyof typeof translations.en;
export type Translations = typeof translations.en;

// Translation dictionaries
export const translations = {
  en: {
    // Connection
    connecting: 'Connecting...',
    connected: 'Connected',
    disconnected: 'Disconnected',
    reconnecting: 'Reconnecting...',
    reconnect_failed: 'Reconnection failed',

    // Pipeline
    pipeline_starting: 'Starting pipeline...',
    pipeline_running: 'Pipeline running',
    pipeline_stopping: 'Stopping pipeline...',
    pipeline_stopped: 'Pipeline stopped',
    pipeline_error: 'Pipeline error',

    // Modules
    module_enabled: 'Enabled',
    module_disabled: 'Disabled',
    module_processing: 'Processing...',
    module_idle: 'Idle',
    module_error: 'Error',

    // Module Names
    audio_extractor: 'Audio Extractor',
    transcriber: 'Transcriber (Whisper)',
    translator: 'Translator',
    tts_engine: 'Text-to-Speech',
    subtitle_generator: 'Subtitle Generator',
    audio_mixer: 'Audio Mixer',
    video_muxer: 'Video Muxer (HLS)',

    // Actions
    start: 'Start',
    stop: 'Stop',
    restart: 'Restart',
    save: 'Save',
    cancel: 'Cancel',
    reset: 'Reset',
    close: 'Close',
    toggle: 'Toggle',
    create: 'Create',
    delete: 'Delete',
    edit: 'Edit',
    copy: 'Copy',
    retry: 'Retry',

    // Status
    running: 'Running',
    idle: 'Idle',
    waiting: 'Waiting...',
    ready: 'Ready',
    enabled: 'Enabled',
    disabled: 'Disabled',

    // Errors
    error: 'Error',
    error_generic: 'An error occurred',
    error_connection: 'Connection error',
    error_timeout: 'Request timeout',

    // Metrics
    chunks: 'Chunks',
    time: 'Time',
    gpu: 'GPU',
    cpu: 'CPU',
    device: 'Device',
    encoder: 'Encoder',
    latency: 'Latency',
    bitrate: 'Bitrate',

    // Input/Output
    input: 'Input',
    output: 'Output',
    outputs: 'Outputs',
    stream: 'Stream',
    url_emision: 'Emission URL',
    copy_url: 'Copy URL',
    manage_outputs: 'Manage Outputs',
    new_output: 'New Output',

    // Input Types
    srt_input: 'SRT Input',
    rtmp_input: 'RTMP Input',
    file_input: 'File Input',

    // Forms
    select_option: 'Select option...',
    no_options: 'No options available',
    chunk_duration: 'Chunk Duration',
    segment_duration: 'Segment Duration',
    list_size: 'List Size',
    original_volume: 'Original Volume',
    tts_volume: 'TTS Volume',
    dubbed_volume: 'Dubbed Volume',

    // Settings
    settings: 'Settings',
    configuration: 'Configuration',
    security: 'Security',
    security_off: 'Security OFF',
    security_on: 'Security ON',

    // Logs
    logs: 'Logs',
    search_logs: 'Search logs...',
    clear_logs: 'Clear Logs',
    no_logs: 'No logs available',

    // Player
    player: 'Player',
    player_error: 'Player Error',
    player_retry: 'Retry',

    // Documentation
    docs: 'Documentation',
    quick_start: 'Quick Start',
    guides: 'Guides',
    modules: 'Modules',

    // Confirmations
    confirm_stop: 'Are you sure you want to stop the pipeline?',
    confirm_delete: 'Are you sure you want to delete this item?',

    // GPU Status
    gpu_available: 'GPU Available',
    gpu_unavailable: 'GPU Unavailable',
    using_gpu: 'Using GPU',
    using_cpu: 'Using CPU',

    // Voice Labels
    voice: 'Voice',
    speed: 'Speed',

    // Language Labels
    source_language: 'Source Language',
    target_language: 'Target Language',

    // Subtitle Labels
    subtitle_format: 'Subtitle Format',
    use_translated: 'Use Translated Text',
    audio_offset: 'Audio Offset (ms)',
    font_size: 'Font Size',

    // Encoder Labels
    encoder_mode: 'Encoder Mode',
    video_quality: 'Video Quality',
    audio_codec: 'Audio Codec',
    audio_bitrate: 'Audio Bitrate',

    // Model Labels
    model: 'Model',
    language: 'Language',

    // Recording
    recording: 'Recording',
    recording_saved: 'Recording saved',

    // Protocol
    protocol: 'Protocol',
    port: 'Port',
    latency_ms: 'Latency (ms)',
    mode: 'Mode',
    listener: 'Listener',
    caller: 'Caller',
  },
  es: {
    // Connection
    connecting: 'Conectando...',
    connected: 'Conectado',
    disconnected: 'Desconectado',
    reconnecting: 'Reconectando...',
    reconnect_failed: 'Reconexion fallida',

    // Pipeline
    pipeline_starting: 'Iniciando pipeline...',
    pipeline_running: 'Pipeline en ejecucion',
    pipeline_stopping: 'Deteniendo pipeline...',
    pipeline_stopped: 'Pipeline detenido',
    pipeline_error: 'Error en pipeline',

    // Modules
    module_enabled: 'Habilitado',
    module_disabled: 'Deshabilitado',
    module_processing: 'Procesando...',
    module_idle: 'Inactivo',
    module_error: 'Error',

    // Module Names
    audio_extractor: 'Extractor de Audio',
    transcriber: 'Transcriptor (Whisper)',
    translator: 'Traductor',
    tts_engine: 'Texto a Voz',
    subtitle_generator: 'Generador de Subtitulos',
    audio_mixer: 'Mezclador de Audio',
    video_muxer: 'Muxer de Video (HLS)',

    // Actions
    start: 'Iniciar',
    stop: 'Detener',
    restart: 'Reiniciar',
    save: 'Guardar',
    cancel: 'Cancelar',
    reset: 'Restablecer',
    close: 'Cerrar',
    toggle: 'Alternar',
    create: 'Crear',
    delete: 'Eliminar',
    edit: 'Editar',
    copy: 'Copiar',
    retry: 'Reintentar',

    // Status
    running: 'Ejecutando',
    idle: 'Inactivo',
    waiting: 'Esperando...',
    ready: 'Listo',
    enabled: 'Habilitado',
    disabled: 'Deshabilitado',

    // Errors
    error: 'Error',
    error_generic: 'Ocurrio un error',
    error_connection: 'Error de conexion',
    error_timeout: 'Tiempo de espera agotado',

    // Metrics
    chunks: 'Fragmentos',
    time: 'Tiempo',
    gpu: 'GPU',
    cpu: 'CPU',
    device: 'Dispositivo',
    encoder: 'Codificador',
    latency: 'Latencia',
    bitrate: 'Bitrate',

    // Input/Output
    input: 'Entrada',
    output: 'Salida',
    outputs: 'Salidas',
    stream: 'Stream',
    url_emision: 'URL de Emision',
    copy_url: 'Copiar URL',
    manage_outputs: 'Gestionar Salidas',
    new_output: 'Nueva Salida',

    // Input Types
    srt_input: 'Entrada SRT',
    rtmp_input: 'Entrada RTMP',
    file_input: 'Entrada de Archivo',

    // Forms
    select_option: 'Seleccionar opcion...',
    no_options: 'Sin opciones disponibles',
    chunk_duration: 'Duracion de Fragmento',
    segment_duration: 'Duracion de Segmento',
    list_size: 'Tamano de Lista',
    original_volume: 'Volumen Original',
    tts_volume: 'Volumen TTS',
    dubbed_volume: 'Volumen Doblado',

    // Settings
    settings: 'Configuracion',
    configuration: 'Configuracion',
    security: 'Seguridad',
    security_off: 'Seguridad OFF',
    security_on: 'Seguridad ON',

    // Logs
    logs: 'Registros',
    search_logs: 'Buscar registros...',
    clear_logs: 'Limpiar Registros',
    no_logs: 'Sin registros disponibles',

    // Player
    player: 'Reproductor',
    player_error: 'Error del Reproductor',
    player_retry: 'Reintentar',

    // Documentation
    docs: 'Documentacion',
    quick_start: 'Inicio Rapido',
    guides: 'Guias',
    modules: 'Modulos',

    // Confirmations
    confirm_stop: 'Estas seguro de que quieres detener el pipeline?',
    confirm_delete: 'Estas seguro de que quieres eliminar este elemento?',

    // GPU Status
    gpu_available: 'GPU Disponible',
    gpu_unavailable: 'GPU No Disponible',
    using_gpu: 'Usando GPU',
    using_cpu: 'Usando CPU',

    // Voice Labels
    voice: 'Voz',
    speed: 'Velocidad',

    // Language Labels
    source_language: 'Idioma de Origen',
    target_language: 'Idioma de Destino',

    // Subtitle Labels
    subtitle_format: 'Formato de Subtitulos',
    use_translated: 'Usar Texto Traducido',
    audio_offset: 'Offset de Audio (ms)',
    font_size: 'Tamano de Fuente',

    // Encoder Labels
    encoder_mode: 'Modo de Codificador',
    video_quality: 'Calidad de Video',
    audio_codec: 'Codec de Audio',
    audio_bitrate: 'Bitrate de Audio',

    // Model Labels
    model: 'Modelo',
    language: 'Idioma',

    // Recording
    recording: 'Grabacion',
    recording_saved: 'Grabacion guardada',

    // Protocol
    protocol: 'Protocolo',
    port: 'Puerto',
    latency_ms: 'Latencia (ms)',
    mode: 'Modo',
    listener: 'Escucha',
    caller: 'Llamador',
  },
} as const;

// Current language state
let currentLanguage: Language = 'en';

/**
 * Get the current language
 */
export function getCurrentLanguage(): Language {
  return currentLanguage;
}

/**
 * Set the current language and persist to localStorage
 */
export function setCurrentLanguage(lang: Language): void {
  currentLanguage = lang;
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEYS.LANGUAGE, lang);
  }
}

/**
 * Initialize language from localStorage
 */
export function initLanguage(): Language {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEYS.LANGUAGE) as Language | null;
    if (stored && SUPPORTED_LANGUAGES.includes(stored)) {
      currentLanguage = stored;
    }
  }
  return currentLanguage;
}

/**
 * Get a translation by key
 */
export function t(key: TranslationKey): string {
  return translations[currentLanguage][key] || translations.en[key] || key;
}

/**
 * Get translation with fallback
 */
export function tFallback(key: TranslationKey, fallback: string): string {
  return translations[currentLanguage][key] || fallback;
}

/**
 * Create a reactive store for language changes
 * Usage: const lang = useLanguage(); then use lang.current
 */
export function createLanguageStore() {
  const listeners: Set<(lang: Language) => void> = new Set();

  return {
    get current() {
      return currentLanguage;
    },
    set(lang: Language) {
      setCurrentLanguage(lang);
      listeners.forEach((fn) => fn(lang));
    },
    subscribe(fn: (lang: Language) => void) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}

// Export for framework integration
export const languageStore = createLanguageStore();

// Vue/React-like useLanguage hook pattern (for vanilla JS)
export function useLanguage() {
  return {
    current: currentLanguage,
    t,
    set: (lang: Language) => languageStore.set(lang),
  };
}

// Shorthand for templates: _('key') instead of t('key')
export const _ = t;