import type { Config, Status, LogMessage } from './types';

const AUTH_TOKEN_KEY = 'srt2web_auth_token';

export function getAuthToken(): string {
  return localStorage.getItem(AUTH_TOKEN_KEY) || '';
}

export function setAuthToken(token: string): void {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

export function clearAuthToken(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

export async function apiCall<T>(method: string, path: string, body?: unknown): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const opts: RequestInit = {
    method,
    headers,
  };
  if (body) opts.body = JSON.stringify(body);

  const resp = await fetch(`/api${path}`, opts);
  if (!resp.ok) {
    let errorMessage = resp.statusText;
    try {
      const err = await resp.json();
      if (err && typeof err === 'object') {
        errorMessage = (err as Record<string, unknown>).detail as string || errorMessage;
      }
    } catch {
      // ignore parse errors
    }
    throw new Error(errorMessage);
  }
  return resp.json();
}

export async function getConfig(): Promise<Config> {
  return apiCall<Config>('GET', '/config');
}

export async function updateConfig(config: Partial<Config>): Promise<Config> {
  return apiCall<Config>('PUT', '/config', { config });
}

export async function getStatus(): Promise<Status> {
  return apiCall<Status>('GET', '/status');
}

export async function startPipeline(): Promise<Status> {
  return apiCall<Status>('POST', '/start');
}

export async function stopPipeline(): Promise<Status> {
  return apiCall<Status>('POST', '/stop');
}

export async function restartPipeline(): Promise<Status> {
  return apiCall<Status>('POST', '/restart');
}

export async function toggleModule(moduleName: string, enabled: boolean): Promise<void> {
  await apiCall('POST', `/modules/${moduleName}/toggle?enabled=${enabled}`);
}

export type WSConnectionState = 'disconnected' | 'connecting' | 'connected';

export interface WSClientOptions {
  onLog?: (data: LogMessage) => void;
  onStatus?: (data: Status) => void;
  onConnectionChange?: (connected: boolean) => void;
  onStateChange?: (state: WSConnectionState) => void;
}

export class WSClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 50;
  private baseReconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private reconnectDelay = this.baseReconnectDelay;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private lastPingTime = 0;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  
  public state: WSConnectionState = 'disconnected';
  public onLog?: (data: LogMessage) => void;
  public onStatus?: (data: Status) => void;
  public onConnectionChange?: (connected: boolean) => void;
  public onStateChange?: (state: WSConnectionState) => void;

  constructor(options: WSClientOptions = {}) {
    this.onLog = options.onLog;
    this.onStatus = options.onStatus;
    this.onConnectionChange = options.onConnectionChange;
    this.onStateChange = options.onStateChange;
  }

  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    this.setState('connecting');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const token = getAuthToken();
    const url = token
      ? `${protocol}//${window.location.host}/ws/logs?token=${encodeURIComponent(token)}`
      : `${protocol}//${window.location.host}/ws/logs`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.reconnectDelay = this.baseReconnectDelay;
        this.setState('connected');
        this._startHeartbeat();
        this.onConnectionChange?.(true);
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'log' && this.onLog) {
            this.onLog(data);
          } else if (data.type === 'status' && this.onStatus) {
            this.onStatus(data);
          } else if (data.type === 'pong') {
            this.lastPingTime = Date.now();
          }
        } catch {
          this.onLog?.({ level: 'info', message: event.data });
        }
      };

      this.ws.onclose = () => {
        this.setState('disconnected');
        this._stopHeartbeat();
        this.onConnectionChange?.(false);
        this._scheduleReconnect();
      };

      this.ws.onerror = () => {
        // onerror is usually followed by onclose
      };

    } catch {
      this.setState('disconnected');
      this._scheduleReconnect();
    }
  }

  private _scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WS] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const jitter = Math.random() * 0.3 * this.reconnectDelay;
    const delay = Math.min(this.reconnectDelay + jitter, this.maxReconnectDelay);
    
    console.log(`[WS] Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts})`);
    
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
    
    this.reconnectTimeout = setTimeout(() => this.connect(), delay);
  }

  private _startHeartbeat(): void {
    this._stopHeartbeat();
    this.lastPingTime = Date.now();
    
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
        
        if (Date.now() - this.lastPingTime > 10000) {
          console.warn('[WS] Heartbeat timeout, reconnecting...');
          this.ws.close();
        }
      }
    }, 30000);
  }

  private _stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private setState(state: WSConnectionState): void {
    this.state = state;
    this.onStateChange?.(state);
    
    const indicator = document.getElementById('ws-status');
    if (indicator) {
      indicator.className = `ws-status ${state}`;
      const dot = indicator.querySelector('.ws-status-dot');
      const label = indicator.querySelector('.ws-status-label');
      if (label) {
        label.textContent = state === 'connected' ? 'WS' : 
                           state === 'connecting' ? 'WS...' : 'WS OFF';
      }
    }
  }

  disconnect(): void {
    this._stopHeartbeat();
    this.maxReconnectAttempts = 0;
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setState('disconnected');
  }

  requestStatus(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'get_status' }));
    }
  }
}

export function connectWebSocket(
  onMessage: (data: LogMessage) => void,
  onError?: (error: Event) => void
): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const token = getAuthToken();
  const url = token
    ? `${protocol}//${window.location.host}/ws/logs?token=${encodeURIComponent(token)}`
    : `${protocol}//${window.location.host}/ws/logs`;
  const ws = new WebSocket(url);
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as LogMessage;
      onMessage(data);
    } catch {
      onMessage({ level: 'info', message: event.data });
    }
  };
  
  ws.onerror = (error) => {
    if (onError) onError(error);
  };
  
  return ws;
}
