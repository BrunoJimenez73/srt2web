/**
 * SRT2Web Frontend Constants
 * All hardcoded values should be defined here.
 */

// Server Configuration
export const SERVER_HOST = 'localhost';
export const SERVER_PORT = 9999;
export const SRT_PORT = 9000;
export const RTMP_PORT = 1935;

// API Configuration
export const API_BASE_PATH = '/api';
export const WS_BASE_PATH = '/ws';

// API Endpoints
export const API_ENDPOINTS = {
  STATUS: `${API_BASE_PATH}/status`,
  START: `${API_BASE_PATH}/start`,
  STOP: `${API_BASE_PATH}/stop`,
  RESTART: `${API_BASE_PATH}/restart`,
  CONFIG: `${API_BASE_PATH}/config`,
  MODULES: `${API_BASE_PATH}/modules`,
  MODULES_TOGGLE: (name: string) => `${API_BASE_PATH}/modules/${name}/toggle`,
  MODULES_DEBUG: (name: string) => `${API_BASE_PATH}/modules/${name}/debug`,
  INPUT_INFO: `${API_BASE_PATH}/input-info`,
  INPUT_CONTROL: (action: string) => `${API_BASE_PATH}/input/control/${action}`,
  OUTPUT_INFO: `${API_BASE_PATH}/output-info`,
  OUTPUTS: `${API_BASE_PATH}/outputs`,
  OUTPUTS_AVAILABLE: `${API_BASE_PATH}/outputs/available`,
  OUTPUTS_TOGGLE: (name: string) => `${API_BASE_PATH}/outputs/${name}/toggle`,
  HEALTH: `${API_BASE_PATH}/health`,
  NETWORK_INFO: `${API_BASE_PATH}/network/info`,
  SRT_INFO: `${API_BASE_PATH}/srt-info`,
  AVAILABLE: `${API_BASE_PATH}/available`,
} as const;

// WebSocket Paths
export const WS_PATHS = {
  LOGS: `${WS_BASE_PATH}/logs`,
  STATUS: `${WS_BASE_PATH}/status`,
} as const;

// Stream URLs
export const DEFAULT_STREAM_URLS = {
  SRT: (port: number = SRT_PORT) => `srt://localhost:${port}`,
  RTMP: 'rtmp://localhost/live/stream',
} as const;

// HLS Configuration
export const HLS_PATH = '/hls';
export const HLS_PLAYLIST = 'stream.m3u8';
export const HLS_FULL_PATH = `${HLS_PATH}/${HLS_PLAYLIST}`;

// Input Types
export const INPUT_TYPES = {
  SRT: 'srt',
  RTMP: 'rtmp',
  FILE: 'file',
} as const;

// Output Types
export const OUTPUT_TYPES = {
  HLS: 'hls',
  RECORDING: 'recording',
  WEBRTC: 'webrtc',
} as const;

// Module Names
export const MODULE_NAMES = {
  AUDIO_EXTRACTOR: 'audio_extractor',
  TRANSCRIBER: 'transcriber',
  TRANSLATOR: 'translator',
  TTS_ENGINE: 'tts_engine',
  SUBTITLE_GENERATOR: 'subtitle_generator',
  AUDIO_MIXER: 'audio_mixer',
  VIDEO_MUXER: 'video_muxer',
} as const;

// Whisper Models
export const WHISPER_MODELS = [
  'tiny',
  'base',
  'small',
  'medium',
  'large-v3',
  'large-v3-turbo',
] as const;

// TTS Engines
export const TTS_ENGINES = ['edge', 'piper'] as const;

// Encoder Modes
export const ENCODER_MODES = ['copy', 'encode', 'nvenc', 'qsv', 'amf'] as const;

// Device Options
export const DEVICE_OPTIONS = ['auto', 'cpu', 'cuda', 'mps'] as const;

// Subtitle Formats
export const SUBTITLE_FORMATS = ['webvtt', 'srt', 'ass'] as const;

