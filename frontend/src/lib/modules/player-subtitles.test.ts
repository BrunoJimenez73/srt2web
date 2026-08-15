/**
 * F108 — HLS.js native subtitle track activation.
 *
 * Regression tests for the new HLS-native subtitle sync path. The previous
 * implementation polled `/subtitles/subs.vtt` every 2s and wipe-and-replaced
 * the active cues, which produced visible desync and flicker. The new path
 * delegates cue rendering to HLS.js, which loads the subtitle media playlist
 * (`subs.m3u8`) natively and uses the same `currentTime` time-base as the
 * video — no polling, no lag, no flicker.
 *
 * These tests cover the `player-subtitles.ts` helper (the unit of logic
 * wired into `player.ts`).
 */

import { describe, it, expect, beforeEach, vi } from "vitest";

// The module under test uses a logger; we don't need to assert on log output
// here, so we mock it to a no-op.
vi.mock("../utils/logger", () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

import type { HlsLike, SubtitleTrackDescriptor } from "./player-subtitles";
import {
  activateFirstSubtitleTrack,
  disableSubtitles,
  forceSubtitleTrackMode,
  getActiveSubtitleTrackId,
  onSubtitleTrackListChange,
} from "./player-subtitles";

function makeHls(tracks: ReadonlyArray<SubtitleTrackDescriptor>): HlsLike {
  return {
    subtitleTrack: -1,
    subtitleDisplay: false,
    subtitleTracks: tracks,
    on: vi.fn(),
    off: vi.fn(),
  };
}

describe("F108 — player-subtitles native track helper", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("activateFirstSubtitleTrack", () => {
    it("activates the first track when no preferred lang given", () => {
      const hls = makeHls([
        { id: 0, lang: "es", name: "Español" },
        { id: 1, lang: "en", name: "English" },
      ]);
      const id = activateFirstSubtitleTrack(hls);
      expect(id).toBe(0);
      expect(hls.subtitleTrack).toBe(0);
      expect(hls.subtitleDisplay).toBe(true);
    });

    it("returns -1 when no subtitle tracks are declared", () => {
      const hls = makeHls([]);
      const id = activateFirstSubtitleTrack(hls);
      expect(id).toBe(-1);
      expect(hls.subtitleTrack).toBe(-1);
      expect(hls.subtitleDisplay).toBe(false);
    });

    it("prefers exact language match (case-insensitive)", () => {
      const hls = makeHls([
        { id: 0, lang: "en", name: "English" },
        { id: 1, lang: "es", name: "Español" },
        { id: 2, lang: "fr", name: "Français" },
      ]);
      const id = activateFirstSubtitleTrack(hls, { preferredLang: "ES" });
      expect(id).toBe(1);
      expect(hls.subtitleTrack).toBe(1);
    });

    it("falls back to language prefix match", () => {
      // User wants 'es' but the manifest has 'es-ES' (region-qualified).
      const hls = makeHls([
        { id: 0, lang: "en", name: "English" },
        { id: 1, lang: "es-ES", name: "Español (España)" },
      ]);
      const id = activateFirstSubtitleTrack(hls, { preferredLang: "es" });
      expect(id).toBe(1);
    });

    it("falls back to the first track when no lang matches", () => {
      const hls = makeHls([
        { id: 0, lang: "en", name: "English" },
        { id: 1, lang: "fr", name: "Français" },
      ]);
      const id = activateFirstSubtitleTrack(hls, { preferredLang: "de" });
      expect(id).toBe(0);
    });

    it("respects showSubtitles=false to keep subtitles hidden", () => {
      const hls = makeHls([{ id: 0, lang: "es" }]);
      activateFirstSubtitleTrack(hls, { showSubtitles: false });
      // Track is selected, but display is left off
      expect(hls.subtitleTrack).toBe(0);
      expect(hls.subtitleDisplay).toBe(false);
    });

    it("filters out closed-caption tracks (type !== 'SUBTITLES')", () => {
      const hls = makeHls([
        { id: 0, lang: "en", type: "CLOSED-CAPTIONS" },
        { id: 1, lang: "es", type: "SUBTITLES" },
      ]);
      const id = activateFirstSubtitleTrack(hls);
      expect(id).toBe(1);
    });

    it("keeps tracks with no type field (legacy hls.js)", () => {
      const hls = makeHls([
        { id: 0, lang: "en" }, // no type — assume SUBTITLES
        { id: 1, lang: "es" },
      ]);
      const id = activateFirstSubtitleTrack(hls);
      expect(id).toBe(0);
    });

    it("prefers allSubtitleTracks over subtitleTracks when both present", () => {
      const hls: HlsLike = {
        subtitleTrack: -1,
        subtitleDisplay: false,
        subtitleTracks: [{ id: 99, lang: "fr" }],
        allSubtitleTracks: [
          { id: 0, lang: "en" },
          { id: 1, lang: "es" },
        ],
        on: vi.fn(),
        off: vi.fn(),
      };
      const id = activateFirstSubtitleTrack(hls, { preferredLang: "es" });
      expect(id).toBe(1);
    });

    it("is safe to call multiple times (re-activation is a no-op for user)", () => {
      const hls = makeHls([{ id: 0, lang: "es" }]);
      expect(activateFirstSubtitleTrack(hls)).toBe(0);
      expect(activateFirstSubtitleTrack(hls)).toBe(0);
      expect(hls.subtitleTrack).toBe(0);
    });
  });

  describe("forceSubtitleTrackMode", () => {
    function makeVideo(
      tracks: Array<{ mode: string; cues?: number; kind?: string }>,
    ): HTMLVideoElement {
      return {
        textTracks: tracks.map((t, i) => ({
          kind: t.kind ?? "subtitles",
          mode: t.mode,
          cues: t.cues !== undefined ? { length: t.cues } : null,
          label: `track-${i}`,
          language: "es",
        })),
      } as unknown as HTMLVideoElement;
    }

    it("forces hidden subtitle tracks to showing and returns the count", () => {
      const video = makeVideo([
        { mode: "hidden" },
        { mode: "disabled", cues: 3 },
      ]);
      const changed = forceSubtitleTrackMode(video);
      expect(changed).toBe(2);
      expect(video.textTracks[0].mode).toBe("showing");
      expect(video.textTracks[1].mode).toBe("showing");
    });

    it("returns 0 when all subtitle tracks are already showing", () => {
      const video = makeVideo([{ mode: "showing" }, { mode: "showing" }]);
      expect(forceSubtitleTrackMode(video)).toBe(0);
    });

    it("ignores non-subtitle tracks (captions, metadata)", () => {
      const video = makeVideo([
        { mode: "hidden", kind: "captions" },
        { mode: "showing" },
        { mode: "disabled", kind: "metadata" },
      ]);
      const changed = forceSubtitleTrackMode(video);
      expect(changed).toBe(0);
      expect(video.textTracks[1].mode).toBe("showing");
    });

    it("is safe on a video without tracks (returns 0)", () => {
      const video = makeVideo([]);
      expect(forceSubtitleTrackMode(video)).toBe(0);
    });
  });

  describe("getActiveSubtitleTrackId", () => {
    it("returns the active track id", () => {
      const hls = makeHls([]);
      hls.subtitleTrack = 3;
      expect(getActiveSubtitleTrackId(hls)).toBe(3);
    });

    it("returns -1 when no track is active", () => {
      const hls = makeHls([]);
      hls.subtitleTrack = -1;
      expect(getActiveSubtitleTrackId(hls)).toBe(-1);
    });
  });

  describe("disableSubtitles", () => {
    it("turns off the active track and hides display", () => {
      const hls = makeHls([{ id: 0, lang: "es" }]);
      activateFirstSubtitleTrack(hls);
      expect(hls.subtitleTrack).toBe(0);
      expect(hls.subtitleDisplay).toBe(true);
      disableSubtitles(hls);
      expect(hls.subtitleTrack).toBe(-1);
      expect(hls.subtitleDisplay).toBe(false);
    });

    it("is safe to call when no track is active", () => {
      const hls = makeHls([]);
      expect(() => disableSubtitles(hls)).not.toThrow();
      expect(hls.subtitleTrack).toBe(-1);
      expect(hls.subtitleDisplay).toBe(false);
    });
  });

  describe("onSubtitleTrackListChange", () => {
    it("calls back with the current usable tracks when the event fires", () => {
      const handler = vi.fn();
      const hls = makeHls([
        { id: 0, lang: "es" },
        { id: 1, lang: "en" },
      ]);
      const callback = vi.fn();
      onSubtitleTrackListChange(hls, callback);

      // The hls.on call must have registered the event name
      expect(hls.on).toHaveBeenCalledWith(
        "hlsSubtitleTracksUpdated",
        expect.any(Function),
      );
      const _handler = handler; // silence unused

      // Manually invoke the registered handler to simulate the event
      const registeredHandler = (hls.on as ReturnType<typeof vi.fn>).mock
        .calls[0][1];
      registeredHandler();

      expect(callback).toHaveBeenCalledWith([
        { id: 0, lang: "es" },
        { id: 1, lang: "en" },
      ]);
    });

    it("filters out closed-captions in the callback", () => {
      const hls = makeHls([
        { id: 0, lang: "en", type: "CLOSED-CAPTIONS" },
        { id: 1, lang: "es", type: "SUBTITLES" },
      ]);
      const callback = vi.fn();
      onSubtitleTrackListChange(hls, callback);
      const registeredHandler = (hls.on as ReturnType<typeof vi.fn>).mock
        .calls[0][1];
      registeredHandler();
      expect(callback).toHaveBeenCalledWith([
        { id: 1, lang: "es", type: "SUBTITLES" },
      ]);
    });

    it("returns an unsubscribe function that detaches the handler", () => {
      const hls = makeHls([{ id: 0, lang: "es" }]);
      const unsubscribe = onSubtitleTrackListChange(hls, vi.fn());
      unsubscribe();
      expect(hls.off).toHaveBeenCalledWith(
        "hlsSubtitleTracksUpdated",
        expect.any(Function),
      );
    });

    it("is safe to unsubscribe when hls.off is missing (no throw)", () => {
      const hls: HlsLike = {
        subtitleTrack: -1,
        subtitleDisplay: false,
        subtitleTracks: [],
        on: vi.fn(),
        // no off — older hls.js polyfill maybe
      };
      const unsubscribe = onSubtitleTrackListChange(hls, vi.fn());
      expect(() => unsubscribe()).not.toThrow();
    });
  });
});
