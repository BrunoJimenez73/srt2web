export interface ServerConfig {
  host: string;
  port: number;
}

export interface InputSRTConfig {
  listen_port: number;
  mode: string;
  latency_ms?: number;
  caller_address?: string;
}

export interface InputConfig {
  srt?: InputSRTConfig;
  type?: string; // 'srt' | 'rtmp' | 'file'
  rtmp?: {
    url?: string;
    mode?: string;
  };
  file?: {
    path?: string;
    loop?: boolean;
    speed?: number;
  };
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
  engine?: string; // 'edge-tts' | 'piper'
  device?: string; // 'auto' | 'cuda' | 'cpu'
}

export interface AudioMixerConfig {
  enabled: boolean;
  original_volume: number;
  dubbed_volume: number;
  tts_volume?: number;
}

export interface VideoMuxerConfig {
  enabled: boolean;
  engine?: string; // 'hls' | 'webrtc'
  hls_segment_duration: number;
  hls_list_size: number;
  audio_offset_ms: number;
  encoder_mode: string;
  video_quality: string;
  video_crf: number;
  audio_codec: string;
  audio_bitrate: string;
  audio_samplerate: string;
  // WebRTC specific settings
  video_codec?: string;
  video_bitrate?: string;
  video_width?: number;
  video_height?: number;
  video_fps?: number;
  audio_sample_rate?: number;
  webrtc_audio_codec?: string;
  webrtc_audio_bitrate?: string;
}

export interface ModulesConfig {
  transcriber: TranscriberConfig;
  translator: TranslatorConfig;
  subtitle_generator: SubtitleGeneratorConfig;
  tts_engine: TTSEngineConfig;
  audio_mixer: AudioMixerConfig;
  video_muxer: VideoMuxerConfig;
}

export interface OutputConfig {
  type?: string;
  srt?: {
    url?: string;
    mode?: string;
    latency_ms?: number;
    video_bitrate?: string;
    audio_bitrate?: string;
  };
  rtmp?: {
    url?: string;
    video_bitrate?: string;
    audio_bitrate?: string;
    encoder_mode?: string;
  };
  file?: {
    path?: string;
    save_video?: boolean;
    save_audio?: boolean;
    save_subtitles?: boolean;
  };
  web?: {
    segment_duration?: number;
    list_size?: number;
  };
}

export interface PipelineConfig {
  chunk_duration_sec?: number;
  enabled_modules?: string[];
}

export interface Config {
  server: ServerConfig;
  input: InputConfig;
  modules: ModulesConfig;
  output?: OutputConfig;
  pipeline?: PipelineConfig;
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
  extra?: ModuleExtra;
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
  input_receiving?: boolean;
  output_info?: {
    streaming?: boolean;
    [key: string]: any;
  };
  input_info?: {
    port?: number;
    listen_port?: number;
    type?: string;
    path?: string;
    [key: string]: any;
  };
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

// Window interface extensions
declare global {
  interface Window {
    handleEngineChange?: (engine: string) => void;
    handleInputTypeChange: (type: string) => void;
    handleOutputFormatChange: (format: string) => void;
    saveConfig: () => void;
    updateInputFields: () => void;
    toggleModule: (moduleName: string, enabled: boolean) => Promise<void>;
    showToast: (message: string, type?: 'success' | 'error' | 'info', duration?: number) => void;
  }
}

// Debounce timeout record
export type ConfigUpdateTimeouts = Record<string, ReturnType<typeof setTimeout>>;
