/**
 * API Client - Llamadas HTTP y WebSocket al backend SRT2Web.
 *
 * Proporciona funciones tipadas para interactuar con el servidor.
 * Los tipos se definen en `types/api.ts`.
 */

import { SERVER_PORT, STORAGE_KEYS } from './constants';

// Import all types from the types module
export type {
  ApiResponse,
  ConfigUpdateResponse,
  PipelineStartResponse,
  PipelineStopResponse,
  ModuleToggleResponse,
  ModuleStatus,
  ModuleName,
  LogLevel,
  LogMessage,
  ModuleState,
  ModuleExtra,
  GpuInfo,
  NetworkInfo,
  HealthStatus,
  ModuleHealth,
  Config,
  ServerConfig,
  InputConfig,
  InputType,
  ConnectionMode,
  SrtInputConfig,
  RtmpInputConfig,
  FileInputConfig,
  OutputConfig,
  OutputType,
  WebOutputConfig,
  RtmpOutputConfig,
  SrtOutputConfig,
  FileOutputConfig,
  RecordingOutputConfig,
  NamedOutput,
  PipelineConfig,
  PipelineMode,
  ModulesConfig,
  ModuleConfig,
  TranscriberConfig,
  TranslatorConfig,
  SubtitleGeneratorConfig,
  TtsEngineConfig,
  AudioMixerConfig,
  VideoMuxerConfig,
  OutputDirectoryConfig,
  WhisperModel,
  Language,
  Device,
  TtsEngine,
  SubtitleFormat,
  EncoderMode,
  VideoQuality,
  VideoCodec,
  AudioCodec,
  Status,
  PipelineState,
  MetricsData,
  InputInfo,
  WebSocketMessage,
  AddOutputRequest,
  OutputStatus,
} from './types/api';

// Re-import for internal use
import type { Config, ConfigUpdateResponse, PipelineStartResponse, PipelineStopResponse, ModuleToggleResponse, ModuleStatus, Status, HealthStatus, NetworkInfo, InputInfo, AddOutputRequest, OutputStatus, WebSocketMessage } from './types/api';

// ── Funciones de autenticación ─────────────────────────────────────────────────

const AUTH_TOKEN_KEY = STORAGE_KEYS.AUTH_TOKEN;

export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAuthToken(token: string | null): void {
  if (typeof window === 'undefined') return;
  if (token) localStorage.setItem(AUTH_TOKEN_KEY, token);
  else localStorage.removeItem(AUTH_TOKEN_KEY);
}

export function clearAuthToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

// ── URLs ───────────────────────────────────────────────────────────────────────

export function getApiBase(): string {
  if (typeof window === 'undefined') return `http://localhost:${SERVER_PORT}`;
  return `${window.location.protocol}//${window.location.host}`;
}

export function getWebSocketUrl(path: string = '/ws/logs'): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const token = getAuthToken();
  const base = `${protocol}//${window.location.host}${path}`;
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
}

// ── Cliente HTTP ───────────────────────────────────────────────────────────────

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getAuthToken();
  const headers = new Headers(options.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...options, headers });
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public statusText: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiCall<T>(method: string, path: string, body?: unknown): Promise<T> {
  const base = getApiBase();
  const cleanPath = path.replace(/^\/+/, '');
  const url = cleanPath ? `${base}/${cleanPath}` : base;
  const options: RequestInit = { method };

  if (body) {
    options.body = JSON.stringify(body);
    options.headers = { 'Content-Type': 'application/json' };
  }

  const res = await fetchWithAuth(url, options);
  if (!res.ok) {
    const errorText = await res.text().catch(() => res.statusText);
    throw new ApiError(`${res.status} ${res.statusText}: ${errorText}`, res.status, res.statusText);
  }
  return res.json();
}

// ── API Calls ──────────────────────────────────────────────────────────────────

export async function getConfig(): Promise<Config> {
  return apiCall<Config>('GET', '/api/config');
}

export async function updateConfig(config: Partial<Config>): Promise<ConfigUpdateResponse> {
  return apiCall<ConfigUpdateResponse>('PUT', '/api/config', { config });
}

export async function updateChunkDuration(chunkDurationSec: number): Promise<{
  status: string;
  chunk_duration_sec: number;
  synced_to: string[];
}> {
  return apiCall<{ status: string; chunk_duration_sec: number; synced_to: string[] }>(
    'POST',
    '/api/config/chunk',
    { chunk_duration_sec: chunkDurationSec }
  );
}

