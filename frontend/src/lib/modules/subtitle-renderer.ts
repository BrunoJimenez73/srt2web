interface CueData {
  globalStart: number;
  globalEnd: number;
  text: string;
}

/**
 * SubtitleRenderer: polls /subtitles/subs.m3u8 for per-chunk VTT fragments
 * and renders cue text positioned over the video element.
 *
 * Sync strategy: instead of independently computing an absolute timeline
 * (which drifts from the video's actual currentTime when segment durations
 * vary), we measure the offset between the subtitle timeline and
 * video.currentTime on each poll cycle. This keeps subtitles locked to the
 * video even when EXTINF values diverge from actual playback time.
 */
export class SubtitleRenderer {
  private video: HTMLVideoElement | null = null;
  private containerEl: HTMLElement | null = null;
  private cueEl: HTMLElement | null = null;
  private cues: CueData[] = [];
  private knownSegments: Set<string> = new Set();
  private subsBaseUrl = `${window.location.origin}/subtitles/`;
  private pollTimer: number | null = null;
  private targetDuration = 10;
  private mediaSequence = 0;
  private enabled = true;
  private destroyed = false;
  private lastActiveText: string | null = null;
  /** Accumulated duration from EXTINF entries (for new segments only) */
  private accumulatedTime = 0;
  /** Offset between subtitle timeline and video.currentTime */
  private timeOffset = 0;
  /** Whether we've calibrated the offset from video.currentTime */
  private offsetCalibrated = false;

  start(video: HTMLVideoElement, container: HTMLElement): void {
    this.video = video;
    this.containerEl = container;
    this.destroyed = false;
    this.createCueElement();
    this.video.addEventListener("timeupdate", this.onTimeUpdate);
    this.video.addEventListener("seeking", this.onTimeUpdate);
    this.schedulePoll();
  }

