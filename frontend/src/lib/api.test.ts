/**
 * Vitest tests for api.ts
 *
 * Tests cover: auth token management, URL generation, API client, WebSocket client
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
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
  __testing_setCsrfToken,
  toggleModule,
  getModules,
  inputPlay,
  inputPause,
  inputSeek,
} from "./api";

describe("Auth Token Management", () => {
  let store: Record<string, string> = {};

  beforeEach(() => {
    store = {};
    const mockLocalStorage = {
      getItem: vi.fn((key: string) => store[key] || null),
      setItem: vi.fn((key: string, value: string) => {
        store[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete store[key];
      }),
    };
    vi.stubGlobal("localStorage", mockLocalStorage);
    vi.stubGlobal("window", {
      location: { protocol: "http:", host: "localhost:9999" },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("getAuthToken returns null when no token stored", () => {
    expect(getAuthToken()).toBeNull();
  });

  it("setAuthToken stores token in localStorage", () => {
    setAuthToken("test-token-123");
    expect(localStorage.setItem).toHaveBeenCalledWith(
      "srt2web_auth_token",
      "test-token-123",
    );
    expect(getAuthToken()).toBe("test-token-123");
  });

  it("setAuthToken with null removes token", () => {
    setAuthToken("test-token");
    setAuthToken(null);
    expect(localStorage.removeItem).toHaveBeenCalledWith("srt2web_auth_token");
    expect(getAuthToken()).toBeNull();
  });

  it("clearAuthToken removes token", () => {
    setAuthToken("test-token");
    clearAuthToken();
    expect(localStorage.removeItem).toHaveBeenCalledWith("srt2web_auth_token");
    expect(getAuthToken()).toBeNull();
  });

  it("returns null when window is undefined (SSR)", () => {
    vi.stubGlobal("window", undefined);
    expect(getAuthToken()).toBeNull();
    expect(setAuthToken("test")).toBeUndefined();
    expect(clearAuthToken()).toBeUndefined();
  });
});

describe("URL Generation", () => {
  beforeEach(() => {
    vi.stubGlobal("window", {
      location: { protocol: "http:", host: "localhost:9999" },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("getApiBase returns correct URL with window", () => {
    expect(getApiBase()).toBe("http://localhost:9999");
  });

  it("getApiBase returns localhost with SERVER_PORT when window undefined", () => {
    vi.stubGlobal("window", undefined);
    expect(getApiBase()).toBe("http://localhost:9999");
  });

  it("getWebSocketUrl returns ws:// URL without token", () => {
    const url = getWebSocketUrl("/ws/logs");
    expect(url).toBe("ws://localhost:9999/ws/logs");
  });

  it("getWebSocketUrl remains a base URL; WSClient adds auth before connect", () => {
    setAuthToken("my-token");
    const url = getWebSocketUrl("/ws/logs");
    expect(url).toBe("ws://localhost:9999/ws/logs");
    expect(url).not.toContain("token=");
  });

  it("getWebSocketUrl uses wss:// for https", () => {
    vi.stubGlobal("window", {
      location: { protocol: "https:", host: "example.com" },
    });
    setAuthToken(null);
    const url = getWebSocketUrl("/ws/status");
    expect(url).toBe("wss://example.com/ws/status");
  });

  it("getWebSocketUrl defaults to /ws/logs", () => {
    const url = getWebSocketUrl();
    expect(url).toBe("ws://localhost:9999/ws/logs");
  });
});

describe("API Client", () => {
  let fetchMock: any;

  beforeEach(() => {
    vi.stubGlobal("window", {
      location: { protocol: "http:", host: "localhost:9999" },
    });
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    clearAuthToken();
    // Mock CSRF token endpoint for GET requests
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ csrf_token: "mock-csrf-token", expires_in: 3600 }),
        { status: 200 },
      ),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetchWithAuth adds Authorization header when token set", async () => {
    setAuthToken("secret-token");
    fetchMock.mockResolvedValueOnce(new Response("{}", { status: 200 }));

    await fetchWithAuth("http://localhost:9999/api/test", { method: "GET" });

    const callArgs = fetchMock.mock.calls[0];
    const headers = new Headers(callArgs[1]?.headers);
    expect(headers.get("Authorization")).toBe("Bearer secret-token");
  });

  it("fetchWithAuth does not add Authorization when no token", async () => {
    fetchMock.mockResolvedValueOnce(new Response("{}", { status: 200 }));

    await fetchWithAuth("http://localhost:9999/api/test");

    const callArgs = fetchMock.mock.calls[0];
    if (callArgs[1]?.headers) {
      const headers = new Headers(callArgs[1].headers);
      expect(headers.get("Authorization")).toBeNull();
    }
  });

  it("fetchWithAuth adds CSRF token on POST requests", async () => {
    await fetchWithAuth("http://localhost:9999/api/start", { method: "POST" });

    const callArgs = fetchMock.mock.calls[1];
    const headers = new Headers(callArgs[1]?.headers);
    expect(headers.get("X-CSRF-Token")).toBe("mock-csrf-token");
  });

  it("fetchWithAuth does not fetch CSRF token on GET requests", async () => {
    fetchMock.mockResolvedValueOnce(new Response("{}", { status: 200 }));

    await fetchWithAuth("http://localhost:9999/api/status", { method: "GET" });

    // First call should be the GET, not CSRF fetch
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:9999/api/status");
  });
});

describe("apiCall", () => {
  let fetchMock: any;

  beforeEach(() => {
    __testing_setCsrfToken(null);
    vi.stubGlobal("window", {
      location: { protocol: "http:", host: "localhost:9999" },
    });
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("makes GET request without body", async () => {
    const mockData = { key: "value" };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(mockData), { status: 200 }),
    );

    const result = await apiCall<typeof mockData>("GET", "/api/config");
    expect(result).toEqual(mockData);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:9999/api/config",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("makes POST request with body and CSRF token", async () => {
    const mockData = { status: "started" };
    const body = { action: "start" };
    // First call: CSRF token fetch
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ csrf_token: "test-csrf", expires_in: 3600 }),
        { status: 200 },
      ),
    );
    // Second call: the actual POST
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(mockData), { status: 200 }),
    );

    const result = await apiCall<typeof mockData>("POST", "/api/start", body);
    expect(result).toEqual(mockData);

    const csrfCall = fetchMock.mock.calls[0];
    expect(csrfCall[0]).toContain("/api/auth/csrf-token");

    const postCall = fetchMock.mock.calls[1];
    expect(postCall[1]?.method).toBe("POST");
    expect(postCall[1]?.body).toBe(JSON.stringify(body));
    const headers = new Headers(postCall[1]?.headers);
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-CSRF-Token")).toBe("test-csrf");
  });

  it("strips leading slashes from path", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({}), { status: 200 }),
    );

    await apiCall("GET", "///api/test");
    const callArgs = fetchMock.mock.calls[0];
    expect(callArgs[0]).toBe("http://localhost:9999/api/test");
  });

  it("throws ApiError on non-ok response", async () => {
    fetchMock.mockResolvedValue(
      new Response("Not Found", { status: 404, statusText: "Not Found" }),
    );

    try {
      await apiCall("GET", "/api/nonexistent");
    } catch (e) {
      const err = e as ApiError;
      expect(err.status).toBe(404);
      expect(err.statusText).toBe("Not Found");
      expect(err.message).toContain("404");
    }
  });

  it("ApiError captures response text on error", async () => {
    __testing_setCsrfToken("test-csrf");
    fetchMock.mockResolvedValueOnce(
      new Response('{"error": "invalid"}', {
        status: 400,
        statusText: "Bad Request",
      }),
    );

    try {
      await apiCall("POST", "/api/config", {});
    } catch (e) {
      const err = e as ApiError;
      expect(err.message).toContain("invalid");
    }
  });

  it("uses the server /api contract for module and input controls", async () => {
    __testing_setCsrfToken("test-csrf");
    fetchMock.mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ status: "ok", modules: [] }), {
          status: 200,
        }),
      ),
    );

    await toggleModule("translator", true);
    await getModules();
    await inputPlay();
    await inputPause();
    await inputSeek(12);

    expect(fetchMock.mock.calls.map((call: unknown[]) => call[0])).toEqual([
      "http://localhost:9999/api/modules/translator/toggle",
      "http://localhost:9999/api/modules",
      "http://localhost:9999/api/input/control/play",
      "http://localhost:9999/api/input/control/pause",
      "http://localhost:9999/api/input/control/seek",
    ]);
  });
});

describe("WSClient - Basic Tests", () => {
  it("WSClient constructor sets URL", () => {
    const client = new WSClient("ws://localhost:9999/ws/logs");
    expect(client).toBeDefined();
  });

  it("WSClient methods are chainable", () => {
    const client = new WSClient("ws://localhost:9999/ws/logs");
    expect(client.onMessage(() => {})).toBe(client);
    expect(client.onError(() => {})).toBe(client);
    expect(client.onClose(() => {})).toBe(client);
  });

  it("WSClient close prevents reconnect", () => {
    const client = new WSClient("ws://localhost:9999/ws/logs");
    client.close();
    expect(client["_isManualClose"]).toBe(true);
  });

  it("WSClient isConnected returns false when not connected", () => {
    const client = new WSClient("ws://localhost:9999/ws/logs");
    expect(client.isConnected()).toBe(false);
  });

  it("WSClient send does not throw when not connected", () => {
    const client = new WSClient("ws://localhost:9999/ws/logs");
    expect(() => client.send({ type: "auth", token: "abc" })).not.toThrow();
  });
});

describe("WSClient - Exponential Backoff", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("WSClient accepts maxReconnectAttempts config", () => {
    const client = new WSClient("ws://localhost:9999/ws", {
      maxReconnectAttempts: 3,
    });
    expect(client["maxReconnectAttempts"]).toBe(3);
  });

  it("WSClient accepts backoffBase config", () => {
    const client = new WSClient("ws://localhost:9999/ws", {
      backoffBase: 2000,
    });
    expect(client["backoffBase"]).toBe(2000);
  });

  it("WSClient defaults to sensible values", () => {
    const client = new WSClient("ws://localhost:9999/ws");
    expect(client["maxReconnectAttempts"]).toBe(Number.POSITIVE_INFINITY);
    expect(client["backoffBase"]).toBe(1000);
    expect(client["maxBackoff"]).toBe(30000);
    expect(client["jitter"]).toBe(500);
  });

  it("WSClient calculates backoff with exponential + jitter", () => {
    const client = new WSClient("ws://localhost:9999/ws", {
      backoffBase: 1000,
      jitter: 500,
    });
    client["reconnectAttempts"] = 1;
    const delay = client["calculateBackoff"]();
    // Base * 2^1 = 2000, plus jitter 0-500, capped at 30000
    expect(delay).toBeGreaterThanOrEqual(2000);
    expect(delay).toBeLessThanOrEqual(2500);
  });

  it("WSClient caps backoff at maxBackoff", () => {
    const client = new WSClient("ws://localhost:9999/ws", {
      backoffBase: 1000,
      maxBackoff: 5000,
      jitter: 0,
    });
    client["reconnectAttempts"] = 10;
    const delay = client["calculateBackoff"]();
    expect(delay).toBe(5000);
  });

  it("WSClient getReconnectAttempts returns current count", () => {
    const client = new WSClient("ws://localhost:9999/ws");
    expect(client.getReconnectAttempts()).toBe(0);
  });
});

describe("WSClient - Auth Token", () => {
  it("WSClient accepts authToken in config", () => {
    const client = new WSClient("ws://localhost:9999/ws", {
      authToken: "my-token",
    });
    expect(client["authToken"]).toBe("my-token");
  });

  it("WSClient defaults authToken to null", () => {
    const client = new WSClient("ws://localhost:9999/ws");
    expect(client["authToken"]).toBeNull();
  });

  it("adds the token before opening the socket", () => {
    class FakeWebSocket {
      static instances: FakeWebSocket[] = [];
      public onopen: (() => void) | null = null;
      public onmessage: ((event: MessageEvent) => void) | null = null;
      public onerror: ((event: Event) => void) | null = null;
      public onclose: (() => void) | null = null;
      public readyState = WebSocket.OPEN;
      public send = vi.fn();
      public close = vi.fn();

      constructor(public readonly url: string) {
        FakeWebSocket.instances.push(this);
      }
    }

    vi.stubGlobal("WebSocket", FakeWebSocket);
    const client = new WSClient("ws://localhost:9999/ws/logs", {
      authToken: "token with spaces",
    });

    client.connect();

    expect(FakeWebSocket.instances[0].url).toBe(
      "ws://localhost:9999/ws/logs?token=token%20with%20spaces",
    );
    expect(FakeWebSocket.instances[0].send).not.toHaveBeenCalled();
    client.close();
  });
});
