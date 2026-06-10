import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

import { SubtitleRenderer } from "./subtitle-renderer";

function makeVideo(ct = 0): HTMLVideoElement {
  const v = document.createElement("video");
  Object.defineProperty(v, "currentTime", { value: ct, writable: true });
  return v;
}

function makeContainer(): HTMLElement {
  const c = document.createElement("div");
  c.id = "video-container";
  return c;
}

describe("SubtitleRenderer", () => {
  let renderer: SubtitleRenderer;
  let video: HTMLVideoElement;
  let container: HTMLElement;

  beforeEach(() => {
    vi.clearAllMocks();
    renderer = new SubtitleRenderer();
    video = makeVideo(0);
    container = makeContainer();
    mockFetch.mockResolvedValue({
      ok: true,
      text: vi.fn().mockResolvedValue(
        "#EXTM3U\n#EXT-X-TARGETDURATION:10\n#EXTINF:10.000,\nsubs_seg_000000.vtt"
      ),
    });
  });

  describe("start / stop lifecycle", () => {
    it("creates cue element and attaches event listeners", () => {
      renderer.start(video, container);
      const cueEl = container.querySelector("#subtitle-renderer-cue") as HTMLElement | null;
      expect(cueEl).not.toBeNull();
      expect(cueEl!.style.display).toBe("none");
    });

    it("removes cue element and cleans up on stop", () => {
      renderer.start(video, container);
      renderer.stop();
      const cueEl = container.querySelector("#subtitle-renderer-cue");
      expect(cueEl).toBeNull();
    });

    it("is safe to call stop without start", () => {
      expect(() => renderer.stop()).not.toThrow();
    });
  });

  describe("setEnabled", () => {
    it("hides cue when disabled", () => {
      renderer.start(video, container);
      renderer.setEnabled(false);
      // no error
    });

    it("shows cue again when re-enabled (text was visible)", () => {
      renderer.start(video, container);
      renderer.setEnabled(false);
      renderer.setEnabled(true);
      // should be visible again on next timeupdate
    });
  });

  describe("parseVTT", () => {
    it("parses a single cue with WEBVTT header", () => {
      const vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nHello world";
      const renderer = new SubtitleRenderer();
      const cues = (renderer as any).parseVTT(vtt, 0);
      expect(cues).toHaveLength(1);
      expect(cues[0].globalStart).toBeCloseTo(1, 3);
      expect(cues[0].globalEnd).toBeCloseTo(4, 3);
      expect(cues[0].text).toBe("Hello world");
    });

    it("parses multiple cues with sequential timestamps", () => {
      const vtt = [
        "WEBVTT",
        "",
        "00:00:01.000 --> 00:00:04.000",
        "First cue",
        "",
        "00:00:05.000 --> 00:00:08.000",
        "Second cue",
      ].join("\n");
      const renderer = new SubtitleRenderer();
      const cues = (renderer as any).parseVTT(vtt, 0);
      expect(cues).toHaveLength(2);
      expect(cues[0].text).toBe("First cue");
      expect(cues[0].globalStart).toBeCloseTo(1, 3);
      expect(cues[0].globalEnd).toBeCloseTo(4, 3);
      expect(cues[1].text).toBe("Second cue");
      expect(cues[1].globalStart).toBeCloseTo(5, 3);
      expect(cues[1].globalEnd).toBeCloseTo(8, 3);
    });

    it("applies segmentStartTime offset to global timestamps", () => {
      const vtt = "WEBVTT\n\n00:00:02.000 --> 00:00:06.000\nOffset test";
      const renderer = new SubtitleRenderer();
      // segmentStartTime=30 (actual accumulated duration from EXTINF)
      const cues = (renderer as any).parseVTT(vtt, 30);
      expect(cues[0].globalStart).toBeCloseTo(32, 3);
      expect(cues[0].globalEnd).toBeCloseTo(36, 3);
    });

    it("handles empty VTT gracefully", () => {
      const renderer = new SubtitleRenderer();
      const cues = (renderer as any).parseVTT("", 0);
      expect(cues).toHaveLength(0);
    });

    it("handles VTT without cues gracefully", () => {
      const renderer = new SubtitleRenderer();
      const cues = (renderer as any).parseVTT("WEBVTT\n", 0);
      expect(cues).toHaveLength(0);
    });

    it("handles multi-line cue text", () => {
      const vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nLine one\nLine two";
      const renderer = new SubtitleRenderer();
      const cues = (renderer as any).parseVTT(vtt, 0);
      expect(cues).toHaveLength(1);
      expect(cues[0].text).toBe("Line one Line two");
    });
  });

  describe("playlist parsing (parsePlaylist)", () => {
    it("extracts targetDuration and mediaSequence", () => {
      const playlist = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        "#EXT-X-TARGETDURATION:6",
        "#EXT-X-MEDIA-SEQUENCE:42",
        "#EXTINF:6.000,",
        "subs_seg_000042.vtt",
        "#EXTINF:6.000,",
        "subs_seg_000043.vtt",
      ].join("\n");
      (renderer as any).parsePlaylist(playlist);
      expect((renderer as any).targetDuration).toBe(6);
      expect((renderer as any).mediaSequence).toBe(42);
      // accumulatedTime bootstraps from mediaSequence * targetDuration (42*6=252)
      // then advances for each new segment (+6+6=+12)
      expect((renderer as any).accumulatedTime).toBe(252 + 12);
    });

    it("loads new segments not in knownSegments with correct accumulated time", () => {
      const playlist = [
        "#EXTM3U",
        "#EXT-X-TARGETDURATION:10",
        "#EXT-X-MEDIA-SEQUENCE:5",
        "#EXTINF:9.880,",
        "subs_seg_000005.vtt",
        "#EXTINF:10.120,",
        "subs_seg_000006.vtt",
      ].join("\n");
      const loadSpy = vi.spyOn(renderer as any, "loadSegment");
      (renderer as any).parsePlaylist(playlist);
      expect(loadSpy).toHaveBeenCalledTimes(2);
      // accumulatedTime bootstraps from mediaSequence * targetDuration (5*10=50)
      // segment 5 starts at 50, segment 6 at 50+9.880=59.880
      expect(loadSpy).toHaveBeenCalledWith("subs_seg_000005.vtt", 5, 50);
      expect(loadSpy).toHaveBeenCalledWith("subs_seg_000006.vtt", 6, 59.880);
    });

    it("skips already-known segments without advancing accumulatedTime", () => {
      const playlist = [
        "#EXTM3U",
        "#EXT-X-MEDIA-SEQUENCE:5",
        "#EXTINF:9.880,",
        "subs_seg_000005.vtt",
      ].join("\n");
      (renderer as any).knownSegments.add("subs_seg_000005.vtt");
      const loadSpy = vi.spyOn(renderer as any, "loadSegment");
      (renderer as any).parsePlaylist(playlist);
      expect(loadSpy).not.toHaveBeenCalled();
      // bootstrap fires (firstParse, mediaSequence=5, accumulatedTime=0)
      // but no advancement since no new segments
      // targetDuration default is 10 → bootstrap sets 5*10=50
      expect((renderer as any).accumulatedTime).toBe(50);
    });

    it("trims old knownSegments when > 60", () => {
      for (let i = 0; i < 65; i++) {
        (renderer as any).knownSegments.add(`seg_${String(i).padStart(6, "0")}.vtt`);
      }
      expect((renderer as any).knownSegments.size).toBe(65);
      const playlist = [
        "#EXTM3U",
        "#EXT-X-MEDIA-SEQUENCE:100",
        "subs_seg_000100.vtt",
      ].join("\n");
      (renderer as any).parsePlaylist(playlist);
      expect((renderer as any).knownSegments.size).toBeLessThanOrEqual(60);
    });

    it("trims cues array when > 600", () => {
      for (let i = 0; i < 700; i++) {
        (renderer as any).cues.push({
          globalStart: i,
          globalEnd: i + 1,
          text: `cue ${i}`,
        });
      }
      expect((renderer as any).cues.length).toBe(700);
      const playlist = [
        "#EXTM3U",
        "#EXT-X-MEDIA-SEQUENCE:0",
        "subs_seg_000000.vtt",
      ].join("\n");
      (renderer as any).parsePlaylist(playlist);
      expect((renderer as any).cues.length).toBeLessThanOrEqual(600);
    });
  });

  describe("onTimeUpdate cue selection", () => {
    it("selects active cue at current time", () => {
      (renderer as any).cues = [
        { globalStart: 5, globalEnd: 10, text: "First block" },
        { globalStart: 10, globalEnd: 15, text: "Second block" },
      ];
      renderer.start(video, container);
      video.currentTime = 7;
      video.dispatchEvent(new Event("timeupdate"));

      const cueEl = container.querySelector("#subtitle-renderer-cue") as HTMLElement;
      expect(cueEl.textContent).toBe("First block");
      expect(cueEl.style.display).toBe("block");
    });

    it("renders nothing when no active cue", () => {
      (renderer as any).cues = [
        { globalStart: 5, globalEnd: 10, text: "Block" },
      ];
      renderer.start(video, container);
      video.currentTime = 2;
      video.dispatchEvent(new Event("timeupdate"));

      const cueEl = container.querySelector("#subtitle-renderer-cue") as HTMLElement;
      expect(cueEl.style.display).toBe("none");
    });

    it("renders nothing between cues", () => {
      (renderer as any).cues = [
        { globalStart: 5, globalEnd: 8, text: "Block A" },
        { globalStart: 12, globalEnd: 15, text: "Block B" },
      ];
      renderer.start(video, container);
      video.currentTime = 10;
      video.dispatchEvent(new Event("timeupdate"));

      const cueEl = container.querySelector("#subtitle-renderer-cue") as HTMLElement;
      expect(cueEl.style.display).toBe("none");
    });

    it("switches cues at boundary", () => {
      (renderer as any).cues = [
        { globalStart: 5, globalEnd: 10, text: "First" },
        { globalStart: 10, globalEnd: 15, text: "Second" },
      ];
      renderer.start(video, container);
      video.currentTime = 9.5;
      video.dispatchEvent(new Event("timeupdate"));

      const cueEl = container.querySelector("#subtitle-renderer-cue") as HTMLElement;
      expect(cueEl.textContent).toBe("First");

      video.currentTime = 10;
      video.dispatchEvent(new Event("timeupdate"));

      expect(cueEl.textContent).toBe("Second");
    });

    it("hides cue when disabled during playback", () => {
      (renderer as any).cues = [
        { globalStart: 0, globalEnd: 10, text: "Visible" },
      ];
      renderer.start(video, container);
      video.currentTime = 5;
      video.dispatchEvent(new Event("timeupdate"));

      const cueEl = container.querySelector("#subtitle-renderer-cue") as HTMLElement;
      expect(cueEl.textContent).toBe("Visible");

      renderer.setEnabled(false);
      expect(cueEl.style.display).toBe("none");
    });

    it("does not update DOM if text is unchanged", () => {
      (renderer as any).cues = [
        { globalStart: 0, globalEnd: 10, text: "Same text" },
      ];
      renderer.start(video, container);
      video.currentTime = 3;
      video.dispatchEvent(new Event("timeupdate"));

      const cueEl = container.querySelector("#subtitle-renderer-cue") as HTMLElement;

      // spy after the first render so lastActiveText is set
      const setter = vi.fn();
      Object.defineProperty(cueEl, "textContent", { configurable: true, set: setter });

      video.currentTime = 5;
      video.dispatchEvent(new Event("timeupdate"));

      expect(setter).not.toHaveBeenCalled();
    });
  });
});