  stop(): void {
    this.destroyed = true;
    if (this.pollTimer !== null) {
      window.clearTimeout(this.pollTimer);
      this.pollTimer = null;
    }
    if (this.video) {
      this.video.removeEventListener("timeupdate", this.onTimeUpdate);
      this.video.removeEventListener("seeking", this.onTimeUpdate);
    }
    this.removeCueElement();
    this.cues = [];
    this.knownSegments.clear();
    this.video = null;
    this.containerEl = null;
  }

  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    if (!enabled) this.hideCue();
  }

  private createCueElement(): void {
    if (!this.containerEl) return;
    this.cueEl = document.createElement("div");
    this.cueEl.id = "subtitle-renderer-cue";
    Object.assign(this.cueEl.style, {
      position: "absolute",
      bottom: "52px",
      left: "50%",
      transform: "translateX(-50%)",
      color: "#fff",
      backgroundColor: "rgba(0,0,0,0.82)",
      padding: "6px 14px",
      borderRadius: "4px",
      fontSize: "1.2em",
      fontFamily: "'Inter', system-ui, sans-serif",
      fontWeight: "500",
      textAlign: "center",
      whiteSpace: "pre-wrap",
      pointerEvents: "none",
      zIndex: "10",
      maxWidth: "80%",
      display: "none",
      lineHeight: "1.4",
    });
    this.containerEl.appendChild(this.cueEl);
  }

  private removeCueElement(): void {
    if (this.cueEl && this.cueEl.parentNode) {
      this.cueEl.parentNode.removeChild(this.cueEl);
    }
    this.cueEl = null;
  }

  private schedulePoll(): void {
    if (this.destroyed) return;
    this.pollTimer = window.setTimeout(() => {
      void this.pollPlaylist();
    }, 2500);
  }

  private async pollPlaylist(): Promise<void> {
    if (this.destroyed) return;
    try {
      const res = await fetch(`${this.subsBaseUrl}subs.m3u8`, {
        cache: "no-cache",
      });
      if (res.ok) {
        const text = await res.text();
        this.parsePlaylist(text);
      }
    } catch {
      // server not running — try again later
    }
    this.schedulePoll();
  }

  private parsePlaylist(text: string): void {
    const lines = text.split("\n");
    let targetDuration = this.targetDuration;
    let mediaSequence = this.mediaSequence;
    const durations: number[] = [];

    for (const line of lines) {
      const t = line.trim();
      if (t.startsWith("#EXT-X-TARGETDURATION:")) {
        const v = parseInt(t.split(":")[1], 10);
        if (!isNaN(v) && v > 0) targetDuration = v;
      } else if (t.startsWith("#EXT-X-MEDIA-SEQUENCE:")) {
        const v = parseInt(t.split(":")[1], 10);
        if (!isNaN(v)) mediaSequence = v;
      } else if (t.startsWith("#EXTINF:")) {
        const durStr = t.split(":")[1].split(",")[0];
        const dur = parseFloat(durStr);
        durations.push(isNaN(dur) ? targetDuration : dur);
      }
    }

    // Parse segment filenames in order
    const segmentFilenames = lines
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith("#"));

    this.targetDuration = targetDuration;
    this.mediaSequence = mediaSequence;

    // Bootstrap: on first parse with mediaSequence > 0, estimate accumulatedTime
    // by summing EXTINF durations from the current playlist window. For segments
    // before the window (mediaSequence..first segment in playlist), use the
    // average EXTINF from the current window as a best estimate.
    if (
      this.accumulatedTime === 0 &&
      mediaSequence >= 0 &&
      durations.length > 0
    ) {
      const avgExtinf = durations.reduce((a, b) => a + b, 0) / durations.length;
      // Estimate: segments before window used avgExtinf, segments in window use actual
      this.accumulatedTime = mediaSequence * avgExtinf;
    }

    for (let i = 0; i < segmentFilenames.length; i++) {
      const name = segmentFilenames[i];
      const actualDuration =
        i < durations.length ? durations[i] : targetDuration;
      const isNew = !this.knownSegments.has(name);

      if (isNew) {
        this.knownSegments.add(name);
        const seqNum = mediaSequence + i;
        const startTime = this.accumulatedTime;
        this.loadSegment(name, seqNum, startTime);
        this.accumulatedTime += actualDuration;
      }
    }

    // Calibrate offset: compare subtitle timeline to video.currentTime
    this.calibrateOffset();

    if (this.knownSegments.size > 60) {
      const sorted = Array.from(this.knownSegments).sort();
      const toRemove = sorted.slice(0, sorted.length - 60);
      for (const s of toRemove) this.knownSegments.delete(s);
    }
    if (this.cues.length > 600) {
      this.cues = this.cues.slice(this.cues.length - 600);
    }
  }

  /**
   * Measure the offset between subtitle time and video.currentTime.
   * Find the subtitle cue that should be active NOW based on the video's
   * current position, and compute the offset needed to align them.
   */
  private calibrateOffset(): void {
    if (!this.video || this.cues.length === 0) return;
    const vt = this.video.currentTime;
    // Find the cue whose time range contains (or is closest to) video.currentTime
    for (const cue of this.cues) {
      if (cue.globalStart <= vt && cue.globalEnd > vt) {
        // This cue should be active — offset = video.currentTime - cue.globalStart
        // But we want subtitles to match the video's timeline, so we set
        // timeOffset = vt - cue.globalStart and apply it during matching
        this.timeOffset = vt - cue.globalStart;
        this.offsetCalibrated = true;
        return;
      }
    }
    // No active cue found — try to find the closest past cue
    let closestCue: CueData | null = null;
    for (const cue of this.cues) {
      if (cue.globalStart <= vt) {
        closestCue = cue;
      } else {
        break;
      }
    }
    if (closestCue) {
      this.timeOffset = vt - closestCue.globalStart;
      this.offsetCalibrated = true;
    }
  }

  private async loadSegment(
    filename: string,
    _seqNum: number,
    segmentStartTime: number,
  ): Promise<void> {
    if (this.destroyed) return;
    try {
      const res = await fetch(`${this.subsBaseUrl}${filename}`, {
        cache: "no-cache",
      });
      if (res.ok) {
        const vtt = await res.text();
        const parsed = this.parseVTT(vtt, segmentStartTime);
        if (parsed.length > 0) {
          this.cues.push(...parsed);
        }
      }
    } catch {
      // Don't advance accumulatedTime — it was already advanced in parsePlaylist.
      // On next poll, this segment won't be "new" anymore (it's in knownSegments)
      // so it won't be re-fetched. If the segment truly failed, the cue data is
      // lost, but the timeline stays correct for subsequent segments.
    }
  }

  private parseVTT(vtt: string, segmentStartTime: number): CueData[] {
    const result: CueData[] = [];
    const lines = vtt.split("\n");
    let currentStart = 0;
    let currentEnd = 0;
    let textParts: string[] = [];
    let inCue = false;

    for (const line of lines) {
      const t = line.trim();
      if (t === "WEBVTT" || t === "") continue;

      const m = t.match(
        /^(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})$/,
      );
      if (m) {
        const start = this.ts(m, 1);
        const end = this.ts(m, 5);
        if (inCue && textParts.length > 0) {
          result.push({
            globalStart: segmentStartTime + currentStart,
            globalEnd: segmentStartTime + currentEnd,
            text: textParts.join(" "),
          });
        }
        currentStart = start;
        currentEnd = end;
        textParts = [];
        inCue = true;
      } else if (inCue && !/^\d+$/.test(t)) {
        textParts.push(t);
      }
    }

    if (inCue && textParts.length > 0) {
      result.push({
        globalStart: segmentStartTime + currentStart,
        globalEnd: segmentStartTime + currentEnd,
        text: textParts.join(" "),
      });
    }

    return result;
  }

  private ts(m: RegExpMatchArray, o: number): number {
    const h = parseInt(m[o], 10);
    const mn = parseInt(m[o + 1], 10);
    const s = parseInt(m[o + 2], 10);
    const ms = parseInt(m[o + 3], 10);
    return h * 3600 + mn * 60 + s + ms / 1000;
  }

  private onTimeUpdate = (): void => {
    if (!this.enabled || !this.video || this.destroyed) {
      this.hideCue();
      return;
    }
    const t = this.video.currentTime;
    let found: string | null = null;
    for (const cue of this.cues) {
      // Apply offset to align subtitle time with video time
      const adjStart = cue.globalStart + this.timeOffset;
      const adjEnd = cue.globalEnd + this.timeOffset;
      if (t >= adjStart && t < adjEnd) {
        found = cue.text;
        break;
      }
      if (adjStart > t) break;
    }
    if (found !== this.lastActiveText) {
      this.lastActiveText = found;
      this.renderCue(found);
    }
  };

  private renderCue(text: string | null): void {
    if (!this.cueEl) return;
    if (text) {
      this.cueEl.textContent = text;
      this.cueEl.style.display = "block";
    } else {
      this.cueEl.style.display = "none";
    }
  }

  private hideCue(): void {
    if (this.cueEl) this.cueEl.style.display = "none";
  }
}