// Audio Bitrates
export const AUDIO_BITRATES = [
  '64k',
  '96k',
  '128k',
  '192k',
  '256k',
  '320k',
] as const;

// External URLs
export const EXTERNAL_URLS = {
  GOOGLE_FONTS: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap',
  HLS_JS: 'https://cdn.jsdelivr.net/npm/hls.js@1.5.7/dist/hls.min.js',
} as const;

// LocalStorage Keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'srt2web_auth_token',
  THEME: 'srt2web_theme',
  LANGUAGE: 'srt2web_language',
  DASHBOARD_STATE: 'srt2web_dashboard_state',
} as const;

// WebSocket Configuration
export const WS_CONFIG = {
  PING_INTERVAL: 30000,
  RECONNECT_DELAY: 1000,
  MAX_RECONNECTS: 10,
  TIMEOUT: 300000,
} as const;

// Animation Durations (ms)
export const ANIMATION = {
  FAST: 150,
  NORMAL: 300,
  SLOW: 500,
} as const;

// Localized Messages (English - default)
export const MESSAGES = {
  // Connection
  CONNECTING: 'Connecting...',
  CONNECTED: 'Connected',
  DISCONNECTED: 'Disconnected',
  RECONNECTING: 'Reconnecting...',
  RECONNECT_FAILED: 'Reconnection failed',

  // Pipeline
  PIPELINE_STARTING: 'Starting pipeline...',
  PIPELINE_RUNNING: 'Pipeline running',
  PIPELINE_STOPPING: 'Stopping pipeline...',
  PIPELINE_STOPPED: 'Pipeline stopped',
  PIPELINE_ERROR: 'Pipeline error',

  // Modules
  MODULE_ENABLED: 'Enabled',
  MODULE_DISABLED: 'Disabled',
  MODULE_PROCESSING: 'Processing...',
  MODULE_IDLE: 'Idle',
  MODULE_ERROR: 'Error',

  // Actions
  START: 'Start',
  STOP: 'Stop',
  RESTART: 'Restart',
  SAVE: 'Save',
  CANCEL: 'Cancel',
  RESET: 'Reset',
  CLOSE: 'Close',

  // Status
  RUNNING: 'Running',
  IDLE: 'Idle',
  WAITING: 'Waiting...',
  READY: 'Ready',

  // Errors
  ERROR: 'Error',
  ERROR_GENERIC: 'An error occurred',
  ERROR_CONNECTION: 'Connection error',
  ERROR_TIMEOUT: 'Request timeout',

  // Metrics
  CHUNKS: 'Chunks',
  TIME: 'Time',
  GPU: 'GPU',
  CPU: 'CPU',
  DEVICE: 'Device',
  ENCODER: 'Encoder',

  // Input/Output
  INPUT: 'Input',
  OUTPUT: 'Output',
  STREAM: 'Stream',
  URL_EMISION: 'Emission URL',
  COPY_URL: 'Copy URL',

  // Forms
  SELECT_OPTION: 'Select option...',
  NO_OPTIONS: 'No options available',
} as const;

// Type exports
export type EndpointKey = keyof typeof API_ENDPOINTS;
export type WsPathKey = keyof typeof WS_PATHS;
export type InputType = (typeof INPUT_TYPES)[keyof typeof INPUT_TYPES];
export type OutputType = (typeof OUTPUT_TYPES)[keyof typeof OUTPUT_TYPES];
export type ModuleName = (typeof MODULE_NAMES)[keyof typeof MODULE_NAMES];
export type WhisperModel = (typeof WHISPER_MODELS)[number];
export type TtsEngine = (typeof TTS_ENGINES)[number];
export type EncoderMode = (typeof ENCODER_MODES)[number];
export type DeviceOption = (typeof DEVICE_OPTIONS)[number];
export type SubtitleFormat = (typeof SUBTITLE_FORMATS)[number];
export type AudioBitrate = (typeof AUDIO_BITRATES)[number];