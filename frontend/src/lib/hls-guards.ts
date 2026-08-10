/**
 * F180 — Type guards for hls.js event payloads.
 *
 * hls.js callbacks deliver event data as `unknown`. Instead of casting
 * (`data as HlsErrorData`), the player routes payloads through these
 * guards so a malformed shape degrades gracefully instead of crashing.
 */

export interface HlsErrorData {
  type: string;
  fatal: boolean;
  details: string;
}

export interface HlsLevelUpdatedData {
  level: number;
  details?: {
    bitrate?: number;
    totalduration?: number;
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isHlsErrorData(data: unknown): data is HlsErrorData {
  if (!isRecord(data)) return false;
  const { type, fatal, details } = data;
  return (
    typeof type === "string" &&
    typeof fatal === "boolean" &&
    (typeof details === "string" || details === undefined)
  );
}

export function isHlsLevelUpdatedData(
  data: unknown,
): data is HlsLevelUpdatedData {
  if (!isRecord(data)) return false;
  if (typeof data.level !== "number") return false;
  if (data.details === undefined) return true;
  if (!isRecord(data.details)) return false;
  const { bitrate, totalduration } = data.details;
  return (
    (bitrate === undefined || typeof bitrate === "number") &&
    (totalduration === undefined || typeof totalduration === "number")
  );
}
