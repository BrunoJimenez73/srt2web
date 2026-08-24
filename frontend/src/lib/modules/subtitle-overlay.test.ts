import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  parseSegIndex,
  pickActiveSegments,
  initSubtitleOverlay,
  type RailChunk,
} from "./subtitle-overlay";

describe("parseSegIndex", () => {
  it("parses plain segment URLs", () => {
    expect(parseSegIndex("/hls/seg_000007.ts")).toBe(7);
    expect(parseSegIndex("http://x/hls/seg_000123.ts")).toBe(123);
  });

  it("returns null for non-segment URLs", () => {
    expect(parseSegIndex("/hls/stream.m3u8")).toBeNull();
    expect(parseSegIndex("")).toBeNull();
  });
});

describe("pickActiveSegments", () => {
  const chunks: RailChunk[] = [
    { idx: 1, dur: 10, segments: [{ s: 0, e: 4, text: "uno" }] },
    {
      idx: 2,
      dur: 10,
      segments: [
        { s: 0.5, e: 5, text: "dos-a" },
        { s: 5, e: 9.9, text: "dos-b" },
      ],
    },
  ];

  it("picks the segment containing tRel", () => {
    expect(pickActiveSegments(chunks, 2, 3).map((s) => s.text)).toEqual([
      "dos-a",
    ]);
    expect(pickActiveSegments(chunks, 2, 7).map((s) => s.text)).toEqual([
      "dos-b",
    ]);
  });

  it("end is exclusive — no overlap at cue boundary", () => {
    expect(pickActiveSegments(chunks, 1, 4)).toEqual([]);
  });

  it("returns empty for unknown chunk or null index", () => {
    expect(pickActiveSegments(chunks, 99, 1)).toEqual([]);
    expect(pickActiveSegments(chunks, null, 1)).toEqual([]);
  });
});

describe("initSubtitleOverlay", () => {
  let video: HTMLVideoElement;
  const hlsHandlers = new Map<string, (...args: unknown[]) => void>();
  const hls = {
    on: (ev: string, cb: (...args: unknown[]) => void) =>
      hlsHandlers.set(ev, cb),
    off: (ev: string) => hlsHandlers.delete(ev),
  };

  beforeEach(() => {
    document.body.innerHTML =
      '<div id="video-container"><div id="subtitle-overlay"></div></div>';
    video = document.createElement("video");
  });

  afterEach(() => {
    // sin fake timers: el módulo vive de polling real; limpiamos instancias
    document.body.innerHTML = "";
  });

  function mount() {
    return initSubtitleOverlay(video, hls);
  }

  function flushPoll() {
    return new Promise((r) => setTimeout(r, 460));
  }

  function stubFetchRail(payload: unknown) {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => payload }),
    );
  }

  it("renders active cue from the rail", async () => {
    stubFetchRail({
      base: 1,
      chunks: [{ idx: 1, dur: 10, segments: [{ s: 0, e: 4, text: "hola" }] }],
    });

    // Simulate hls.js switching to fragment seg_000001 starting at t=100
    video.currentTime = 102;
    const ctrl = mount();
    hlsHandlers.get("hlsFragChanged")?.("hlsFragChanged", {
      frag: { url: "/hls/seg_000001.ts", start: 100 },
    });

    await flushPoll();

    expect(fetch).toHaveBeenCalled(); // el poll disparó
    const el = document.getElementById("subtitle-overlay");
    expect(el?.textContent).toBe("hola");
    ctrl.stop();
  });

  it("hides overlay when no active segment", async () => {
    stubFetchRail({ base: 1, chunks: [] });
    video.currentTime = 5;
    const ctrl = mount();
    hlsHandlers.get("hlsFragChanged")?.("hlsFragChanged", {
      frag: { url: "/hls/seg_000001.ts", start: 100 },
    });
    await flushPoll();
    const el = document.getElementById("subtitle-overlay");
    expect(el?.textContent).toBe("");
    ctrl.stop();
  });

  it("survives fetch failures and stops cleanly", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    const ctrl = mount();
    await flushPoll(); // no debe lanzar
    ctrl.stop();
    expect(hlsHandlers.has("hlsFragChanged")).toBe(false);
  });
});
