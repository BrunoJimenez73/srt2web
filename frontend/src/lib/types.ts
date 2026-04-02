export interface ServerConfig {
  host: string;
  port: number;
}

export interface InputSRTConfig {
  listen_port: number;
  mode: string;
}

export interface InputConfig {
  srt: InputSRTConfig;
}

export interface TranscriberConfig {
  enabled: boolean;
  model: string;
  language: string;
  device: string;
}

export interface TranslatorConfig {
  enabled: boolean;
  source_lang: string;
  target_lang: string;
}

export interface SubtitleGeneratorConfig {
  enabled: boolean;
  format: string;
  use_translated: boolean;
}

export interface TTSEngineConfig {
  enabled: boolean;
  voice: string;
  speed: number;
}

export interface AudioMixerConfig {
  enabled: boolean;
  original_volume: number;
  dubbed_volume: number;
}

export interface VideoMuxerConfig {
  enabled: boolean;
  hls_segment_duration: number;
  hls_list_size: number;
  audio_offset_ms: number;
  encoder_mode: string;
  video_quality: string;
  video_crf: number;
  audio_codec: string;
  audio_bitrate: string;
  audio_samplerate: string;
}

export interface ModulesConfig {
  transcriber: TranscriberConfig;
  translator: TranslatorConfig;
  subtitle_generator: SubtitleGeneratorConfig;
  tts_engine: TTSEngineConfig;
  audio_mixer: AudioMixerConfig;
  video_muxer: VideoMuxerConfig;
}

export interface Config {
  server: ServerConfig;
  input: InputConfig;
  modules: ModulesConfig;
}

export interface ModuleStatus {
  name: string;
  state: 'idle' | 'running' | 'error' | 'disabled';
  enabled: boolean;
  error_message?: string;
  processed_chunks: number;
  last_process_time_ms: number;
  circuit_state?: string;
  memory_mb?: number;
}

export interface NetworkInfo {
  local_ip: string;
}

export interface SystemMetrics {
  cpu_percent: number;
  memory_mb: number;
  memory_percent: number;
  gpu_percent: number;
  gpu_memory_mb: number;
  gpu_available: boolean;
  available: boolean;
}

export interface Status {
  state: 'idle' | 'running' | 'stopping';
  network?: NetworkInfo;
  modules?: ModuleStatus[];
  chunks_processed?: number;
  system?: SystemMetrics;
}

export type LogLevel = 'info' | 'warning' | 'error' | 'success';

export interface LogMessage {
  level: LogLevel;
  message: string;
  timestamp?: string;
}

export type ModuleName = 
  | 'srt_ingest' 
  | 'audio_extractor' 
  | 'transcriber' 
  | 'translator' 
  | 'subtitle_generator' 
  | 'tts_engine' 
  | 'audio_mixer' 
  | 'video_muxer';

export interface ModuleMapping {
  card: string;
  indicator: string;
}

// Module extra information from backend
export interface ModuleExtra {
  using_gpu?: boolean;
  device?: string;
  engine?: string;
  encoder_mode?: string;
  compute_type?: string;
}

// Extended ModuleStatus with extra field
export interface ModuleStatusExtended extends ModuleStatus {
  extra?: ModuleExtra;
}

// UI Element IDs
export type CardId = 
  | 'card-input' 
  | 'card-whisper' 
  | 'card-translate' 
  | 'card-tts' 
  | 'card-subtitle' 
  | 'card-audio-mixer'
  | 'card-video-muxer'
  | 'card-output';

export type IndicatorId = 
  | 'indicator-input' 
  | 'indicator-whisper' 
  | 'indicator-translate' 
  | 'indicator-tts' 
  | 'indicator-subtitle'
  | 'indicator-audio-mixer'
  | 'indicator-video-muxer'
  | 'indicator-output';

// Toast notification types
export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastMessage {
  message: string;
  type: ToastType;
  duration?: number;
}

// Dashboard state
export interface DashboardState {
  config: Config | null;
  status: Status | null;
  localMode: 'local' | 'remote';
  isConnected: boolean;
}

// Debounce timeout record
export type ConfigUpdateTimeouts = Record<string, ReturnType<typeof setTimeout>>;
