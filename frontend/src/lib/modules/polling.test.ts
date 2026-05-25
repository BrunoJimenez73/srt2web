/**
 * Vitest tests for polling.ts
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    apiCall: vi.fn(),
  };
});

describe("polling - Status Polling", () => {
  let pipelineStatusSignal: any;
  let apiMock: any;

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.stubGlobal("window", {
      location: { protocol: "http:", host: "localhost:9999" },
      origin: "http://localhost:9999",
    });

    const api = await import("../api");
    apiMock = vi.mocked(api.apiCall);

    const signals = await import("../store/signals");
    pipelineStatusSignal = signals.pipelineStatus;
    pipelineStatusSignal.value = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("restartPolling calls apiCall and updates signal", async () => {
    const statusData = { state: "stopped", chunks_processed: 0, modules: [] };
    apiMock.mockResolvedValue(statusData);

    const { restartPolling, stopStatusPolling } = await import("./polling");
    restartPolling();

    // The initial poll() is async; wait for promises
    await vi.advanceTimersByTimeAsync(10);

    expect(apiMock).toHaveBeenCalledWith("GET", "api/status");
    expect(pipelineStatusSignal.value).toEqual(statusData);

    stopStatusPolling();
  });

  it("restartPolling updates pipelineStatus on success", async () => {
    const statusData = { state: "running", chunks_processed: 10, modules: [] };
    apiMock.mockResolvedValue(statusData);

    const { restartPolling, stopStatusPolling } = await import("./polling");
    restartPolling();
    await vi.advanceTimersByTimeAsync(10);

    expect(pipelineStatusSignal.value).toEqual(statusData);
    stopStatusPolling();
  });

  it("restartPolling does not throw on fetch error", async () => {
    apiMock.mockRejectedValue(new Error("Network error"));

    const { restartPolling, stopStatusPolling } = await import("./polling");
    expect(() => restartPolling()).not.toThrow();
    await vi.advanceTimersByTimeAsync(10);

    // Signal unchanged since fetch failed
    expect(pipelineStatusSignal.value).toBeNull();
    stopStatusPolling();
  });

  it("enterPostStartMode uses fast polling interval", async () => {
    apiMock.mockResolvedValue({
      state: "stopped",
      chunks_processed: 0,
      modules: [],
    });

    const { enterPostStartMode, stopStatusPolling } = await import("./polling");
    apiMock.mockClear();

    // enterPostStartMode calls restartPolling internally
    enterPostStartMode();
    await vi.advanceTimersByTimeAsync(10);

    // Should have called apiCall once from the restart inside enterPostStartMode
    expect(apiMock).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1000);
    // Post-start interval = 1s, so should have called 2 times now
    expect(apiMock).toHaveBeenCalledTimes(2);

    stopStatusPolling();
  });

  it("exitPostStartMode cancels fast mode", async () => {
    apiMock.mockResolvedValue({
      state: "stopped",
      chunks_processed: 0,
      modules: [],
    });

    const { enterPostStartMode, exitPostStartMode, stopStatusPolling } =
      await import("./polling");
    apiMock.mockClear();

    enterPostStartMode();
    await vi.advanceTimersByTimeAsync(10);
    apiMock.mockClear();

    exitPostStartMode();
    await vi.advanceTimersByTimeAsync(10);
    // exitPostStartMode calls restartPolling → 1 call
    expect(apiMock).toHaveBeenCalledTimes(1);

    stopStatusPolling();
  });

  it("post-start auto-exits after 5s", async () => {
    apiMock.mockResolvedValue({
      state: "stopped",
      chunks_processed: 0,
      modules: [],
    });

    const { enterPostStartMode, stopStatusPolling } = await import("./polling");
    apiMock.mockClear();

    enterPostStartMode();
    await vi.advanceTimersByTimeAsync(10);
    // count = 1 (initial restart from enterPostStartMode)
    apiMock.mockClear();

    // 5s of post-start polling at 1s intervals
    await vi.advanceTimersByTimeAsync(5000);
    expect(apiMock.mock.calls.length).toBeGreaterThanOrEqual(4);
    expect(apiMock.mock.calls.length).toBeLessThanOrEqual(6);

    stopStatusPolling();
  });

  it("stopStatusPolling clears intervals", async () => {
    apiMock.mockResolvedValue({
      state: "running",
      chunks_processed: 5,
      modules: [],
    });

    const { restartPolling, stopStatusPolling } = await import("./polling");
    restartPolling();
    await vi.advanceTimersByTimeAsync(10);
    apiMock.mockClear();

    stopStatusPolling();
    await vi.advanceTimersByTimeAsync(10000);

    expect(apiMock).not.toHaveBeenCalled();
  });

  it("polls at slower interval when status is stopped (10s)", async () => {
    apiMock.mockResolvedValue({
      state: "stopped",
      chunks_processed: 0,
      modules: [],
    });

    const { restartPolling, stopStatusPolling } = await import("./polling");
    restartPolling();
    await vi.advanceTimersByTimeAsync(10);
    expect(apiMock).toHaveBeenCalledTimes(1);
    apiMock.mockClear();

    // 9s → no call yet
    await vi.advanceTimersByTimeAsync(9000);
    expect(apiMock).not.toHaveBeenCalled();

    // +2s = 11s total after restart → should have polled once
    await vi.advanceTimersByTimeAsync(2000);
    expect(apiMock).toHaveBeenCalledTimes(1);

    stopStatusPolling();
  });
});

describe("polling - File Info Polling", () => {
  let fetchMock: any;
  let container: HTMLDivElement;

  beforeEach(() => {
    vi.useFakeTimers();

    fetchMock = vi.fn();

    // Need to preserve jsdom's window.location.origin by not replacing the whole window
    // Only stub fetch on the window
    vi.stubGlobal("fetch", fetchMock);

    // Stub localStorage for fetchWithAuth's getAuthToken
    vi.stubGlobal("localStorage", {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });

    // Use existing window with proper location.origin
    Object.defineProperty(window, "location", {
      value: {
        protocol: "http:",
        host: "localhost:9999",
        origin: "http://localhost:9999",
      },
      configurable: true,
      writable: true,
    });

    container = document.createElement("div");
    document.body.appendChild(container);

    const slider = document.createElement("input");
    slider.id = "input-file-position";
    slider.type = "range";
    container.appendChild(slider);

    const current = document.createElement("span");
    current.id = "file-time-current";
    container.appendChild(current);

    const total = document.createElement("span");
    total.id = "file-time-total";
    container.appendChild(total);

    const playBtn = document.createElement("button");
    playBtn.id = "btn-file-play";
    playBtn.style.display = "inline";
    container.appendChild(playBtn);

    const pauseBtn = document.createElement("button");
    pauseBtn.id = "btn-file-pause";
    pauseBtn.style.display = "none";
    container.appendChild(pauseBtn);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    document.body.innerHTML = "";
  });

  it("startFileInfoPolling fetches input-info periodically", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "file",
          duration: 120,
          position: 30,
          is_playing: true,
        }),
        { status: 200 },
      ),
    );

    const { startFileInfoPolling, stopFileInfoPolling } = await import(
      "./polling"
    );
    startFileInfoPolling();
    await vi.advanceTimersByTimeAsync(500);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/input-info",
      expect.anything(),
    );

    stopFileInfoPolling();
  });

  it("startFileInfoPolling updates slider and displays", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "file",
          duration: 120,
          position: 30,
          is_playing: true,
        }),
        { status: 200 },
      ),
    );

    const { startFileInfoPolling, stopFileInfoPolling } = await import(
      "./polling"
    );
    startFileInfoPolling();
    await vi.advanceTimersByTimeAsync(500);

    const slider = document.getElementById(
      "input-file-position",
    ) as HTMLInputElement;
    const current = document.getElementById(
      "file-time-current",
    ) as HTMLSpanElement;
    const total = document.getElementById("file-time-total") as HTMLSpanElement;

    expect(slider.value).toBe("25");
    expect(current.textContent).toBe("0:30");
    expect(total.textContent).toBe("2:00");

    stopFileInfoPolling();
  });

  it("startFileInfoPolling toggles play/pause buttons", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "file",
          duration: 60,
          position: 10,
          is_playing: false,
        }),
        { status: 200 },
      ),
    );

    const { startFileInfoPolling, stopFileInfoPolling } = await import(
      "./polling"
    );
    startFileInfoPolling();
    await vi.advanceTimersByTimeAsync(500);

    const playBtn = document.getElementById(
      "btn-file-play",
    ) as HTMLButtonElement;
    const pauseBtn = document.getElementById(
      "btn-file-pause",
    ) as HTMLButtonElement;

    expect(playBtn.style.display).toBe("inline");
    expect(pauseBtn.style.display).toBe("none");

    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "file",
          duration: 60,
          position: 20,
          is_playing: true,
        }),
        { status: 200 },
      ),
    );

    await vi.advanceTimersByTimeAsync(500);
    expect(playBtn.style.display).toBe("none");
    expect(pauseBtn.style.display).toBe("inline");

    stopFileInfoPolling();
  });

  it("startFileInfoPolling handles non-file response", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ type: "srt" }), { status: 200 }),
    );

    const { startFileInfoPolling, stopFileInfoPolling } = await import(
      "./polling"
    );
    expect(() => startFileInfoPolling()).not.toThrow();
    await vi.advanceTimersByTimeAsync(500);

    stopFileInfoPolling();
  });

  it("startFileInfoPolling handles fetch error gracefully", async () => {
    fetchMock.mockRejectedValue(new Error("Network error"));

    const { startFileInfoPolling, stopFileInfoPolling } = await import(
      "./polling"
    );
    expect(() => startFileInfoPolling()).not.toThrow();
    await vi.advanceTimersByTimeAsync(500);

    stopFileInfoPolling();
  });

  it("stopFileInfoPolling clears the interval", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "file",
          duration: 60,
          position: 0,
          is_playing: false,
        }),
        { status: 200 },
      ),
    );

    const { startFileInfoPolling, stopFileInfoPolling } = await import(
      "./polling"
    );
    startFileInfoPolling();
    await vi.advanceTimersByTimeAsync(500);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    stopFileInfoPolling();
    fetchMock.mockClear();
    await vi.advanceTimersByTimeAsync(2000);

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
