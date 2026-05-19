import { j as b } from "./vendor-signals.DQU3zyvD.js";
import {
  g as x,
  C as I,
  v as h,
} from "./InputCard.astro_astro_type_script_index_0_lang.DFbizcxd.js";
function a(u) {
  return document.getElementById(u);
}
b(() => {
  const p = x.value?.modules ?? [],
    i = I.value,
    c = h.value,
    m = Object.fromEntries(p.map((t) => [t.name, t])),
    _ = [
      {
        name: "input",
        indicator: "indicator-input",
        status: "status-input",
        badge: "gpu-badge-input",
        timeId: "module-time-input",
        chunksId: "module-chunks-input",
        encoderId: "module-encoder-input",
      },
      {
        name: "audio_extractor",
        indicator: "indicator-audio-extractor",
        status: "status-audio_extractor",
        badge: "gpu-badge-audio_extractor",
        timeId: "module-time-audio_extractor",
        chunksId: "module-chunks-audio_extractor",
        encoderId: "module-encoder-audio_extractor",
      },
      {
        name: "transcriber",
        indicator: "indicator-whisper",
        status: "status-transcriber",
        badge: "gpu-badge-transcriber",
        timeId: "module-time-transcriber",
        chunksId: "module-chunks-transcriber",
        encoderId: "module-encoder-transcriber",
      },
      {
        name: "translator",
        indicator: "indicator-translate",
        status: "status-translator",
        badge: "gpu-badge-translator",
        timeId: "module-time-translator",
        chunksId: "module-chunks-translator",
        encoderId: "module-encoder-translator",
      },
      {
        name: "tts_engine",
        indicator: "indicator-tts",
        status: "status-tts_engine",
        badge: "gpu-badge-tts_engine",
        timeId: "module-time-tts_engine",
        chunksId: "module-chunks-tts_engine",
        encoderId: "module-encoder-tts_engine",
      },
      {
        name: "subtitle_generator",
        indicator: "indicator-subtitle",
        status: "status-subtitle_generator",
        badge: "gpu-badge-subtitle_generator",
        timeId: "module-time-subtitle_generator",
        chunksId: "module-chunks-subtitle_generator",
        encoderId: "module-encoder-subtitle_generator",
      },
      {
        name: "audio_mixer",
        indicator: "indicator-audio-mixer",
        status: "status-audio_mixer",
        badge: "gpu-badge-audio_mixer",
        timeId: "module-time-audio_mixer",
        chunksId: "module-chunks-audio_mixer",
        encoderId: "module-encoder-audio_mixer",
      },
      {
        name: "video_muxer",
        indicator: "indicator-video-muxer",
        status: "status-video_muxer",
        badge: "gpu-badge-video_muxer",
        timeId: "module-time-video_muxer",
        chunksId: "module-chunks-video_muxer",
        encoderId: "module-encoder-video_muxer",
      },
      {
        name: "output",
        indicator: "indicator-output",
        status: "status-output",
        badge: "gpu-badge-output",
        timeId: "module-time-output",
        chunksId: "module-chunks-output",
        encoderId: "module-encoder-output",
      },
    ];
  for (const t of _) {
    const e = m[t.name] ?? m[t.name.replace("_", "_")],
      r = a(t.indicator);
    if (r) {
      const s = i && e?.enabled;
      r.classList.toggle("active", s && e?.state !== "degraded"),
        r.classList.toggle("degraded", e?.state === "degraded");
    }
    const d = a(t.status);
    d &&
      e &&
      ((d.className = "status-dot"),
      d.classList.toggle("running", e.state === "running"),
      d.classList.toggle("error", e.state === "error"),
      d.classList.toggle("degraded", e.state === "degraded"),
      d.classList.toggle("disabled", !e.enabled));
    const n = a(t.badge);
    if (n && e?.extra) {
      const s = i && e.enabled && (e.processed_chunks ?? 0) > 0;
      e.extra.using_gpu
        ? ((n.textContent = e.extra.device === "mps" ? "MPS" : "GPU"),
          (n.style.display = "inline"),
          n.classList.toggle("active", s))
        : ((n.textContent = "CPU"),
          (n.style.display = "inline"),
          n.classList.remove("active"));
    }
    const o = a(t.timeId);
    if (o && e)
      if (e.last_process_time_ms > 0) {
        const s = e.last_process_time_ms;
        o.textContent =
          s < 1e3 ? `${Math.round(s)}ms` : `${(s / 1e3).toFixed(1)}s`;
      } else
        i && c > 0
          ? (o.textContent = `${(1e3 / c).toFixed(0)}ms`)
          : e.state === "error"
            ? ((o.textContent = "ERROR"), (o.style.color = "var(--error)"))
            : (o.textContent = e.enabled ? "--" : "OFF");
    const l = a(t.chunksId);
    l && e && (l.textContent = String(e.processed_chunks ?? 0));
    const g = a(t.encoderId);
    if (g && e?.extra) {
      const s =
        e.extra.device === "mps" ? "MPS" : e.extra.using_gpu ? "GPU" : "CPU";
      g.textContent = e.extra.encoder_label || s;
    }
  }
});