export async function startPipeline(): Promise<PipelineStartResponse> {
  return apiCall<PipelineStartResponse>('POST', '/api/start');
}

export async function stopPipeline(): Promise<PipelineStopResponse> {
  return apiCall<PipelineStopResponse>('POST', '/api/stop');
}

export async function getStatus(): Promise<Status> {
  return apiCall<Status>('GET', '/api/status');
}

export async function getHealth(): Promise<HealthStatus> {
  return apiCall<HealthStatus>('GET', '/api/health');
}

export async function getNetworkInfo(): Promise<NetworkInfo> {
  return apiCall<NetworkInfo>('GET', '/api/network/info');
}

export async function getInputInfo(): Promise<InputInfo> {
  return apiCall<InputInfo>('GET', '/api/input-info');
}

export async function toggleModule(moduleName: string, enabled: boolean): Promise<ModuleToggleResponse> {
  return apiCall<ModuleToggleResponse>('PUT', `modules/${moduleName}/toggle`, { enabled });
}

export async function getModules(): Promise<{ modules: ModuleStatus[] }> {
  return apiCall<{ modules: ModuleStatus[] }>('GET', '/modules');
}

export async function getAvailableOutputs(): Promise<{ available_types: string[] }> {
  return apiCall<{ available_types: string[] }>('GET', '/api/outputs/available');
}

export async function getOutputs(): Promise<{ outputs: OutputStatus[] }> {
  return apiCall<{ outputs: OutputStatus[] }>('GET', '/api/outputs');
}

export async function addOutput(output: AddOutputRequest): Promise<{ status: string; name: string; type: string }> {
  return apiCall<{ status: string; name: string; type: string }>('POST', '/api/outputs', output);
}

export async function removeOutput(outputName: string): Promise<{ status: string; name: string }> {
  return apiCall<{ status: string; name: string }>('DELETE', `/api/outputs/${encodeURIComponent(outputName)}`);
}

export async function toggleOutput(outputName: string, enabled: boolean): Promise<{ status: string; name: string; enabled: boolean }> {
  return apiCall<{ status: string; name: string; enabled: boolean }>('POST', `/api/outputs/${encodeURIComponent(outputName)}/toggle`, { enabled });
}

// ── Control de reproducción de archivo ─────────────────────────────────────────

export async function inputPlay(): Promise<{ status: string; message: string }> {
  return apiCall<{ status: string; message: string }>('POST', 'input/control/play');
}

export async function inputPause(): Promise<{ status: string; message: string }> {
  return apiCall<{ status: string; message: string }>('POST', 'input/control/pause');
}

export async function inputSeek(position: number): Promise<{ status: string; position: number; message: string }> {
  return apiCall<{ status: string; position: number; message: string }>('POST', 'input/control/seek', { position });
}

// ── WebSocket Client ───────────────────────────────────────────────────────────

export class WSClient {
  private ws: WebSocket | null = null;
  private url: string;
  private onMessageHandler?: (data: WebSocketMessage) => void;
  private onErrorHandler?: (error: Event) => void;
  private onCloseHandler?: () => void;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(url: string) {
    this.url = url;
  }

  connect(): void {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (e: MessageEvent) => {
      console.log('[WS] Received:', e.data);
      try {
        const data = JSON.parse(e.data) as WebSocketMessage;
        console.log('[WS] Parsed:', data);
        this.onMessageHandler?.(data);
      } catch {
        console.error('Failed to parse WebSocket message:', e.data);
      }
    };

    this.ws.onerror = (e: Event) => {
      console.error('[WS] Error:', e);
      this.onErrorHandler?.(e);
    };

    this.ws.onclose = () => {
      console.log('[WS] Connection closed, reconnecting...');
      this.onCloseHandler?.();
      this.attemptReconnect();
    };
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  onMessage(fn: (data: WebSocketMessage) => void): this {
    this.onMessageHandler = fn;
    return this;
  }

  onError(fn: (error: Event) => void): this {
    this.onErrorHandler = fn;
    return this;
  }

  onClose(fn: () => void): this {
    this.onCloseHandler = fn;
    return this;
  }

  send(data: unknown): void {
    this.ws?.send(JSON.stringify(data));
  }

  close(): void {
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent auto-reconnect
    this.ws?.close();
    this.ws = null;
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
