/**
 * Vitest tests for api.ts
 *
 * Tests cover: auth token management, URL generation, API client, WebSocket client
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  getAuthToken,
  setAuthToken,
  clearAuthToken,
  getApiBase,
  getWebSocketUrl,
  fetchWithAuth,
  apiCall,
  ApiError,
  WSClient,
} from './api';

describe('Auth Token Management', () => {
  let store: Record<string, string> = {};

  beforeEach(() => {
    store = {};
    const mockLocalStorage = {
      getItem: vi.fn((key: string) => store[key] || null),
      setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
      removeItem: vi.fn((key: string) => { delete store[key]; }),
    };
    vi.stubGlobal('localStorage', mockLocalStorage);
    vi.stubGlobal('window', { location: { protocol: 'http:', host: 'localhost:9999' } });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('getAuthToken returns null when no token stored', () => {
    expect(getAuthToken()).toBeNull();
  });

  it('setAuthToken stores token in localStorage', () => {
    setAuthToken('test-token-123');
    expect(localStorage.setItem).toHaveBeenCalledWith('srt2web_auth_token', 'test-token-123');
    expect(getAuthToken()).toBe('test-token-123');
  });

  it('setAuthToken with null removes token', () => {
    setAuthToken('test-token');
    setAuthToken(null);
    expect(localStorage.removeItem).toHaveBeenCalledWith('srt2web_auth_token');
    expect(getAuthToken()).toBeNull();
  });

  it('clearAuthToken removes token', () => {
    setAuthToken('test-token');
    clearAuthToken();
    expect(localStorage.removeItem).toHaveBeenCalledWith('srt2web_auth_token');
    expect(getAuthToken()).toBeNull();
  });

  it('returns null when window is undefined (SSR)', () => {
    vi.stubGlobal('window', undefined);
    expect(getAuthToken()).toBeNull();
    expect(setAuthToken('test')).toBeUndefined();
    expect(clearAuthToken()).toBeUndefined();
  });
});

describe('URL Generation', () => {
  beforeEach(() => {
    vi.stubGlobal('window', { location: { protocol: 'http:', host: 'localhost:9999' } });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('getApiBase returns correct URL with window', () => {
    expect(getApiBase()).toBe('http://localhost:9999');
  });

  it('getApiBase returns localhost with SERVER_PORT when window undefined', () => {
    vi.stubGlobal('window', undefined);
    expect(getApiBase()).toBe('http://localhost:9999');
  });

  it('getWebSocketUrl returns ws:// URL without token', () => {
    const url = getWebSocketUrl('/ws/logs');
    expect(url).toBe('ws://localhost:9999/ws/logs');
  });

  it('getWebSocketUrl includes token when set', () => {
    setAuthToken('my-token');
    const url = getWebSocketUrl('/ws/logs');
    expect(url).toBe('ws://localhost:9999/ws/logs?token=my-token');
  });

  it('getWebSocketUrl uses wss:// for https', () => {
    vi.stubGlobal('window', { location: { protocol: 'https:', host: 'example.com' } });
    setAuthToken(null);
    const url = getWebSocketUrl('/ws/status');
    expect(url).toBe('wss://example.com/ws/status');
  });

  it('getWebSocketUrl defaults to /ws/logs', () => {
    const url = getWebSocketUrl();
    expect(url).toBe('ws://localhost:9999/ws/logs');
  });
});

describe('API Client', () => {
  let fetchMock: any;

  beforeEach(() => {
    vi.stubGlobal('window', { location: { protocol: 'http:', host: 'localhost:9999' } });
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    clearAuthToken();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetchWithAuth adds Authorization header when token set', async () => {
    setAuthToken('secret-token');
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 200 }));

    await fetchWithAuth('http://localhost:9999/api/test', { method: 'GET' });

    const callArgs = fetchMock.mock.calls[0];
    const headers = new Headers(callArgs[1]?.headers);
    expect(headers.get('Authorization')).toBe('Bearer secret-token');
  });

  it('fetchWithAuth does not add Authorization when no token', async () => {
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 200 }));

    await fetchWithAuth('http://localhost:9999/api/test');

    const callArgs = fetchMock.mock.calls[0];
    if (callArgs[1]?.headers) {
      const headers = new Headers(callArgs[1].headers);
      expect(headers.get('Authorization')).toBeNull();
    }
  });
});

describe('apiCall', () => {
  let fetchMock: any;

  beforeEach(() => {
    vi.stubGlobal('window', { location: { protocol: 'http:', host: 'localhost:9999' } });
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('makes GET request without body', async () => {
    const mockData = { key: 'value' };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(mockData), { status: 200 })
    );

    const result = await apiCall<typeof mockData>('GET', '/api/config');
    expect(result).toEqual(mockData);
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:9999/api/config',
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('makes POST request with body', async () => {
    const mockData = { status: 'started' };
    const body = { action: 'start' };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(mockData), { status: 200 })
    );

    const result = await apiCall<typeof mockData>('POST', '/api/start', body);
    expect(result).toEqual(mockData);

    const callArgs = fetchMock.mock.calls[0];
    expect(callArgs[1]?.method).toBe('POST');
    expect(callArgs[1]?.body).toBe(JSON.stringify(body));
    const headers = new Headers(callArgs[1]?.headers);
    expect(headers.get('Content-Type')).toBe('application/json');
  });

  it('strips leading slashes from path', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({}), { status: 200 })
    );

    await apiCall('GET', '///api/test');
    const callArgs = fetchMock.mock.calls[0];
    expect(callArgs[0]).toBe('http://localhost:9999/api/test');
  });

  it('throws ApiError on non-ok response', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response('Not Found', { status: 404, statusText: 'Not Found' })
    );

    await expect(apiCall('GET', '/api/nonexistent')).rejects.toThrow(ApiError);

    try {
      await apiCall('GET', '/api/nonexistent');
    } catch (e) {
      const err = e as ApiError;
      expect(err.status).toBe(404);
      expect(err.statusText).toBe('Not Found');
      expect(err.message).toContain('404');
    }
  });

  it('ApiError captures response text on error', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response('{"error": "invalid"}', { status: 400, statusText: 'Bad Request' })
    );

    try {
      await apiCall('POST', '/api/config', {});
    } catch (e) {
      const err = e as ApiError;
      expect(err.message).toContain('invalid');
    }
  });
});

describe('WSClient - Basic Tests', () => {
  it('WSClient constructor sets URL', () => {
    const client = new WSClient('ws://localhost:9999/ws/logs');
    expect(client).toBeDefined();
  });

  it('WSClient methods are chainable', () => {
    const client = new WSClient('ws://localhost:9999/ws/logs');
    expect(client.onMessage(() => {})).toBe(client);
    expect(client.onError(() => {})).toBe(client);
    expect(client.onClose(() => {})).toBe(client);
  });

  it('WSClient close prevents reconnect', () => {
    const client = new WSClient('ws://localhost:9999/ws/logs');
    client.close();
    expect(client['reconnectAttempts']).toBe(5); // Max attempts
  });

  it('WSClient isConnected returns false when not connected', () => {
    const client = new WSClient('ws://localhost:9999/ws/logs');
    expect(client.isConnected()).toBe(false);
  });

  it('WSClient send does not throw when not connected', () => {
    const client = new WSClient('ws://localhost:9999/ws/logs');
    expect(() => client.send({ test: 'data' })).not.toThrow();
  });
});
