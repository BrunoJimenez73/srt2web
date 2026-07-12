/**
 * Vitest tests for presets-client.ts
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

describe("presets-client", () => {
  let fetchMock: any;
  let presetsSignal: any;
  let selectedPresetSignal: any;
  let pipelineConfigSignal: any;
  let addLogSpy: any;

  beforeEach(async () => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("window", {
      location: { protocol: "http:", host: "localhost:9999" },
    });
    vi.stubGlobal("localStorage", {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });

    // Pre-populate CSRF cache so mutation tests don't trigger a CSRF fetch
    const api = await import("../api");
    api.__testing_setCsrfToken("mock-csrf-token");

    const signals = await import("../store/signals");
    presetsSignal = signals.presets;
    selectedPresetSignal = signals.selectedPreset;
    pipelineConfigSignal = signals.pipelineConfig;
    addLogSpy = vi.spyOn(signals, "addLog");

    presetsSignal.value = [];
    selectedPresetSignal.value = "";
    pipelineConfigSignal.value = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ── loadPresets ──────────────────────────────────────────────────────────────

  it("loadPresets fetches /api/presets and updates presets signal", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          presets: [
            { name: "default", description: "Default preset" },
            { name: "low-latency", description: "Low latency" },
          ],
        }),
        { status: 200 },
      ),
    );

    const { loadPresets } = await import("./presets-client");
    await loadPresets();

    expect(fetchMock).toHaveBeenCalledWith("/api/presets", expect.anything());
    expect(presetsSignal.value).toEqual([
      { name: "default", description: "Default preset" },
      { name: "low-latency", description: "Low latency" },
    ]);
  });

  it("loadPresets does not update on non-ok response", async () => {
    fetchMock.mockResolvedValueOnce(new Response("Not Found", { status: 404 }));

    const { loadPresets } = await import("./presets-client");
    await loadPresets();

    expect(presetsSignal.value).toEqual([]);
  });

  it("loadPresets handles fetch error and logs error", async () => {
    fetchMock.mockRejectedValueOnce(new Error("Network error"));

    const { loadPresets } = await import("./presets-client");
    await loadPresets();

    expect(addLogSpy).toHaveBeenCalledWith(
      "ERROR",
      expect.stringContaining("error"),
    );
  });

  // ── applyPreset ──────────────────────────────────────────────────────────────

  it("applyPreset sends POST to /api/presets/{name}/apply", async () => {
    const configResponse = {
      config: { input: { type: "srt" }, pipeline: { chunk_duration_sec: 5 } },
    };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(configResponse), { status: 200 }),
    );

    const { applyPreset } = await import("./presets-client");
    await applyPreset("low-latency");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/presets/low-latency/apply",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("applyPreset updates pipelineConfig and selectedPreset on success", async () => {
    const configResponse = {
      config: { input: { type: "srt" }, pipeline: { chunk_duration_sec: 5 } },
    };
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(configResponse), { status: 200 }),
    );

    const { applyPreset } = await import("./presets-client");
    await applyPreset("low-latency");

    expect(pipelineConfigSignal.value).toEqual(configResponse.config);
    expect(selectedPresetSignal.value).toBe("low-latency");
  });

  it("applyPreset logs error when API returns non-ok", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("Server error", { status: 500 }),
    );

    // setting loading fires addLog, so we must account for that
    const { applyPreset } = await import("./presets-client");
    await applyPreset("broken");

    expect(addLogSpy).toHaveBeenLastCalledWith(
      expect.any(String),
      expect.stringContaining("Server error"),
    );
  });

  it("applyPreset handles fetch error gracefully", async () => {
    fetchMock.mockRejectedValueOnce(new Error("Connection refused"));

    const { applyPreset } = await import("./presets-client");
    await applyPreset("test");

    expect(addLogSpy).toHaveBeenLastCalledWith(
      expect.any(String),
      expect.stringContaining("Connection refused"),
    );
  });

  // ── savePreset ───────────────────────────────────────────────────────────────

  it("savePreset sends POST to /api/presets", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ presets: [{ name: "my-preset", description: "" }] }),
          { status: 200 },
        ),
      );

    const { savePreset } = await import("./presets-client");
    await savePreset("my-preset");

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/presets",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "my-preset", description: "" }),
      }),
    );
  });

  it("savePreset reloads presets after saving", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ presets: [{ name: "my-preset", description: "" }] }),
          { status: 200 },
        ),
      );

    const { savePreset } = await import("./presets-client");
    await savePreset("my-preset");

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/presets",
      expect.anything(),
    );
    expect(presetsSignal.value).toEqual([
      { name: "my-preset", description: "" },
    ]);
  });

  it("savePreset logs error on non-ok response", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("Bad Request", { status: 400 }),
    );

    const { savePreset } = await import("./presets-client");
    await savePreset("broken");

    expect(addLogSpy).toHaveBeenLastCalledWith(
      expect.any(String),
      expect.stringContaining("Bad Request"),
    );
  });

  it("savePreset handles fetch error gracefully", async () => {
    fetchMock.mockRejectedValueOnce(new Error("Network error"));

    const { savePreset } = await import("./presets-client");
    await savePreset("test");

    expect(addLogSpy).toHaveBeenLastCalledWith(
      expect.any(String),
      expect.stringContaining("Network error"),
    );
  });
});
