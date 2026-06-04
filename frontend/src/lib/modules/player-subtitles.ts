/**
 * F108 — HLS.js native subtitle track management.
 *
 * Replaces the old polling + wipe-and-replace VTT loader (see
 * `frontend/src/lib/modules/player.ts` history) with a small helper that
 * activates the first subtitle track declared in the master playlist.
 *
 * Why this exists:
 *
 *   The previous implementation did:
 *     setInterval(() => fetch("/subtitles/subs.vtt").then(parseVTT)
 *                       .then(wipe-and-replace ALL cues), 2000)
 *
 *   That produced a 0-2s oscillation (user-visible desync), flicker every
 *   2s when the active cue was wiped and re-added, and unbounded memory
 *   growth as the rolling window accumulated up to 2000 cues.
 *
 *   With this helper, HLS.js loads the subtitle media playlist
 *   (subs.m3u8) natively, parses per-chunk fragments with media-relative
 *   timestamps, and adds cues to a <track> element attached to the
 *   <video>. The browser renders each cue at the correct currentTime in
 *   the SAME time-base as the video — no polling, no lag, no flicker.
 *
 * Public API:
 *   - activateFirstSubtitleTrack(hls, options?)
 *       Call after MANIFEST_PARSED. If subtitle tracks are declared in
 *       the master playlist, enables the first one (or the one matching
 *       `options.preferredLang`).
 *
 *   - getActiveSubtitleTrackId(hls)
 *       Returns the currently active track id, or -1 if none.
 *
 *   - disableSubtitles(hls)
 *       Turn off all subtitle tracks (e.g. on disconnect).
 *
 *   - onSubtitleTrackListChange(hls, callback)
 *       Subscribe to SUBTITLE_TRACKS_UPDATED events so the UI can show
 *       track selection controls. Returns an unsubscribe function.
 */

import { logger } from "../utils/logger";

// Subset of the hls.js API we touch. Kept narrow on purpose so this
// helper can be unit-tested with a hand-rolled mock.
export interface HlsLike {
  subtitleTrack: number;
  subtitleDisplay: boolean;
  subtitleTracks: ReadonlyArray<SubtitleTrackDescriptor>;
  allSubtitleTracks?: ReadonlyArray<SubtitleTrackDescriptor>;
  on(event: string, callback: (...args: unknown[]) => void): void;
  off?(event: string, callback: (...args: unknown[]) => void): void;
}

export interface SubtitleTrackDescriptor {
  id: number;
  name?: string;
  lang?: string;
  /**
   * The hls.js MediaPlaylist type field. We use it to filter out
   * closed-caption tracks (which require a different parser path).
   */
  type?: string;
}

export interface ActivateOptions {
  /**
   * If provided, prefer a track whose `lang` matches (case-insensitive).
   * Falls back to the first available track if no match.
   */
  preferredLang?: string;
  /**
   * If true, force-enable subtitleDisplay when activating a track.
   * Defaults to true.
   */
  showSubtitles?: boolean;
}

const HLS_EVENT_SUBTITLE_TRACKS_UPDATED = "hlsSubtitleTracksUpdated";

/**
 * Activate the first subtitle track declared in the master playlist.
 *
 * Returns the id of the track that was activated, or -1 if there are
 * no subtitle tracks in the manifest.
 *
 * Safe to call multiple times — re-activation just re-selects the same
 * track id and is a no-op for the user.
 */
export function activateFirstSubtitleTrack(
  hls: HlsLike,
  options: ActivateOptions = {},
): number {
  const { preferredLang, showSubtitles = true } = options;

  const tracks = collectUsableSubtitleTracks(hls);
  if (tracks.length === 0) {
    logger.debug("player-subtitles", "No subtitle tracks in manifest");
    return -1;
  }

  const chosen = pickPreferredTrack(tracks, preferredLang);
  if (chosen === null) {
    return -1;
  }

  hls.subtitleDisplay = showSubtitles;
  hls.subtitleTrack = chosen.id;
  logger.info(
    "player-subtitles",
    `Activated subtitle track id=${chosen.id}`,
    chosen.lang ?? "(no lang)",
    chosen.name ?? "(no name)",
  );
  return chosen.id;
}

/**
 * Get the currently active subtitle track id, or -1 if none.
 */
export function getActiveSubtitleTrackId(hls: HlsLike): number {
  return hls.subtitleTrack;
}

/**
 * Disable all subtitle tracks. Safe to call even if none are active.
 */
export function disableSubtitles(hls: HlsLike): void {
  hls.subtitleTrack = -1;
  hls.subtitleDisplay = false;
  logger.debug("player-subtitles", "Subtitles disabled");
}

/**
 * Subscribe to SUBTITLE_TRACKS_UPDATED events. Returns an unsubscribe
 * function. The callback receives the latest track list.
 *
 * Use this to repopulate UI track-selection controls when the master
 * playlist is re-parsed (e.g. after reconnect).
 */
export function onSubtitleTrackListChange(
  hls: HlsLike,
  callback: (tracks: ReadonlyArray<SubtitleTrackDescriptor>) => void,
): () => void {
  const handler = (..._args: unknown[]) => {
    callback(collectUsableSubtitleTracks(hls));
  };
  hls.on(HLS_EVENT_SUBTITLE_TRACKS_UPDATED, handler);
  return () => {
    if (typeof hls.off === "function") {
      hls.off(HLS_EVENT_SUBTITLE_TRACKS_UPDATED, handler);
    }
  };
}

/**
 * Filter out closed-caption tracks (handled by a different code path in
 * hls.js) and return only WebVTT subtitle tracks. Falls back to
 * `subtitleTracks` if `allSubtitleTracks` isn't populated.
 */
function collectUsableSubtitleTracks(hls: HlsLike): SubtitleTrackDescriptor[] {
  const source = hls.allSubtitleTracks ?? hls.subtitleTracks;
  if (!Array.isArray(source)) {
    return [];
  }
  return source.filter((t) => {
    if (!t) return false;
    if (t.type && t.type !== "SUBTITLES") return false;
    return true;
  });
}

/**
 * Pick the track that best matches the user's preference. Returns null
 * if no tracks are available.
 */
function pickPreferredTrack(
  tracks: ReadonlyArray<SubtitleTrackDescriptor>,
  preferredLang: string | undefined,
): SubtitleTrackDescriptor | null {
  if (tracks.length === 0) return null;
  if (!preferredLang) return tracks[0] ?? null;

  const target = preferredLang.toLowerCase();
  const exact = tracks.find((t) => (t.lang ?? "").toLowerCase() === target);
  if (exact) return exact;

  const prefix = tracks.find((t) =>
    (t.lang ?? "").toLowerCase().startsWith(target),
  );
  return prefix ?? tracks[0] ?? null;
}
