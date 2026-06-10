interface CueData {
  globalStart: number;
  globalEnd: number;
  text: string;
}

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
  /** Tracks whether we've seen the first playlist parse to bootstrap accumulatedTime */
  private firstParse = true;
  private enabled = true;
  private destroyed = false;
  private lastActiveText: string | null = null;
  /** Accumulated actual duration from EXTINF entries for accurate global offset */
  private accumulatedTime = 0;

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

    // Bootstrap accumulatedTime on first load: if the playlist starts mid-stream
    // (mediaSequence > 0), estimate the initial offset so cues aren't shifted
    // by minutes. Subsequent parses only add actual EXTINF durations for NEW
    // segments, keeping the timeline in sync with the video.
    if (this.firstParse && mediaSequence > 0 && this.accumulatedTime === 0) {
      this.accumulatedTime = mediaSequence * targetDuration;
    }
    this.firstParse = false;

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
        // Only advance accumulatedTime for new segments to prevent
        // unbounded growth on repeated polls of the same playlist window
        this.accumulatedTime += actualDuration;
      }
    }

    if (this.knownSegments.size > 60) {
      const sorted = Array.from(this.knownSegments).sort();
      const toRemove = sorted.slice(0, sorted.length - 60);
      for (const s of toRemove) this.knownSegments.delete(s);
    }
    if (this.cues.length > 600) {
      this.cues = this.cues.slice(this.cues.length - 600);
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
      // ignore
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
      if (t >= cue.globalStart && t < cue.globalEnd) {
        found = cue.text;
        break;
      }
      if (cue.globalStart > t) break;
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
