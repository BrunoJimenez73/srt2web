/**
 * SRT2Web Internationalization (i18n) System
 * Supports multiple languages for UI labels and messages.
 */

import { STORAGE_KEYS } from "./constants";

// Supported Languages
export const SUPPORTED_LANGUAGES = ["en", "es"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

// Translation type
export type TranslationKey = keyof typeof translations.en;
export type Translations = typeof translations.en;

// Translation dictionaries
export const translations = {
  en: {
    // Connection
    connecting: "Connecting...",
    connected: "Connected",
    disconnected: "Disconnected",
    reconnecting: "Reconnecting...",
    reconnect_failed: "Reconnection failed",

    // Pipeline
    pipeline_starting: "Starting pipeline...",
    pipeline_running: "Pipeline running",
    pipeline_stopping: "Stopping pipeline...",
    pipeline_stopped: "Pipeline stopped",
    pipeline_error: "Pipeline error",
    pipeline_started: "Pipeline started successfully",
    pipeline_confirm_stop: "Are you sure you want to stop the pipeline?",

    // Pipeline UI Status
    status_active: "ACTIVE",
    status_off: "OFF",
    status_starting: "STARTING",
    status_stopping: "STOPPING",
    status_error: "ERROR",

    // Modules
    module_enabled: "Enabled",
    module_disabled: "Disabled",
    module_processing: "Processing...",
    module_idle: "Idle",
    module_error: "Error",
    module_degraded: "Degraded",

    // Module Names
    audio_extractor: "Audio Extractor",
    transcriber: "Transcriber (Whisper)",
    translator: "Translator",
    tts_engine: "Text-to-Speech",
    subtitle_generator: "Subtitle Generator",
    audio_mixer: "Audio Mixer",
    video_muxer: "Video Muxer (HLS)",

    // Module Titles (ProcessGrid)
    module_title_input: "INPUT",
    module_title_whisper: "WHISPER",
    module_title_translator: "TRANSLATOR",
    module_title_tts: "TTS ENGINE",
    module_title_subtitles: "SUBTITLES",
    module_title_mixer: "AUDIO MIXER",
    module_title_muxer: "HLS MUXER",
    module_title_outputs: "OUTPUTS",

    // Actions
    start: "Start",
    stop: "Stop",
    restart: "Restart",
    save: "Save",
    cancel: "Cancel",
    reset: "Reset",
    close: "Close",
    toggle: "Toggle",
    create: "Create",
    delete: "Delete",
    edit: "Edit",
    copy: "Copy",
    retry: "Retry",
    play: "Play",
    pause: "Pause",

    // Status
    running: "Running",
    idle: "Idle",
    waiting: "Waiting...",
    ready: "Ready",
    enabled: "Enabled",
    disabled: "Disabled",

    // Errors
    error: "Error",
    error_generic: "An error occurred",
    error_connection: "Connection error",
    error_timeout: "Request timeout",

    // Metrics
    metrics: "Metrics",
    chunks: "Chunks",
    time: "Time",
    gpu: "GPU",
    cpu: "CPU",
    device: "Device",
    encoder: "Encoder",
    latency: "Latency",
    bitrate: "Bitrate",
    memory: "Memory",
    throughput: "Throughput",
    system_metrics: "System Metrics",

    // Input/Output
    input: "Input",
    output: "Output",
    outputs: "Outputs",
    stream: "Stream",
    url_emision: "Emission URL",
    copy_url: "Copy URL",
    manage_outputs: "Manage Outputs",
    new_output: "New Output",
    stream_url: "Stream URL",
    player_url: "Player URL",

    // Input Types
    srt_input: "SRT Input",
    rtmp_input: "RTMP Input",
    file_input: "File Input",

    // Input Card Labels
    type: "Type",
    srt_port: "SRT Port",
    mode: "Mode",
    chunk: "Chunk (s)",
    chunk_duration: "Chunk Duration",
    latency_ms: "Latency (ms)",
    caller_address: "Caller Address",
    obs_url: "URL for OBS (RTMP Listen)",
    port: "Port",
    app: "App",
    stream_key: "Stream Key",
    video_file_path: "Video File (full path)",
    select_file: "Select File",
    file_hint: "Select a file or type the full path manually",
    loop: "Loop",
    speed: "Speed",
    yes: "Yes",
    no: "No",

    // Forms
    select_option: "Select option...",
    no_options: "No options available",
    segment_duration: "Segment Duration",
    list_size: "List Size",
    original_volume: "Original Volume",
    tts_volume: "TTS Volume",
    dubbed_volume: "Dubbed Volume",

    // Settings
    settings: "Settings",
    configuration: "Configuration",
    security: "Security",
    security_off: "Secure OFF",
    security_on: "Secure ON",

    // Logs
    logs: "Logs",
    search_logs: "Search logs...",
    clear_logs: "Clear Logs",
    no_logs: "No logs available",
    no_logs_yet: "No logs yet",
    log_title: "Logs",
    log_filter_all: "All",
    log_filter_info: "INFO",
    log_filter_warning: "WARNING",
    log_filter_error: "ERROR",
    log_search_placeholder: "Search...",
    log_export_json: "Export JSON",
    log_export_txt: "Export TXT",
    log_clear: "Clear",

    // Player
    player: "Player",
    player_error: "Player Error",
    player_retry: "Retry",

    // Documentation
    docs: "Docs",
    quick_start: "Quick Start",
    guides: "Guides",
    modules: "Modules",

    // Confirmations
    confirm_stop: "Are you sure you want to stop the pipeline?",
    confirm_delete: "Are you sure you want to delete this item?",

    // GPU Status
    gpu_available: "GPU Available",
    gpu_unavailable: "GPU Unavailable",
    using_gpu: "Using GPU",
    using_cpu: "Using CPU",

    // Voice Labels
    voice: "Voice",
    speed_label: "Speed",

    // Language Labels
    source_language: "Source Language",
    target_language: "Target Language",
    language: "Language",
    language_en: "English",
    language_es: "Español",

    // Subtitle Labels
    subtitle_format: "Subtitle Format",
    use_translated: "Use Translated Text",
    audio_offset: "Audio Offset (ms)",
    font_size: "Font Size",

    // Encoder Labels
    encoder_mode: "Encoder Mode",
    video_quality: "Video Quality",
    audio_codec: "Audio Codec",
    audio_bitrate: "Audio Bitrate",

    // Model Labels
    model: "Model",
    language_model: "Language",

    // Recording
    recording: "Recording",
    recording_saved: "Recording saved",

    // Protocol
    protocol: "Protocol",
    port_label: "Port",
    latency_ms_label: "Latency (ms)",
    mode_label: "Mode",
    listener: "Listener",
    caller: "Caller",
    rendezvous: "Rendezvous",

    // Status Card
    local: "LOCAL",
    remote: "REMOTE",
    stop_btn: "Stop",
    start_btn: "Start",
    srt_label: "SRT:",
    rtmp_label: "RTMP:",
    stream_label: "Stream:",
    player_label: "Player:",
    emitter_address_label: "Emitter SRT Address",
    emitter_placeholder: "203.0.113.xx",

    // WebSocket Status
    ws_off: "WS OFF",
    ws_on: "WS ON",
    ws_connected: "Connected to server",
    ws_disconnected: "WebSocket disconnected",
    ws_error: "WebSocket connection error",

    // Security Panel
    auth_token: "Auth Token",
    token_placeholder: "Enter token...",
    token_saved_reload: "Token saved. Reload to apply.",
    auth_disabled: "Authentication disabled.",
    generate_token: "Generate Token",
    save_token: "Save Token",
    close_panel: "Close panel",
    show_hide: "Show/Hide",

    // Header
    save_config: "Save Config",
    live_clock: "Clock",

    // Language Selector
    language_selector: 'Language',

    // Keyboard Shortcuts
    keyboard_shortcuts: 'Keyboard Shortcuts',

    // Pipeline Control Messages
    saving_config: "Saving config...",
    config_saved: "Configuration saved successfully",
    config_save_error: "Error saving configuration",
    config_load_error: "Error loading configuration",
    loading: "Loading...",
    success: "Operation completed successfully",
    warning: "Warning",
    info: "Info",

    // Input Messages
    input_file_selected: "File selected. Enter the full path manually.",
    input_file_play: "Playback resumed",
    input_file_pause: "Playback paused",
    input_file_seek_error: "Error seeking position",

    // URL Copy
    url_copied: "URL copied to clipboard",
    url_copy_error: "Error copying URL",

    // Output Messages
    output_created: "Output created successfully",
    output_removed: "Output removed",
    output_toggled: "Output state updated",

    // Keyboard Shortcuts
    config_saved_shortcut: "Config saved (Ctrl+S)",
    dark_mode_on: "Dark mode activated",
    light_mode_on: "Light mode activated",

    // Presets
    preset_applying: "Applying preset...",
    preset_applied: "Preset applied",
    preset_error: "Error applying preset",
    preset_saving: "Saving preset...",
    preset_saved: "Preset saved",
    preset_save_error: "Error saving preset",
    config_exported: "Config exported",
    config_export_error: "No config to export",

    // Pipeline Control
    pipeline_starting_msg: "Starting pipeline...",
    pipeline_started_msg: "Pipeline started",
    pipeline_stopping_msg: "Stopping pipeline...",
    pipeline_stopped_msg: "Pipeline stopped",
    pipeline_stop_error: "Error stopping pipeline",
    chunk_synced: "Chunk synced",

    // Errors
    error_occurred: "An error occurred",
    init_error: "Initialization error",
    presets_load_error: "Error loading presets",
  },
  es: {
    // Connection
    connecting: "Conectando...",
    connected: "Conectado",
    disconnected: "Desconectado",
    reconnecting: "Reconectando...",
    reconnect_failed: "Reconexión fallida",

    // Pipeline
    pipeline_starting: "Iniciando pipeline...",
    pipeline_running: "Pipeline en ejecución",
    pipeline_stopping: "Deteniendo pipeline...",
    pipeline_stopped: "Pipeline detenido",
    pipeline_error: "Error en pipeline",
    pipeline_started: "Pipeline iniciado correctamente",
    pipeline_confirm_stop: "¿Estás seguro de que quieres detener el pipeline?",

    // Pipeline UI Status
    status_active: "ACTIVO",
    status_off: "APAGADO",
    status_starting: "INICIANDO",
    status_stopping: "DETENIENDO",
    status_error: "ERROR",

    // Modules
    module_enabled: "Habilitado",
    module_disabled: "Deshabilitado",
    module_processing: "Procesando...",
    module_idle: "Inactivo",
    module_error: "Error",
    module_degraded: "Degradado",

    // Module Names
    audio_extractor: "Extractor de Audio",
    transcriber: "Transcriptor (Whisper)",
    translator: "Traductor",
    tts_engine: "Texto a Voz",
    subtitle_generator: "Generador de Subtítulos",
    audio_mixer: "Mezclador de Audio",
    video_muxer: "Muxer de Video (HLS)",

    // Module Titles (ProcessGrid)
    module_title_input: "INPUT",
    module_title_whisper: "WHISPER",
    module_title_translator: "TRADUCTOR",
    module_title_tts: "TTS",
    module_title_subtitles: "SUBTÍTULOS",
    module_title_mixer: "MEZCLADOR",
    module_title_muxer: "MUXER HLS",
    module_title_outputs: "SALIDAS",

    // Actions
    start: "Iniciar",
    stop: "Detener",
    restart: "Reiniciar",
    save: "Guardar",
    cancel: "Cancelar",
    reset: "Restablecer",
    close: "Cerrar",
    toggle: "Alternar",
    create: "Crear",
    delete: "Eliminar",
    edit: "Editar",
    copy: "Copiar",
    retry: "Reintentar",
    play: "Reproducir",
    pause: "Pausar",

    // Status
    running: "Ejecutando",
    idle: "Inactivo",
    waiting: "Esperando...",
    ready: "Listo",
    enabled: "Habilitado",
    disabled: "Deshabilitado",

    // Errors
    error: "Error",
    error_generic: "Ocurrió un error",
    error_connection: "Error de conexión",
    error_timeout: "Tiempo de espera agotado",

    // Metrics
    metrics: "Métricas",
    chunks: "Fragmentos",
    time: "Tiempo",
    gpu: "GPU",
    cpu: "CPU",
    device: "Dispositivo",
    encoder: "Codificador",
    latency: "Latencia",
    bitrate: "Bitrate",
    memory: "Memoria",
    throughput: "Rendimiento",
    system_metrics: "Métricas del Sistema",

    // Input/Output
    input: "Entrada",
    output: "Salida",
    outputs: "Salidas",
    stream: "Stream",
    url_emision: "URL de Emisión",
    copy_url: "Copiar URL",
    manage_outputs: "Gestionar Salidas",
    new_output: "Nueva Salida",
    stream_url: "URL del Stream",
    player_url: "URL del Player",

    // Input Types
    srt_input: "Entrada SRT",
    rtmp_input: "Entrada RTMP",
    file_input: "Entrada de Archivo",

    // Input Card Labels
    type: "Tipo",
    srt_port: "Puerto SRT",
    mode: "Modo",
    chunk: "Chunk (s)",
    chunk_duration: "Duración de Fragmento",
    latency_ms: "Latencia (ms)",
    caller_address: "Dirección Caller",
    obs_url: "URL para OBS (RTMP Listen)",
    port: "Puerto",
    app: "App",
    stream_key: "Stream Key",
    video_file_path: "Archivo de Video (ruta completa)",
    select_file: "Seleccionar Archivo",
    file_hint: "Selecciona un archivo o escribe la ruta completa manualmente",
    loop: "Loop",
    speed: "Velocidad",
    yes: "Sí",
    no: "No",

    // Forms
    select_option: "Seleccionar opción...",
    no_options: "Sin opciones disponibles",
    segment_duration: "Duración de Segmento",
    list_size: "Tamaño de Lista",
    original_volume: "Volumen Original",
    tts_volume: "Volumen TTS",
    dubbed_volume: "Volumen Doblado",

    // Settings
    settings: "Configuración",
    configuration: "Configuración",
    security: "Seguridad",
    security_off: "Seguridad OFF",
    security_on: "Seguridad ON",

    // Logs
    logs: "Registros",
    search_logs: "Buscar registros...",
    clear_logs: "Limpiar Registros",
    no_logs: "Sin registros disponibles",
    no_logs_yet: "Sin registros aún",
    log_title: "Registros",
    log_filter_all: "Todos",
    log_filter_info: "INFO",
    log_filter_warning: "ADVERTENCIA",
    log_filter_error: "ERROR",
    log_search_placeholder: "Buscar...",
    log_export_json: "Exportar JSON",
    log_export_txt: "Exportar TXT",
    log_clear: "Limpiar",

    // Player
    player: "Reproductor",
    player_error: "Error del Reproductor",
    player_retry: "Reintentar",

    // Documentation
    docs: "Docs",
    quick_start: "Inicio Rápido",
    guides: "Guías",
    modules: "Módulos",

    // Confirmations
    confirm_stop: "¿Estás seguro de que quieres detener el pipeline?",
    confirm_delete: "¿Estás seguro de que quieres eliminar este elemento?",

    // GPU Status
    gpu_available: "GPU Disponible",
    gpu_unavailable: "GPU No Disponible",
    using_gpu: "Usando GPU",
    using_cpu: "Usando CPU",

    // Voice Labels
    voice: "Voz",
    speed_label: "Velocidad",

    // Language Labels
    source_language: "Idioma de Origen",
    target_language: "Idioma de Destino",
    language: "Idioma",
    language_en: "English",
    language_es: "Español",

    // Subtitle Labels
    subtitle_format: "Formato de Subtítulos",
    use_translated: "Usar Texto Traducido",
    audio_offset: "Offset de Audio (ms)",
    font_size: "Tamaño de Fuente",

    // Encoder Labels
    encoder_mode: "Modo de Codificador",
    video_quality: "Calidad de Video",
    audio_codec: "Codec de Audio",
    audio_bitrate: "Bitrate de Audio",

    // Model Labels
    model: "Modelo",
    language_model: "Idioma",

    // Recording
    recording: "Grabación",
    recording_saved: "Grabación guardada",

    // Protocol
    protocol: "Protocolo",
    port_label: "Puerto",
    latency_ms_label: "Latencia (ms)",
    mode_label: "Modo",
    listener: "Escucha",
    caller: "Llamador",
    rendezvous: "Rendezvous",

    // Status Card
    local: "LOCAL",
    remote: "REMOTO",
    stop_btn: "Detener",
    start_btn: "Iniciar",
    srt_label: "SRT:",
    rtmp_label: "RTMP:",
    stream_label: "Stream:",
    player_label: "Player:",
    emitter_address_label: "Dirección del Emisor SRT",
    emitter_placeholder: "203.0.113.xx",

    // WebSocket Status
    ws_off: "WS OFF",
    ws_on: "WS ON",
    ws_connected: "Conectado al servidor",
    ws_disconnected: "WebSocket desconectado",
    ws_error: "Error de conexión WebSocket",

    // Security Panel
    auth_token: "Token de Autenticación",
    token_placeholder: "Ingresa token...",
    token_saved_reload: "Token guardado. Recarga para aplicar.",
    auth_disabled: "Autenticación desactivada.",
    generate_token: "Generar Token",
    save_token: "Guardar Token",
    close_panel: "Cerrar panel",
    show_hide: "Mostrar/Ocultar",

    // Header
    save_config: "Guardar Config",
    live_clock: "Reloj",

    // Language Selector
    language_selector: 'Idioma',

    // Keyboard Shortcuts
    keyboard_shortcuts: 'Atajos de Teclado',

    // Pipeline Control Messages
    saving_config: "Guardando configuración...",
    config_saved: "Configuración guardada correctamente",
    config_save_error: "Error al guardar configuración",
    config_load_error: "Error al cargar configuración",
    loading: "Cargando...",
    success: "Operación completada correctamente",
    warning: "Advertencia",
    info: "Información",

    // Input Messages
    input_file_selected:
      "Archivo seleccionado. Ingresa la ruta completa manualmente.",
    input_file_play: "Reproducción reanudada",
    input_file_pause: "Reproducción pausada",
    input_file_seek_error: "Error al buscar posición",

    // URL Copy
    url_copied: "URL copiada al portapapeles",
    url_copy_error: "Error al copiar URL",

    // Output Messages
    output_created: "Salida creada correctamente",
    output_removed: "Salida eliminada",
    output_toggled: "Estado de salida actualizado",

    // Keyboard Shortcuts
    config_saved_shortcut: "Configuración guardada (Ctrl+S)",
    dark_mode_on: "Modo oscuro activado",
    light_mode_on: "Modo claro activado",

    // Presets
    preset_applying: "Aplicando preset...",
    preset_applied: "Preset aplicado",
    preset_error: "Error al aplicar preset",
    preset_saving: "Guardando preset...",
    preset_saved: "Preset guardado",
    preset_save_error: "Error al guardar preset",
    config_exported: "Configuración exportada",
    config_export_error: "No hay configuración para exportar",

    // Pipeline Control
    pipeline_starting_msg: "Iniciando pipeline...",
    pipeline_started_msg: "Pipeline iniciado",
    pipeline_stopping_msg: "Deteniendo pipeline...",
    pipeline_stopped_msg: "Pipeline detenido",
    pipeline_stop_error: "Error al detener pipeline",
    chunk_synced: "Chunk sincronizado",

    // Errors
    error_occurred: "Ha ocurrido un error",
    init_error: "Error de inicialización",
    presets_load_error: "Error al cargar presets",
  },
} as const;

// Current language state
let currentLanguage: Language = "en";

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
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEYS.LANGUAGE, lang);
  }
}

/**
 * Initialize language from localStorage
 */
export function initLanguage(): Language {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(
      STORAGE_KEYS.LANGUAGE,
    ) as Language | null;
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
