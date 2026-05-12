/**
 * API Types - Todos los tipos relacionados con la API del backend.
 * 
 * Este archivo centraliza todas las definiciones de tipos para la API.
 */

// ── Tipos de API ────────────────────────────────────────────────────────────────

export interface ApiResponse<T = unknown> {
  data?: T;
  error?: string;
}

export interface ConfigUpdateResponse {
  status: 'updated';
  config: Config;
  warning?: string;
}

export interface PipelineStartResponse {
  status: 'started';
  input: Record<string, unknown>;
}

export interface PipelineStopResponse {
  status: 'stopped';
}

export interface ModuleToggleResponse {
  module: string;
  enabled: boolean;
  status: ModuleStatus;
  hot_reload?: boolean;
  warning?: string;
  error?: string;
}

export interface ModuleStatus {
  name: string;
  state: ModuleState;
  enabled: boolean;
  last_process_time_ms: number;
  processed_chunks?: number;
  memory_mb?: number;
  extra?: ModuleExtra;
}

export type ModuleName = 'input' | 'whisper' | 'translator' | 'tts' | 'subtitles' | 'mixer' | 'muxer' | 'outputs';

export type LogLevel = 'INFO' | 'WARNING' | 'ERROR';

export interface LogMessage {
  level: LogLevel;
  message: string;
  timestamp: string;
  module?: ModuleName;
}

export type ModuleState = 'idle' | 'running' | 'error' | 'stopped' | 'degraded' | 'disabled';

export interface ModuleExtra {
  using_gpu?: boolean;
  device?: string;
  encoder_mode?: string;
  compute_type?: string;
  sample_rate?: number;
  provider?: string;
  gpu_info?: GpuInfo;
  hwaccel?: boolean;
  encoder_label?: string;
  encoder?: string;
  video_encoder?: string;
}

export interface GpuInfo {
  nvenc?: boolean;
  qsv?: boolean;
  amf?: boolean;
  vaapi?: boolean;
}

export interface NetworkInfo {
  server_ip: string;
  server_port: number;
  srt_port: number;
  latency_ms: number;
  srt_mode: string;
  caller_address: string;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptime_seconds: number;
  memory_mb: number;
  memory_percent: number;
  chunks_processed: number;
  pipeline_state: string;
  modules: Record<string, ModuleHealth>;
  input: {
    receiving: boolean;
    type?: string;
  };
  output: {
    streaming: boolean;
    type?: string;
  };
}

export interface ModuleHealth {
  state: string;
  circuit_state: string;
  enabled: boolean;
  processed_chunks: number;
  last_process_time_ms: number;
  error?: string;
}

// ── Tipos de Configuración ──────────────────────────────────────────────────────

export interface Config {
  server: ServerConfig;
  input: InputConfig;
  output: OutputConfig;
  pipeline: PipelineConfig;
  modules: ModulesConfig;
  output_dir: OutputDirectoryConfig;
}

export interface ServerConfig {
  host: string;
  port: number;
  cors_origins: string[];
  auth_token: string;
  rate_limit_rpm: number;
  max_request_size_mb: number;
}

export interface InputConfig {
  type: InputType;
  srt?: SrtInputConfig;
  rtmp?: RtmpInputConfig;
  file?: FileInputConfig;
}

export type InputType = 'srt' | 'rtmp' | 'file';

export type ConnectionMode = 'local' | 'remote' | 'hybrid';

export interface SrtInputConfig {
  listen_port: number;
  port?: number;
  mode: 'listener' | 'caller';
  latency_ms: number;
  caller_address: string;
  chunk_duration_sec: number;
}

export interface RtmpInputConfig {
  listen_port: number;
  port?: number;
  app: string;
  stream_key: string;
  url: string;
  mode: 'listener' | 'pull';
  chunk_duration_sec: number;
}

export interface FileInputConfig {
  path: string;
  loop: boolean;
  speed: number;
  chunk_duration_sec: number;
}

export interface OutputConfig {
  type: OutputType;
  web?: WebOutputConfig;
  hls?: WebOutputConfig;
  rtmp?: RtmpOutputConfig;
  srt?: SrtOutputConfig;
  file?: FileOutputConfig;
  recording?: RecordingOutputConfig;
  outputs: NamedOutput[];
}

export type OutputType = 'web' | 'hls' | 'srt' | 'rtmp' | 'file' | 'recording';

export interface WebOutputConfig {
  segment_duration: number;
  list_size: number;
  audio_offset_ms: number;
  encoder_mode: EncoderMode;
}

export interface RtmpOutputConfig {
  url: string;
  video_bitrate: string;
  audio_bitrate: string;
  video_codec: VideoCodec;
  preset: string;
  audio_codec: AudioCodec;
  encoder_mode: EncoderMode;
}

export interface SrtOutputConfig {
  url: string;
  mode: 'listener' | 'caller';
  latency_ms: number;
  stream_id: string;
  passphrase: string;
  video_bitrate: string;
  audio_bitrate: string;
  video_codec: VideoCodec;
  preset: string;
  audio_codec: AudioCodec;
}

export interface FileOutputConfig {
  path: string;
  save_video: boolean;
  save_audio: boolean;
  save_subtitles: boolean;
}

