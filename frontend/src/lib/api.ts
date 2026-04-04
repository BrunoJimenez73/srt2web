/**
 * API utilities for communicating with the SRT2Web backend
 */

// Auth token storage key
const AUTH_TOKEN_KEY = 'srt2web_auth_token';

/**
 * Get stored authentication token
 */
export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

/**
 * Set authentication token
 */
export function setAuthToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  } catch {
    // Storage not available
  }
}

/**
 * Clear authentication token
 */
export function clearAuthToken(): void {
  setAuthToken(null);
}

/**
 * Get the API base URL
 */
export function getApiBaseUrl(): string {
  const protocol = window.location.protocol;
  const host = window.location.host;
  return `${protocol}//${host}`;
}

/**
 * Get WebSocket URL
 */
export function getWebSocketUrl(path: string = '/ws/logs'): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const token = getAuthToken();
  
  let url = `${protocol}//${host}${path}`;
  if (token) {
    url += `?token=${encodeURIComponent(token)}`;
  }
  return url;
}

/**
 * Get headers with authentication
 */
export function getAuthHeaders(): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  const token = getAuthToken();
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
}

/**
 * Make an authenticated fetch request
 */
export async function fetchWithAuth(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };
  
  return fetch(url, {
    ...options,
    headers,
  });
}

/**
 * Make an API call
 */
export async function apiCall<T>(
  method: string,
  path: string,
  body?: any
): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`;
  const options: RequestInit = {
    method,
    headers: getAuthHeaders(),
  };
  
  if (body && method !== 'GET') {
    options.body = JSON.stringify(body);
  }
  
  const response = await fetch(url, options);
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error ${response.status}: ${errorText}`);
  }
  
  return response.json();
}

/**
 * Get current configuration
 */
export async function getConfig(): Promise<any> {
  return apiCall('GET', '/api/config');
}

/**
 * Update configuration
 */
export async function updateConfig(config: any): Promise<any> {
  return apiCall('PUT', '/api/config', { config });
}

/**
 * Start the pipeline
 */
export async function startPipeline(): Promise<any> {
  return apiCall('POST', '/api/start');
}

/**
 * Stop the pipeline
 */
export async function stopPipeline(): Promise<any> {
  return apiCall('POST', '/api/stop');
}

/**
 * Get pipeline status
 */
export async function getStatus(): Promise<any> {
  return apiCall('GET', '/api/status');
}

/**
 * Toggle a module
 */
export async function toggleModule(moduleName: string, enabled: boolean): Promise<any> {
  return apiCall('PUT', `/api/modules/${moduleName}/toggle`, { enabled });
}

/**
 * Get network information
 */
export async function getNetworkInfo(): Promise<any> {
  return apiCall('GET', '/api/network/info');
}

/**
 * Health check
 */
export async function healthCheck(): Promise<any> {
  return apiCall('GET', '/health');
}