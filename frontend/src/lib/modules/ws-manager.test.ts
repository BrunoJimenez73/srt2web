/**
 * Vitest tests for ws-manager.ts
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

const mockWsClientInstance = {
  onMessage: vi.fn().mockReturnThis(),
  onError: vi.fn().mockReturnThis(),
  onClose: vi.fn().mockReturnThis(),
  onOpen: vi.fn().mockReturnThis(),
  connect: vi.fn(),
  close: vi.fn(),
  send: vi.fn(),
};

const mockWSClientConstructor = vi.fn(function () {
  return mockWsClientInstance;
});

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    WSClient: mockWSClientConstructor as any,
  };
});

describe("ws-manager", () => {
  let addLogSpy: any;
  let updateStatusSpy: any;
  let wsConnectedSignal: any;

  beforeEach(async () => {
    vi.stubGlobal("window", {
      location: { protocol: "http:", host: "localhost:9999" },
    });

    const store: Record<string, string> = {};
    vi.stubGlobal("localStorage", {
      getItem: vi.fn((key: string) => store[key] || null),
      setItem: vi.fn((key: string, value: string) => {
        store[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete store[key];
      }),
    });

    mockWsClientInstance.onMessage.mockClear();
    mockWsClientInstance.onError.mockClear();
    mockWsClientInstance.onClose.mockClear();
    mockWsClientInstance.onOpen.mockClear();
    mockWsClientInstance.connect.mockClear();
    mockWsClientInstance.close.mockClear();

    const signals = await import("../store/signals");
    addLogSpy = vi.spyOn(signals, "addLog");
    updateStatusSpy = vi.spyOn(signals, "updateStatus");
    wsConnectedSignal = signals.wsConnected;
    wsConnectedSignal.value = false;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("getWSClient returns null before connection", async () => {
    const { getWSClient } = await import("./ws-manager");
    expect(getWSClient()).toBeNull();
  });

  it("connectWebSocket creates WSClient with correct URL", async () => {
    const api = await import("../api");
    const { connectWebSocket } = await import("./ws-manager");
    connectWebSocket();

    expect(api.WSClient).toHaveBeenCalledWith(
      "ws://localhost:9999/ws/logs",
      expect.objectContaining({ maxReconnectAttempts: 5, backoffBase: 1000 }),
    );
  });

  it("connectWebSocket calls connect on the client", async () => {
    const { connectWebSocket } = await import("./ws-manager");
    connectWebSocket();
    expect(mockWsClientInstance.connect).toHaveBeenCalled();
  });

  it("connectWebSocket registers message handler for log messages", async () => {
    const { connectWebSocket } = await import("./ws-manager");
    connectWebSocket();

    const onMessageFn = mockWsClientInstance.onMessage.mock.calls[0][0];
    onMessageFn({ type: "log", level: "INFO", message: "test log" });

    expect(addLogSpy).toHaveBeenCalledWith("INFO", "test log");
  });

  it("connectWebSocket handles status messages", async () => {
    const { connectWebSocket } = await import("./ws-manager");
    connectWebSocket();

    const onMessageFn = mockWsClientInstance.onMessage.mock.calls[0][0];
    const statusPayload = {
      state: "running",
      chunks_processed: 5,
      modules: [],
    };
    onMessageFn({ type: "status", status: statusPayload });

    expect(updateStatusSpy).toHaveBeenCalledWith(statusPayload);
  });

  it("connectWebSocket triggers enterPostStartMode on running", async () => {
    const polling = await import("./polling");
    const enterPostStartSpy = vi.spyOn(polling, "enterPostStartMode");

    const { connectWebSocket } = await import("./ws-manager");
    connectWebSocket();

    const onMessageFn = mockWsClientInstance.onMessage.mock.calls[0][0];
    onMessageFn({
      type: "status",
      status: { state: "running", chunks_processed: 5, modules: [] },
    });

    expect(enterPostStartSpy).toHaveBeenCalledOnce();
  });

  it("connectWebSocket does not trigger post-start for stopped", async () => {
    const polling = await import("./polling");
    const enterPostStartSpy = vi.spyOn(polling, "enterPostStartMode");

    const { connectWebSocket } = await import("./ws-manager");
    connectWebSocket();

    const onMessageFn = mockWsClientInstance.onMessage.mock.calls[0][0];
    onMessageFn({
      type: "status",
      status: { state: "stopped", chunks_processed: 0, modules: [] },
    });

    expect(enterPostStartSpy).not.toHaveBeenCalled();
  });

  it("connectWebSocket registers error handler", async () => {
    const { connectWebSocket } = await import("./ws-manager");
    connectWebSocket();

    const onErrorFn = mockWsClientInstance.onError.mock.calls[0][0];
    onErrorFn(new Event("error"));

    expect(addLogSpy).toHaveBeenCalledWith("ERROR", expect.any(String));
  });

  it("connectWebSocket registers close handler", async () => {
    const { connectWebSocket } = await import("./ws-manager");
    connectWebSocket();

    const onCloseFn = mockWsClientInstance.onClose.mock.calls[0][0];
    onCloseFn(true);

    expect(wsConnectedSignal.value).toBe(false);
    expect(addLogSpy).toHaveBeenCalledWith("WARNING", expect.any(String));
  });

  it("connectWebSocket close handler with different message", async () => {
    const { connectWebSocket } = await import("./ws-manager");
    connectWebSocket();

    const onCloseFn = mockWsClientInstance.onClose.mock.calls[0][0];
    onCloseFn(false);

    expect(addLogSpy).toHaveBeenCalledWith("ERROR", expect.any(String));
  });

  it("disconnectWebSocket closes the client", async () => {
    const { connectWebSocket, disconnectWebSocket, getWSClient } = await import(
      "./ws-manager"
    );
    connectWebSocket();

    disconnectWebSocket();
    expect(getWSClient()).toBeNull();
    expect(mockWsClientInstance.close).toHaveBeenCalled();
  });

  it("disconnectWebSocket is safe when not connected", async () => {
    const { disconnectWebSocket } = await import("./ws-manager");
    expect(() => disconnectWebSocket()).not.toThrow();
  });
});