export interface RecordingOutputConfig {
  output_path: string;
  format: 'mp4' | 'mkv' | 'webm';
  codec: string;
  video_bitrate: string;
  video_crf: number;
  quality_mode: 'cbr' | 'crf';
  audio_codec: string;
  audio_bitrate: string;
  split_mode: 'none' | 'time' | 'size';
  split_value: number;
  subtitles: 'none' | 'burnt' | 'vtt';
  video_preset: string;
}

export interface NamedOutput {
  name: string;
  type: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

export interface PipelineConfig {
  chunk_duration_sec: number;
  mode: PipelineMode;
  max_concurrent_chunks: number;
  buffer_size: number;
  retry_attempts: number;
  retry_delay: number;
}

export type PipelineMode = 'sequential' | 'thread_parallel' | 'asyncio';

export interface ModulesConfig {
  audio_extractor: ModuleConfig;
  transcriber: TranscriberConfig;
  translator: TranslatorConfig;
  subtitle_generator: SubtitleGeneratorConfig;
  tts_engine: TtsEngineConfig;
  audio_mixer: AudioMixerConfig;
  video_muxer: VideoMuxerConfig;
}

export interface ModuleConfig {
  enabled: boolean;
}

export interface TranscriberConfig extends ModuleConfig {
  model: WhisperModel;
  language: Language;
  device: Device;
  beam_size: number;
}

export interface TranslatorConfig extends ModuleConfig {
  source_lang: Language;
  target_lang: Language;
}

export interface SubtitleGeneratorConfig extends ModuleConfig {
  format: SubtitleFormat;
  use_translated: boolean;
  chunk_duration: number;
}

export interface TtsEngineConfig extends ModuleConfig {
  engine: TtsEngine;
  device: Device;
  voice: string;
  speed: number;
}

export interface AudioMixerConfig extends ModuleConfig {
  original_volume: number;
  tts_volume: number;
  dubbed_volume: number;
}

export interface VideoMuxerConfig extends ModuleConfig {
  engine: 'hls' | 'webrtc';
  hls_segment_duration: number;
  hls_list_size: number;
  audio_offset_ms: number;
  encoder_mode: EncoderMode;
  video_quality: VideoQuality;
  video_crf: number;
  audio_codec: AudioCodec;
  audio_bitrate: string;
  audio_samplerate: string;
  video_codec?: string;
  video_bitrate?: string;
  video_fps?: number;
  video_width?: number;
  video_height?: number;
  webrtc_audio_codec?: AudioCodec;
  webrtc_audio_bitrate?: string;
  audio_sample_rate?: number;
  gpu_preset?: string;
  video_preset?: string;
}

export interface OutputDirectoryConfig {
  directory: string;
}

// ── Tipos de enumeraciones ─────────────────────────────────────────────────────

export type WhisperModel = 'tiny' | 'base' | 'small' | 'medium' | 'large' | 'large-v2' | 'large-v3';
export type Language = 'auto' | 'en' | 'es' | 'fr' | 'de' | 'it' | 'pt' | 'ja' | 'zh' | 'ko' | 'ru';
export type Device = 'auto' | 'cpu' | 'cuda' | 'mps';
export type TtsEngine = 'edge-tts' | 'piper' | 'elevenlabs';
export type SubtitleFormat = 'webvtt' | 'srt' | 'ass';
export type EncoderMode = 'auto' | 'cpu' | 'gpu_nvenc' | 'gpu_vaapi';
export type VideoQuality = 'low' | 'medium' | 'high' | 'ultra';
export type VideoCodec = 'h264' | 'h265' | 'vp8' | 'vp9';
export type AudioCodec = 'aac' | 'mp3' | 'opus';

// ── Tipos de Status ────────────────────────────────────────────────────────────

export interface Status {
  state: PipelineState;
  chunks_processed: number;
  chunks_failed?: number;
  modules: ModuleStatus[];
  metrics?: MetricsData;
  input_receiving?: boolean;
  input_info?: InputInfo;
  network?: NetworkInfo;
}

export type PipelineState = 'stopped' | 'running' | 'starting' | 'stopping' | 'error';

export interface MetricsData {
  cpu_percent: number;
  memory_mb: number;
  memory_percent: number;
  gpu_usage?: number;
  gpu_memory?: number;
  gpu_util?: number;
  gpu_memory_mb?: number;
  gpu_memory_percent?: number;
  chunks_per_second?: number;
}

export interface InputInfo {
  type: InputType;
  mode?: string;
  port?: number;
  latency_ms?: number;
  url?: string;
  obs_url?: string;
  duration?: number;
  position?: number;
  is_playing?: boolean;
}

// ── Tipos de WebSocket ────────────────────────────────────────────────────────

export interface WebSocketMessage {
  type: 'log' | 'status';
  level?: 'INFO' | 'WARNING' | 'ERROR';
  message?: string;
  status?: Status;
  timestamp?: number;
}

// ── Tipos de Outputs ───────────────────────────────────────────────────────────

export interface AddOutputRequest {
  type: string;
  name?: string;
  config?: Record<string, unknown>;
  enabled?: boolean;
}

export interface OutputStatus {
  name: string;
  type: string;
  state: 'running' | 'stopped' | 'starting' | 'stopping';
  enabled: boolean;
  processed_chunks: number;
  last_process_time_ms: number;
  extra?: ModuleExtra;
  stream_info?: Record<string, unknown>;
  error?: string;
}