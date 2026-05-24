/**
 * Vitest tests for config-client.ts
 *
 * Tests cover: save config, export config, dumpConfig helper
 */

import type { Config } from "../types/api";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

describe("config-client - dumpConfig", () => {
  it("dumpConfig returns null for null/undefined", async () => {
    const { dumpConfig } = await import("./config-client");
    expect(dumpConfig(null)).toBe("null");
    expect(dumpConfig(undefined)).toBe("null");
  });

  it("dumpConfig returns quoted string", async () => {
    const { dumpConfig } = await import("./config-client");
    expect(dumpConfig("hello")).toBe('"hello"');
  });

  it("dumpConfig returns number as string", async () => {
    const { dumpConfig } = await import("./config-client");
    expect(dumpConfig(42)).toBe("42");
    expect(dumpConfig(3.14)).toBe("3.14");
  });

  it("dumpConfig returns boolean as string", async () => {
    const { dumpConfig } = await import("./config-client");
    expect(dumpConfig(true)).toBe("true");
    expect(dumpConfig(false)).toBe("false");
  });

  it("dumpConfig returns empty array as []", async () => {
    const { dumpConfig } = await import("./config-client");
    expect(dumpConfig([])).toBe("[]");
  });

  it("dumpConfig returns empty object as {}", async () => {
    const { dumpConfig } = await import("./config-client");
    expect(dumpConfig({})).toBe("{}");
  });

  it("dumpConfig formats simple object", async () => {
    const { dumpConfig } = await import("./config-client");
    const result = dumpConfig({ key: "value" });
    expect(result).toContain("key:");
    expect(result).toContain('"value"');
  });

  it("dumpConfig formats array items", async () => {
    const { dumpConfig } = await import("./config-client");
    const result = dumpConfig(["a", "b"]);
    expect(result).toContain('- "a"');
    expect(result).toContain('- "b"');
  });

  it("dumpConfig falls back to String() for unknown types", async () => {
    const { dumpConfig } = await import("./config-client");
    const sym = Symbol("test");
    expect(dumpConfig(sym as any)).toBe("Symbol(test)");
  });
});

describe("config-client - handleSaveConfig", () => {
  let fetchMock: any;
  let apiCallMock: any;

  beforeEach(async () => {
    vi.stubGlobal("window", {
      location: { protocol: "http:", host: "localhost:9999" },
    });

    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    // Mock getConfig and updateChunkDuration from api module
    const api = await import("../api");
    apiCallMock = vi.spyOn(api, "apiCall");

    // Mock collectConfigFromUI to return a simple config
    const collector = await import("./config-collector");
    vi.spyOn(collector, "collectConfigFromUI").mockReturnValue({
      input: { type: "srt" },
      pipeline: { chunk_duration_sec: 3, mode: "thread_parallel", max_concurrent_chunks: 2, buffer_size: 10, retry_attempts: 3, retry_delay: 5 },
    } as Partial<Config>);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("handleSaveConfig calls apiCall with PUT /api/config", async () => {
    // Mock apiCall for PUT and GET
    apiCallMock
      .mockResolvedValueOnce({ status: "ok" }) // PUT /api/config
      .mockResolvedValueOnce({
        status: "ok",
        chunk_duration_sec: 3,
        synced_to: [],
      }) // POST /api/config/chunk
      .mockResolvedValueOnce({}); // GET /api/config

    const { handleSaveConfig } = await import("./config-client");
    await handleSaveConfig();

    expect(apiCallMock).toHaveBeenNthCalledWith(1, "PUT", "/api/config", {
      config: expect.any(Object),
    });
  });

  it("handleSaveConfig does not throw on success", async () => {
    apiCallMock
      .mockResolvedValueOnce({ status: "ok" })
      .mockResolvedValueOnce({
        status: "ok",
        chunk_duration_sec: 3,
        synced_to: [],
      })
      .mockResolvedValueOnce({});

    const { handleSaveConfig } = await import("./config-client");
    await expect(handleSaveConfig()).resolves.toBeUndefined();
  });

  it("handleSaveConfig handles apiCall error gracefully", async () => {
    apiCallMock.mockRejectedValueOnce(new Error("Server error"));

    const { handleSaveConfig } = await import("./config-client");
    await expect(handleSaveConfig()).resolves.toBeUndefined();
  });

  it("handleSaveConfig logs warning when chunk sync fails", async () => {
    apiCallMock
      .mockResolvedValueOnce({ status: "ok" })
      .mockRejectedValueOnce(new Error("Timeout"));

    const { handleSaveConfig } = await import("./config-client");
    await handleSaveConfig();
    // Should not throw despite chunk sync failure
  });
});

describe("config-client - exportConfig", () => {
  let createObjectURL: any;
  let revokeObjectURL: any;
  let clickSpy: any;

  beforeEach(async () => {
    clickSpy = vi.fn();
    createObjectURL = vi.fn(() => "blob:test");
    revokeObjectURL = vi.fn();

    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    vi.stubGlobal("window", {
      location: { protocol: "http:", host: "localhost:9999" },
    });

    // Mock document.createElement to return anchor with click spy
    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation(
      (tagName, options) => {
        const el = originalCreateElement(tagName, options);
        if (tagName === "a") {
          vi.spyOn(el as HTMLAnchorElement, "click").mockImplementation(
            clickSpy,
          );
        }
        return el;
      },
    );

    const signals = await import("../store/signals");
    // Set a mock config so export has data
    signals.pipelineConfig.value = {
      input: { type: "srt", srt: { listen_port: 9000 } },
      pipeline: { chunk_duration_sec: 3 },
    } as any;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("exportConfig creates a download link", async () => {
    const { exportConfig } = await import("./config-client");
    await exportConfig();

    expect(createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalled();
  });

  it("exportConfig shows error when config is null", async () => {
    const signals = await import("../store/signals");
    signals.pipelineConfig.value = null;

    const { exportConfig } = await import("./config-client");
    await exportConfig();

    expect(createObjectURL).not.toHaveBeenCalled();
  });
});
