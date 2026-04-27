/**
 * Tipos de datos para gestión de salidas múltiples.
 */

// Re-export shared types via barrel
export type { Config, Status, PipelineState, ModuleStatus, ModuleState, MetricsData, InputConfig, WebSocketMessage, HealthStatus, LogMessage } from './shared-types';

// Configuración base para todas las salidas
export interface BaseOutputConfig {
  type: string;
  name?: string;
  enabled?: boolean;
}

// Configuración específica para Recording (grabación continua)
export interface RecordingOutputConfig extends BaseOutputConfig {
  type: 'recording';
  output_path: string;
  format: 'mp4' | 'mkv' | 'webm';
  codec: 'copy' | 'h264_nvenc' | 'h265_nvenc' | 'libx264' | 'libx265';
  video_bitrate?: string;
  video_crf?: number;
  quality_mode: 'cbr' | 'crf';
  audio_codec: 'copy' | 'aac' | 'opus';
  audio_bitrate?: string;
  split_mode: 'none' | 'time' | 'size';
  split_value?: number;
  subtitles: 'none' | 'burnt' | 'vtt';
  video_preset?: string;
}

// Configuración específica para SRT
export interface SrtOutputConfig extends BaseOutputConfig {
  type: 'srt';
  url: string;
  mode: 'caller' | 'listener' | 'rendezvous';
  latency_ms: number;
  stream_id?: string;
  passphrase?: string;
  video_bitrate: string;
  audio_bitrate: string;
  video_codec: string;
  preset: string;
  audio_codec: string;
}

// Configuración específica para Archivo
export interface FileOutputConfig extends BaseOutputConfig {
  type: 'file';
  save_video: boolean;
  save_audio: boolean;
  save_subtitles: boolean;
  path: string;
}

// Configuración específica para RTMP
export interface RtmpOutputConfig extends BaseOutputConfig {
  type: 'rtmp';
  url: string;
  video_bitrate: string;
  audio_bitrate: string;
  video_codec: string;
  preset: string;
  audio_codec: string;
  encoder_mode: 'auto' | 'cpu' | 'gpu_nvenc' | 'gpu_vaapi';
}

// Configuración específica para Web/HLS
export interface WebOutputConfig extends BaseOutputConfig {
  type: 'web';
  segment_duration: number;
  list_size: number;
  audio_offset_ms: number;
  encoder_mode: 'auto' | 'cpu' | 'gpu_nvenc' | 'gpu_vaapi';
}

// Tipo unión para todas las configuraciones de salida
export type OutputConfig = RecordingOutputConfig | SrtOutputConfig | FileOutputConfig | RtmpOutputConfig | WebOutputConfig;

// Estado de una salida
export interface OutputStatus {
  name: string;
  type: string;
  state: 'running' | 'stopped' | 'starting' | 'stopping';
  enabled: boolean;
  processed_chunks: number;
  last_process_time_ms: number;
  extra?: Record<string, any>;
}

// Respuesta de múltiples salidas
export interface OutputsResponse {
  statuses: OutputStatus[];
  errors: Record<string, string>;
}

// Estado de la aplicación para gestión de salidas
export interface OutputManagerState {
  outputs: OutputStatus[];
  errors: Record<string, string>;
}

// Tipos para el formulario de configuración
export interface OutputFormState {
  outputType: string;
  outputName: string;
  url: string;
  mode: string;
  latency: string;
  streamId: string;
  passphrase: string;
  videoBitrate: string;
  audioBitrate: string;
  videoCodec: string;
  preset: string;
  audioCodec: string;
  saveVideo: boolean;
  saveAudio: boolean;
  saveSubtitles: boolean;
  path: string;
  segmentDuration: string;
  listSize: string;
  audioOffset: string;
  encoderMode: string;
}

// Tipos para los manejadores de eventos
export interface OutputHandlers {
  onAddOutput: (config: any) => void;
  onRemoveOutput: (name: string) => void;
  onReconnectOutput: (name: string) => void;
  onEnableOutput: (name: string, enable: boolean) => void;
}

// Tipos para los componentes
export interface OutputStatusCardProps {
  output: OutputStatus;
  error: string | null;
  onRemove: () => void;
  onReconnect: () => void;
  onEnable: (enable: boolean) => void;
}

export interface OutputConfigFormProps {
  onAddOutput: (config: any) => void;
}

export interface OutputManagerCardProps extends OutputHandlers {
  outputs: OutputStatus[];
  errors: Record<string, string>;
}

export interface ModuleExtra {
  using_gpu?: boolean;
  device?: string;
  encoder_mode?: string;
  compute_type?: string;
  sample_rate?: number;
  provider?: string;
}

declare global {
  interface Window {
    showToast?: (message: string, type?: 'info' | 'success' | 'error') => void;
    updateStats?: (stats: any) => void;
    dashboardStore?: any;
  }
}

export interface ConfigUpdateTimeouts {
  input?: ReturnType<typeof setTimeout>;
  pipeline?: ReturnType<typeof setTimeout>;
  output?: ReturnType<typeof setTimeout>;
}