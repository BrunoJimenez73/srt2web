/**
 * F205 — Client-side subtitle overlay fed by the JSON "subtitle rail".
 *
 * Replaces the HLS-native WebVTT path for the web player. The server
 * exposes GET /api/subtitles/recent (rolling window of chunks with their
 * segments); this module polls it and renders the active cues against
 * hls.js's own video positions — the same clock as the dubbed audio —
 * so sync holds for late joiners, seeks and stalls by construction.
 */

import { logger } from "../utils/logger";

export interface RailSegment {
  s: number;
  e: number;
  text: string;
}

export interface RailChunk {
  idx: number;
  dur: number;
  segments: RailSegment[];
}

export interface SubtitleRail {
  base: number;
  chunks: RailChunk[];
}

/** Minimal structural typing of the hls.js instance we need. */
export interface HlsLike {
  on(event: string, callback: (...args: unknown[]) => void): void;
  off(event: string, callback: (...args: unknown[]) => void): void;
}

interface FragChangedData {
  frag?: { url?: string; start?: number };
}

const POLL_INTERVAL_MS = 400;
const RAIL_URL = "/api/subtitles/recent?count=16";
export const SUBTITLE_OVERLAY_ID = "subtitle-overlay";

/** Extract the chunk index from an HLS fragment URL like .../seg_000007.ts */
export function parseSegIndex(url: string): number | null {
  const m = /seg_(\d+)\.(?:ts|m4s)$/.exec(url);
  return m ? Number.parseInt(m[1], 10) : null;
}

/** Segments of `idx` whose window contains local time `tRel`. */
export function pickActiveSegments(
  chunks: RailChunk[],
  idx: number | null,
  tRel: number,
): RailSegment[] {
  if (idx === null) return [];
  const chunk = chunks.find((c) => c.idx === idx);
  if (!chunk) return [];
  return chunk.segments.filter((s) => tRel >= s.s && tRel < s.e);
}

function isRail(value: unknown): value is SubtitleRail {
  if (!value || typeof value !== "object") return false;
  const v = value as { base?: unknown; chunks?: unknown };
  return typeof v.base === "number" && Array.isArray(v.chunks);
}

async function fetchRail(signal?: AbortSignal): Promise<SubtitleRail | null> {
  try {
    const res = await fetch(RAIL_URL, { signal });
    if (!res.ok) return null;
    const data: unknown = await res.json();
    return isRail(data) ? data : null;
  } catch {
    return null;
  }
}

export interface SubtitleOverlayController {
  stop(): void;
}

/**
 * Mount the overlay on #subtitle-overlay and drive it from rail polling +
 * hls.js FRAG_CHANGED/timeupdate events.
 */
export function initSubtitleOverlay(
  video: HTMLVideoElement,
  hls: HlsLike,
): SubtitleOverlayController {
  let container = document.getElementById(SUBTITLE_OVERLAY_ID);
  if (!container) {
    container = document.createElement("div");
    container.id = SUBTITLE_OVERLAY_ID;
    document.getElementById("video-container")?.appendChild(container);
  }

  let rail: SubtitleRail | null = null;
  let curIdx: number | null = null;
  let curFragStart = 0;

  const render = (): void => {
    if (!container) return;
    const tRel = video.currentTime - curFragStart;
    const active = pickActiveSegments(rail?.chunks ?? [], curIdx, tRel);
    const text = active.map((s) => s.text).join(" ");
    if (container.textContent !== text) {
      container.textContent = text;
      container.style.display = text ? "" : "none";
    }
  };

  const onFragChanged = (...args: unknown[]): void => {
    // hls.js llama on(eventName, data) — el payload puede venir en args[1] o args[0]
    const data =
      (args[1] as FragChangedData | undefined) ??
      (args[0] as FragChangedData | undefined);
    const url = data?.frag?.url ?? "";
    const idx = parseSegIndex(url);
    if (idx !== null) curIdx = idx;
    if (typeof data?.frag?.start === "number") curFragStart = data.frag.start;
    render();
  };

  const pollTimer = setInterval(() => {
    void fetchRail().then((r) => {
      if (r) rail = r;
      render();
    });
  }, POLL_INTERVAL_MS);

  hls.on("hlsFragChanged", onFragChanged);
  video.addEventListener("timeupdate", render);
  // rAF cubre los huecos entre timeupdate (~250ms) para bordes de cue nítidos
  const rafId = requestAnimationFrame(function loop() {
    render();
    requestAnimationFrame(loop);
  });

  logger.info("player", "Subtitle overlay renderer active (rail mode)");

  return {
    stop(): void {
      clearInterval(pollTimer);
      cancelAnimationFrame(rafId);
      hls.off("hlsFragChanged", onFragChanged);
      video.removeEventListener("timeupdate", render);
      if (container) container.textContent = "";
    },
  };
}
