import { SERVER_PORT, STORAGE_KEYS } from './constants';

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

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getAuthToken();
  const headers = new Headers(options.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...options, headers });
}

export async function apiCall<T = any>(method: string, path: string, body?: any): Promise<T> {
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
    throw new Error(`${res.status} ${res.statusText}: ${errorText}`);
  }
  return res.json();
}

export async function getConfig(): Promise<any> {
  return apiCall('GET', '/api/config');
}

export async function updateConfig(config: any): Promise<any> {
  return apiCall('PUT', '/api/config', { config });
}

export async function startPipeline(): Promise<any> {
  return apiCall('POST', '/api/start');
}

export async function stopPipeline(): Promise<any> {
  return apiCall('POST', '/api/stop');
}

export async function getStatus(): Promise<any> {
  return apiCall('GET', '/api/status');
}

export class WSClient {
  private ws: WebSocket | null = null;
  private url: string;
  private onmessage?: (data: any) => void;
  private onerror?: (error: any) => void;
  private onclose?: () => void;

  constructor(url: string) {
    this.url = url;
  }

  connect(): void {
    this.ws = new WebSocket(this.url);
    this.ws.onmessage = (e) => this.onmessage?.(JSON.parse(e.data));
    this.ws.onerror = (e) => this.onerror?.(e);
    this.ws.onclose = () => this.onclose?.();
  }

  onMessage(fn: (data: any) => void): this {
    this.onmessage = fn;
    return this;
  }

  onError(fn: (error: any) => void): this {
    this.onerror = fn;
    return this;
  }

  onClose(fn: () => void): this {
    this.onclose = fn;
    return this;
  }

  send(data: any): void {
    this.ws?.send(JSON.stringify(data));
  }

  close(): void {
    this.ws?.close();
    this.ws = null;
  }
}