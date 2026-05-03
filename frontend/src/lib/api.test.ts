import { describe, test, expect, vi, beforeEach } from 'vitest';
import { getAuthToken, setAuthToken, clearAuthToken, getApiBase, getWebSocketUrl, fetchWithAuth } from './api';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

Object.defineProperty(window, 'location', {
  value: {
    protocol: 'http:',
    host: 'localhost:9999',
  },
});

describe('api.ts', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('Auth token management', () => {
    test('getAuthToken returns null when no token stored', () => {
      expect(getAuthToken()).toBeNull();
    });

    test('getAuthToken returns stored token', () => {
      localStorageMock.setItem('srt2web_auth_token', 'test-token-123');
      expect(getAuthToken()).toBe('test-token-123');
    });

    test('setAuthToken stores token', () => {
      setAuthToken('new-token');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('srt2web_auth_token', 'new-token');
    });

    test('setAuthToken with null removes token', () => {
      localStorageMock.setItem('srt2web_auth_token', 'old-token');
      setAuthToken(null);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('srt2web_auth_token');
    });

    test('clearAuthToken removes token', () => {
      localStorageMock.setItem('srt2web_auth_token', 'token-to-clear');
      clearAuthToken();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('srt2web_auth_token');
    });
  });

  describe('URL helpers', () => {
    test('getApiBase returns correct URL', () => {
      expect(getApiBase()).toBe('http://localhost:9999');
    });

    test('getWebSocketUrl returns correct URL without token', () => {
      const url = getWebSocketUrl();
      expect(url).toBe('ws://localhost:9999/ws/logs');
    });

    test('getWebSocketUrl includes token when available', () => {
      setAuthToken('test-token');
      const url = getWebSocketUrl();
      expect(url).toContain('token=test-token');
    });

    test('getWebSocketUrl with custom path', () => {
      const url = getWebSocketUrl('/ws/pipeline');
      expect(url).toBe('ws://localhost:9999/ws/pipeline');
    });
  });

  describe('fetchWithAuth', () => {
    beforeEach(() => {
      global.fetch = vi.fn();
    });

    test('adds Authorization header when token exists', async () => {
      setAuthToken('my-token');
      const mockResponse = new Response(JSON.stringify({ success: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
      vi.mocked(fetch).mockResolvedValueOnce(mockResponse);

      await fetchWithAuth('/api/config');

      // Get the first call arguments
      const callArgs = vi.mocked(fetch).mock.calls[0];
      const url = callArgs[0];
      const options = callArgs[1] || {};
      
      expect(url).toBe('/api/config');
      expect(options.headers).toBeDefined();
      expect((options.headers as Record<string, string>)['Authorization'] || (options.headers as Headers).get('Authorization')).toContain('Bearer my-token');
    });

    test('does not add Authorization header when no token', async () => {
      const mockResponse = new Response(JSON.stringify({ success: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
      vi.mocked(fetch).mockResolvedValueOnce(mockResponse);

      await fetchWithAuth('/api/config');

      const callArgs = vi.mocked(fetch).mock.calls[0];
      const headers = callArgs[1]?.headers || {};
      expect(headers).not.toHaveProperty('Authorization');
    });
  });
});
