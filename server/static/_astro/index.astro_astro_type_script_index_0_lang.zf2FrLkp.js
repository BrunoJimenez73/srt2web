const __vite__mapDeps = (
  i,
  m = __vite__mapDeps,
  d = m.f ||
    (m.f = [
      "_astro/keyboard-shortcuts.mHPwB8P3.js",
      "_astro/index.BpSbb1Lw.js",
    ]),
) => i.map((i) => d[i]);
import {
  j as B,
  p as N,
  a as te,
  s as Ae,
  t as ne,
  c as Fe,
  w as oe,
  b as $e,
  d as Ge,
  e as Y,
  f as De,
  g as y,
  u as M,
  r as Ve,
  i as lt,
  m as rt,
} from "./store.YvzDn7sh.js";
import {
  D as E,
  a as O,
  u as at,
  b as We,
  M as h,
  c as ct,
  W as dt,
  I as ie,
  d as mt,
  e as je,
  f as pt,
} from "./api.CwWA6hCN.js";
import { s as I, c as J } from "./index.BpSbb1Lw.js";
import { a as gt, i as yt, f as Re } from "./logpanel.Dz867OYr.js";
const vt = (function () {
    const t = typeof document < "u" && document.createElement("link").relList;
    return t && t.supports && t.supports("modulepreload")
      ? "modulepreload"
      : "preload";
  })(),
  ft = function (e) {
    return "/" + e;
  },
  Ue = {},
  ze = function (t, n, o) {
    let i = Promise.resolve();
    if (n && n.length > 0) {
      let a = function (c) {
        return Promise.all(
          c.map((_) =>
            Promise.resolve(_).then(
              (p) => ({ status: "fulfilled", value: p }),
              (p) => ({ status: "rejected", reason: p }),
            ),
          ),
        );
      };
      document.getElementsByTagName("link");
      const r = document.querySelector("meta[property=csp-nonce]"),
        d = r?.nonce || r?.getAttribute("nonce");
      i = a(
        n.map((c) => {
          if (((c = ft(c)), c in Ue)) return;
          Ue[c] = !0;
          const _ = c.endsWith(".css"),
            p = _ ? '[rel="stylesheet"]' : "";
          if (document.querySelector(`link[href="${c}"]${p}`)) return;
          const v = document.createElement("link");
          if (
            ((v.rel = _ ? "stylesheet" : vt),
            _ || (v.as = "script"),
            (v.crossOrigin = ""),
            (v.href = c),
            d && v.setAttribute("nonce", d),
            document.head.appendChild(v),
            _)
          )
            return new Promise((g, C) => {
              v.addEventListener("load", g),
                v.addEventListener("error", () =>
                  C(new Error(`Unable to preload CSS for ${c}`)),
                );
            });
        }),
      );
    }
    function u(r) {
      const d = new Event("vite:preloadError", { cancelable: !0 });
      if (((d.payload = r), window.dispatchEvent(d), !d.defaultPrevented))
        throw r;
    }
    return i.then((r) => {
      for (const d of r || []) d.status === "rejected" && u(d.reason);
      return t().catch(u);
    });
  };
let Ne = !1;
function Et() {
  Ne ||
    ((Ne = !0),
    Me(),
    setInterval(() => {
      Me();
    }, 1e3));
}
function Me() {
  const e = document.getElementById("live-clock");
  e && (e.textContent = new Date().toLocaleTimeString("en-US", { hour12: !1 }));
}
var U = ((e) => (
  (e.STOPPED = "stopped"),
  (e.RUNNING = "running"),
  (e.STARTING = "starting"),
  (e.STOPPING = "stopping"),
  (e.ERROR = "error"),
  e
))(U || {});
function _t(e) {
  switch (e) {
    case "running":
      return "running";
    case "starting":
      return "starting";
    case "stopping":
      return "stopping";
    case "error":
      return "error";
    default:
      return "stopped";
  }
}
function s(e) {
  return document.getElementById(e);
}
function It() {
  B(() => {
    const e = N.value,
      t = s("status-dot"),
      n = s("status-text");
    if (!t || !n) return;
    const o = _t(e?.state);
    t.classList.toggle("running", o === U.RUNNING),
      t.classList.toggle("error", o === U.ERROR),
      (n.textContent = o === U.RUNNING ? "ACTIVO" : "APAGADO");
    const i = s("btn-start"),
      u = s("btn-stop");
    if (i) {
      const r = o === U.RUNNING;
      (i.disabled = r), (i.style.opacity = r ? "0.5" : "1");
    }
    if (u) {
      const r = o === U.RUNNING;
      (u.disabled = !r), (u.style.opacity = r ? "1" : "0.5");
    }
  }),
    B(() => {
      const t = N.value?.modules ?? [],
        n = te.value,
        o = {
          srt_input: "indicator-input",
          rtmp_input: "indicator-input",
          file_input: "indicator-input",
          audio_extractor: "indicator-audio-extractor",
          transcriber: "indicator-whisper",
          translator: "indicator-translate",
          tts_engine: "indicator-tts",
          subtitle_generator: "indicator-subtitle",
          audio_mixer: "indicator-audio-mixer",
          video_muxer: "indicator-video-muxer",
          output: "indicator-video-muxer",
          webplayer_output: "indicator-output",
          srt_output: "indicator-output",
          rtmp_output: "indicator-output",
          file_output: "indicator-output",
        };
      for (const r of t) {
        const d = o[r.name];
        if (!d) continue;
        const a = s(d);
        a && a.classList.toggle("active", n && r.enabled);
      }
      const i = s("indicator-output"),
        u = t.find((r) => r.name === "output");
      i && u && i.classList.toggle("active", n && u.enabled);
    }),
    B(() => {
      const e = N.value,
        t = s("pipeline-indicator");
      t && t.classList.toggle("active", e?.state === "running");
    });
}
function q(e) {
  return e < 40 ? "low" : e < 80 ? "medium" : "high";
}
function ht(e) {
  return e < 80 ? "warning" : "critical";
}
function bt() {
  B(() => {
    const e = Ae.value,
      t = ne.value,
      n = s("metric-cpu"),
      o = s("metric-cpu-bar"),
      i = s("metric-cpu-value");
    o &&
      ((o.style.width = `${e.cpu}%`),
      o.classList.remove("low", "medium", "high"),
      o.classList.add(q(e.cpu))),
      n &&
        (n.classList.remove("warning", "critical"), n.classList.add(ht(e.cpu))),
      i && (i.textContent = `${e.cpu.toFixed(0)}%`),
      console.log("[Metrics] CPU:", e.cpu, "Bar class:", q(e.cpu));
    const u = s("metric-memory-bar"),
      r = s("metric-memory-value"),
      d = s("metric-memory-percent");
    u &&
      ((u.style.width = `${e.memoryPercent}%`),
      u.classList.remove("low", "medium", "high"),
      u.classList.add(q(e.memoryPercent))),
      r && (r.textContent = `${e.memoryMb.toFixed(0)} MB`),
      d && (d.textContent = `${e.memoryPercent.toFixed(0)}%`);
    const a = s("metric-gpu-bar"),
      c = s("metric-gpu-value"),
      _ = s("metric-gpu-memory");
    a &&
      ((a.style.width = `${e.gpuUtil}%`),
      a.classList.remove("low", "medium", "high"),
      a.classList.add(q(e.gpuUtil))),
      c && (c.textContent = `${e.gpuUtil.toFixed(0)}%`),
      _ &&
        (_.textContent =
          e.gpuMemMb > 0 ? `${e.gpuMemMb.toFixed(0)} MB` : "N/A");
    const p = s("metric-throughput-bar"),
      v = s("metric-throughput-value");
    p && (p.style.width = `${Math.min(t * 10, 100)}%`),
      v && (v.textContent = `${t.toFixed(2)}/s`);
  });
}
function Bt() {
  B(() => {
    const t = N.value?.modules ?? [],
      n = te.value,
      o = ne.value,
      i = Object.fromEntries(t.map((l) => [l.name, l]));
    for (const l of [
      "audio_extractor",
      "transcriber",
      "translator",
      "tts_engine",
      "subtitle_generator",
      "audio_mixer",
    ]) {
      const m = i[l],
        L = s(`module-time-${l}`),
        j = s(`module-chunks-${l}`),
        z = s(`module-memory-${l}`),
        H = s(`module-encoder-${l}`);
      if (L)
        if (m?.last_process_time_ms !== void 0 && m.last_process_time_ms > 0) {
          const b = m.last_process_time_ms;
          L.textContent =
            b < 1e3 ? `${Math.round(b)}ms` : `${(b / 1e3).toFixed(1)}s`;
        } else if (n && o > 0) {
          const b = (1e3 / o).toFixed(0);
          L.textContent = `${b}ms`;
        } else L.textContent = "--";
      if (
        (j && (j.textContent = String(m?.processed_chunks ?? 0)),
        z &&
          (z.textContent =
            m?.memory_mb !== void 0 ? `${Math.round(m.memory_mb)} MB` : "--"),
        H && m?.extra)
      ) {
        const b = m.extra.encoder_label || (m.extra.using_gpu ? "GPU" : "CPU");
        H.textContent = b;
      }
      const R = s(`gpu-badge-${l}`);
      if (R && m?.extra) {
        const b = n && m.enabled && (m.processed_chunks ?? 0) > 0;
        m.extra.using_gpu
          ? ((R.style.display = "inline"), R.classList.toggle("active", b))
          : (R.style.display = "none");
      }
    }
    const u = i.audio_extractor,
      r = s("module-device-audio_extractor"),
      d = s("gpu-badge-audio_extractor");
    if (
      (r &&
        u?.extra &&
        (r.textContent = u.extra.device || (u.extra.using_gpu ? "GPU" : "CPU")),
      d && u?.extra)
    ) {
      const l = n && u.enabled && (u.processed_chunks ?? 0) > 0;
      u.extra.using_gpu
        ? ((d.style.display = "inline"), d.classList.toggle("active", l))
        : (d.style.display = "none");
    }
    const a = i.input ?? i.srt_input ?? i.rtmp_input ?? i.file_input,
      c = s("module-time-input"),
      _ = s("module-chunks-input"),
      p = s("gpu-badge-input"),
      v = s("module-encoder-input");
    if (c)
      if (a?.last_process_time_ms !== void 0 && a.last_process_time_ms > 0) {
        const l = a.last_process_time_ms;
        c.textContent =
          l < 1e3 ? `${Math.round(l)}ms` : `${(l / 1e3).toFixed(1)}s`;
      } else
        n && o > 0
          ? (c.textContent = `${(1e3 / o).toFixed(0)}ms`)
          : a?.enabled
            ? a?.state === "error"
              ? ((c.textContent = "ERROR"), (c.style.color = "var(--error)"))
              : (c.textContent = "IDLE")
            : (c.textContent = "--");
    if ((_ && a && (_.textContent = String(a.processed_chunks ?? 0)), p && a)) {
      const l = a.extra?.using_gpu === !0,
        m = n && (a.processed_chunks ?? 0) > 0;
      a.enabled && l
        ? ((p.style.display = "inline"),
          p.classList.toggle("active", m),
          (p.textContent = "GPU"))
        : (p.style.display = "none");
    }
    if (v && a) {
      const l = a.extra?.encoder_label || (a.extra?.using_gpu ? "GPU" : "CPU");
      v.textContent = l;
    }
    const g = i.video_muxer,
      C = s("module-time-video_muxer"),
      F = s("module-memory-video_muxer"),
      $ = s("module-chunks-video_muxer"),
      G = s("module-encoder-video_muxer"),
      x = s("gpu-badge-video_muxer");
    if (C)
      if (g?.last_process_time_ms !== void 0 && g.last_process_time_ms > 0) {
        const l = g.last_process_time_ms;
        C.textContent =
          l < 1e3 ? `${Math.round(l)}ms` : `${(l / 1e3).toFixed(1)}s`;
      } else
        n && o > 0
          ? (C.textContent = `${(1e3 / o).toFixed(0)}ms`)
          : (C.textContent = "--");
    if (
      (F &&
        g &&
        (F.textContent =
          g.memory_mb !== void 0 ? `${Math.round(g.memory_mb)} MB` : "--"),
      $ && g && ($.textContent = String(g.processed_chunks ?? 0)),
      G && g?.extra)
    ) {
      const l = g.extra.encoder_label || (g.extra.using_gpu ? "GPU" : "CPU");
      G.textContent = l;
    }
    if (x) {
      const l = n && g?.enabled && (g.processed_chunks ?? 0) > 0;
      g?.extra?.using_gpu ?? !1
        ? ((x.textContent = "GPU"),
          (x.style.display = "inline"),
          x.classList.toggle("active", l))
        : ((x.textContent = "CPU"),
          (x.style.display = "inline"),
          x.classList.remove("active"));
    }
    const f = i.output,
      w = s("module-time-output"),
      D = s("module-memory-output"),
      V = s("module-chunks-output"),
      W = s("module-encoder-output"),
      S = s("gpu-badge-output");
    if (w)
      if (f?.last_process_time_ms !== void 0 && f.last_process_time_ms > 0) {
        const l = f.last_process_time_ms;
        w.textContent =
          l < 1e3 ? `${Math.round(l)}ms` : `${(l / 1e3).toFixed(1)}s`;
      } else
        n && o > 0
          ? (w.textContent = `${(1e3 / o).toFixed(0)}ms`)
          : (w.textContent = "--");
    if (
      (D &&
        f &&
        (D.textContent =
          f.memory_mb !== void 0 ? `${Math.round(f.memory_mb)} MB` : "--"),
      V && f && (V.textContent = String(f.processed_chunks ?? 0)),
      W && f?.extra)
    ) {
      const l = f.extra.encoder_label || (f.extra.using_gpu ? "GPU" : "CPU");
      W.textContent = l;
    }
    if (S) {
      const l = n && f?.enabled && (f.processed_chunks ?? 0) > 0;
      f?.extra?.using_gpu ?? !1
        ? ((S.textContent = "GPU"),
          (S.style.display = "inline"),
          S.classList.toggle("active", l))
        : ((S.textContent = "CPU"),
          (S.style.display = "inline"),
          S.classList.remove("active"));
    }
  });
}
function xt() {
  B(() => {
    const e = Fe.value,
      t = s("url-emision-label"),
      n = s("url-emision"),
      o = s("url-stream"),
      i = s("url-player");
    t && (t.textContent = e.primaryLabel),
      n && (n.textContent = e.primaryUrl),
      o && (o.textContent = e.streamUrl),
      i && ((i.textContent = e.playerUrl), (i.href = e.playerUrl));
  });
}
function St() {
  B(() => {
    const e = oe.value,
      t = s("ws-status-badge");
    t &&
      ((t.textContent = e ? "WS ON" : "WS OFF"),
      t.classList.toggle("active", e));
  });
}
function Ct() {
  B(() => {
    N.value;
    const e = s("live-clock");
    e &&
      (e.textContent = new Date().toLocaleTimeString("en-US", { hour12: !1 }));
  }),
    Et();
}
function wt() {
  B(() => {
    const e = $e.value,
      t = s("remote-config"),
      n = s("btn-mode-local"),
      o = s("btn-mode-remote");
    t && (t.style.display = e === "remote" ? "" : "none"),
      n && n.classList.toggle("active", e === "local"),
      o && o.classList.toggle("active", e === "remote");
  });
}
function Lt() {
  B(() => {
    Ge.value, Y.value;
  });
}
let Oe = 0;
function kt() {
  B(() => {
    const e = De.value,
      t = e.slice(Oe);
    for (const n of t) gt(n.level, n.message, n.timestamp);
    Oe = e.length;
  });
}
function He() {
  It(), bt(), Bt(), xt(), St(), Ct(), wt(), Lt(), kt();
}
const Dt = Object.freeze(
  Object.defineProperty(
    {
      __proto__: null,
      addLog: y,
      connectionMode: $e,
      connectionUrls: Fe,
      inputType: lt,
      isPipelineRunning: te,
      moduleStates: rt,
      pipelineConfig: Y,
      pipelineLogs: De,
      pipelineStatus: N,
      resetThroughput: Ve,
      startEffects: He,
      systemMetrics: Ae,
      throughputAvg: ne,
      throughputHistory: Ge,
      updateStatus: M,
      wsConnected: oe,
    },
    Symbol.toStringTag,
    { value: "Module" },
  ),
);
function Ke() {
  const e = document.getElementById("input-type")?.value || "srt";
  document.getElementById("output-type")?.value;
  const t = parseInt(
      document.getElementById("input-chunk-duration")?.value ||
        document.getElementById("input-rtmp-chunk")?.value ||
        document.getElementById("input-file-chunk")?.value ||
        String(E.CHUNK_DURATION),
    ),
    n = { type: e };
  e === "srt"
    ? (n.srt = {
        listen_port: parseInt(
          document.getElementById("input-srt-port")?.value || "9000",
        ),
        mode: document.getElementById("input-srt-mode")?.value || "listener",
        latency_ms: parseInt(
          document.getElementById("input-srt-latency")?.value || "200",
        ),
        caller_address: "",
        chunk_duration_sec: t,
      })
    : e === "rtmp"
      ? (n.rtmp = {
          url:
            document.getElementById("input-rtmp-url")?.value ||
            "rtmp://localhost/live/stream",
          mode: document.getElementById("input-rtmp-mode")?.value || "pull",
          app: document.getElementById("input-rtmp-app")?.value || "live",
          listen_port: 1935,
          stream_key: "",
          chunk_duration_sec: t,
        })
      : e === "file" &&
        (n.file = {
          path: document.getElementById("input-file-path")?.value || "",
          loop: document.getElementById("input-file-loop")?.value === "true",
          speed: parseFloat(
            document.getElementById("input-file-speed")?.value ||
              String(E.TTS_SPEED),
          ),
          chunk_duration_sec: t,
        });
  const o = {
    audio_extractor: { enabled: !0 },
    transcriber: {
      enabled: document.getElementById("whisper-enabled")?.checked ?? !0,
      model: document.getElementById("whisper-model")?.value || E.WHISPER_MODEL,
      language:
        document.getElementById("whisper-lang")?.value || E.WHISPER_LANGUAGE,
      device: document.getElementById("whisper-device")?.value || "auto",
      beam_size: 2,
    },
    translator: {
      enabled: document.getElementById("translator-enabled")?.checked ?? !0,
      source_lang:
        document.getElementById("translator-source")?.value ||
        E.WHISPER_LANGUAGE,
      target_lang:
        document.getElementById("translator-target")?.value ||
        E.TRANSLATE_TARGET,
    },
    tts_engine: {
      enabled: document.getElementById("tts-enabled")?.checked ?? !0,
      engine: document.getElementById("tts-engine")?.value || "edge-tts",
      voice:
        document.getElementById("tts-engine")?.value === "piper"
          ? document.getElementById("tts-voice-piper")?.value ||
            "es_ES-sharvard-medium"
          : document.getElementById("tts-voice-edge")?.value ||
            "es-ES-ElviraNeural",
      speed: parseFloat(
        document.getElementById("tts-speed")?.value || String(E.TTS_SPEED),
      ),
      device: document.getElementById("tts-device")?.value || "auto",
    },
    subtitle_generator: {
      enabled: document.getElementById("subtitle-enabled")?.checked ?? !0,
      format:
        document.getElementById("subtitle-format")?.value || E.SUBTITLE_FORMAT,
      use_translated:
        document.getElementById("subtitle-use-translated")?.value === "true",
      chunk_duration: t,
    },
    audio_mixer: {
      enabled: document.getElementById("audio-mixer-enabled")?.checked ?? !1,
      original_volume: parseFloat(
        document.getElementById("audio-mixer-original-volume")?.value ||
          String(E.ORIGINAL_VOLUME),
      ),
      tts_volume: parseFloat(
        document.getElementById("audio-mixer-dubbed-volume")?.value ||
          String(E.TTS_VOLUME),
      ),
      dubbed_volume: parseFloat(
        document.getElementById("audio-mixer-dubbed-volume")?.value ||
          String(E.TTS_VOLUME),
      ),
    },
    video_muxer: {
      enabled: document.getElementById("muxer-enabled")?.checked ?? !0,
      engine: document.getElementById("video-muxer-engine")?.value || "hls",
      hls_segment_duration: parseInt(
        document.getElementById("hls-segment")?.value ||
          String(E.SEGMENT_DURATION),
      ),
      hls_list_size: parseInt(
        document.getElementById("hls-list")?.value || String(E.LIST_SIZE),
      ),
      audio_offset_ms: parseInt(
        document.getElementById("hls-audio-offset")?.value ||
          String(E.AUDIO_OFFSET),
      ),
      encoder_mode: document.getElementById("hls-encoder")?.value || "auto",
      video_quality: "medium",
      video_crf: parseInt(
        document.getElementById("hls-crf")?.value || String(E.CRF),
      ),
      audio_codec:
        (document.getElementById("video-muxer-engine")?.value === "webrtc"
          ? document.getElementById("webrtc-audio-codec")?.value
          : document.getElementById("hls-audio-codec")?.value) || "aac",
      audio_bitrate:
        document.getElementById("hls-audio-bitrate")?.value || "192k",
      audio_samplerate: "48000",
      video_codec: document.getElementById("webrtc-video-codec")?.value,
      video_bitrate: document.getElementById("webrtc-video-bitrate")?.value,
      video_fps: document.getElementById("webrtc-video-fps")
        ? parseInt(document.getElementById("webrtc-video-fps").value)
        : void 0,
      audio_sample_rate: document.getElementById("webrtc-audio-sample-rate")
        ? parseInt(document.getElementById("webrtc-audio-sample-rate").value)
        : void 0,
      ...(() => {
        const i = document.getElementById("webrtc-video-resolution");
        if (i?.value) {
          const [u, r] = i.value.split("x").map(Number);
          return { video_width: u, video_height: r };
        }
        return {};
      })(),
    },
  };
  return {
    input: n,
    pipeline: {
      chunk_duration_sec: t,
      mode: "sequential",
      max_concurrent_chunks: 2,
      buffer_size: 10,
      retry_attempts: 3,
      retry_delay: 1,
    },
    modules: o,
  };
}
function se(e) {
  const t = document.getElementById("input-type"),
    n = document.getElementById("output-type"),
    o = document.getElementById("whisper-enabled"),
    i = document.getElementById("whisper-model"),
    u = document.getElementById("whisper-lang"),
    r = document.getElementById("whisper-device"),
    d = document.getElementById("translator-enabled"),
    a = document.getElementById("translator-source"),
    c = document.getElementById("translator-target"),
    _ = document.getElementById("tts-enabled"),
    p = document.getElementById("tts-engine"),
    v = document.getElementById("tts-device"),
    g = document.getElementById("tts-device-group"),
    C = document.getElementById("tts-voice-edge"),
    F = document.getElementById("tts-voice-piper"),
    $ = document.getElementById("tts-voice-edge-group"),
    G = document.getElementById("tts-voice-piper-group"),
    x = document.getElementById("tts-speed"),
    f = document.getElementById("subtitle-enabled"),
    w = document.getElementById("subtitle-format"),
    D = document.getElementById("subtitle-use-translated"),
    V = document.getElementById("muxer-enabled"),
    W = document.getElementById("video-muxer-engine"),
    S = document.getElementById("hls-segment"),
    l = document.getElementById("hls-list"),
    m = document.getElementById("hls-encoder"),
    L = document.getElementById("hls-crf"),
    j = document.getElementById("hls-audio-offset"),
    z = document.getElementById("hls-audio-codec"),
    H = document.getElementById("hls-audio-bitrate"),
    R = e.input?.type || "srt";
  t && ((t.value = R), Pt());
  const b = document.getElementById("input-srt-port"),
    le = document.getElementById("input-srt-mode"),
    re = document.getElementById("input-srt-latency"),
    k = e.input?.srt;
  b && k?.listen_port && (b.value = String(k.listen_port)),
    le && k?.mode && (le.value = k.mode),
    re && k?.latency_ms && (re.value = String(k.latency_ms));
  const ae = document.getElementById("input-chunk-duration"),
    ce = document.getElementById("input-rtmp-chunk"),
    de = document.getElementById("input-file-chunk"),
    Z = e.pipeline?.chunk_duration_sec || E.CHUNK_DURATION;
  ae && (ae.value = String(k?.chunk_duration_sec || Z));
  const P = e.input?.rtmp,
    T = e.input?.file;
  ce && (ce.value = String(P?.chunk_duration_sec || Z));
  const me = document.getElementById("input-rtmp-url"),
    pe = document.getElementById("input-rtmp-mode"),
    ge = document.getElementById("input-rtmp-app");
  me && P?.url && (me.value = P.url),
    pe && P?.mode && (pe.value = P.mode),
    ge && P?.app && (ge.value = P.app);
  const ye = document.getElementById("input-file-path"),
    ve = document.getElementById("input-file-loop"),
    fe = document.getElementById("input-file-speed");
  ye && T?.path && (ye.value = T.path),
    ve && T?.loop !== void 0 && (ve.value = T.loop ? "true" : "false"),
    fe && T?.speed && (fe.value = String(T.speed)),
    de && (de.value = String(T?.chunk_duration_sec || Z));
  const ut =
    e.output?.type === "web" ? "webplayer" : e.output?.type || "webplayer";
  if (
    (n && ((n.value = ut), Tt()),
    o && (o.checked = e.modules.transcriber.enabled),
    i && (i.value = e.modules.transcriber.model),
    u && (u.value = e.modules.transcriber.language),
    r && (r.value = e.modules.transcriber.device),
    d && (d.checked = e.modules.translator.enabled),
    a && (a.value = e.modules.translator.source_lang),
    c && (c.value = e.modules.translator.target_lang),
    _ && (_.checked = e.modules.tts_engine.enabled),
    p &&
      ((p.value = e.modules.tts_engine.engine || "edge-tts"),
      g && (g.style.display = p.value === "piper" ? "block" : "none"),
      $ && G))
  ) {
    const Te = p.value === "edge-tts";
    ($.style.display = Te ? "block" : "none"),
      (G.style.display = Te ? "none" : "block");
  }
  v && (v.value = e.modules.tts_engine.device || "auto"),
    C && (C.value = e.modules.tts_engine.voice || "es-ES-AlvaroNeural"),
    F && (F.value = e.modules.tts_engine.voice || "es_ES-sharvard-medium"),
    x && (x.value = String(e.modules.tts_engine.speed)),
    f && (f.checked = e.modules.subtitle_generator.enabled),
    w && (w.value = e.modules.subtitle_generator.format),
    D && (D.value = String(e.modules.subtitle_generator.use_translated)),
    V && (V.checked = e.modules.video_muxer.enabled),
    W && (W.value = e.modules.video_muxer.engine || "hls");
  const Ee = document.getElementById("audio-mixer-enabled");
  Ee && (Ee.checked = e.modules.audio_mixer?.enabled ?? !1);
  const _e = document.getElementById("audio-mixer-original-volume");
  _e && (_e.value = String(e.modules.audio_mixer?.original_volume ?? 0.3));
  const Ie = document.getElementById("audio-mixer-original-value");
  Ie &&
    (Ie.textContent = String(e.modules.audio_mixer?.original_volume ?? 0.3));
  const he = document.getElementById("audio-mixer-dubbed-volume");
  he &&
    (he.value = String(
      e.modules.audio_mixer?.tts_volume ??
        e.modules.audio_mixer?.dubbed_volume ??
        1,
    ));
  const be = document.getElementById("audio-mixer-dubbed-value");
  be &&
    (be.textContent = String(
      e.modules.audio_mixer?.tts_volume ??
        e.modules.audio_mixer?.dubbed_volume ??
        1,
    )),
    S && (S.value = String(e.modules.video_muxer.hls_segment_duration)),
    l && (l.value = String(e.modules.video_muxer.hls_list_size)),
    m && (m.value = e.modules.video_muxer.encoder_mode),
    L && (L.value = String(e.modules.video_muxer.video_crf)),
    j && (j.value = String(e.modules.video_muxer.audio_offset_ms || 0)),
    z && (z.value = e.modules.video_muxer.audio_codec || "aac"),
    H && (H.value = e.modules.video_muxer.audio_bitrate || "192k");
  const Be = document.getElementById("webrtc-encoder"),
    xe = document.getElementById("webrtc-video-codec"),
    Se = document.getElementById("webrtc-video-bitrate"),
    Ce = document.getElementById("webrtc-video-resolution"),
    we = document.getElementById("webrtc-video-fps"),
    Le = document.getElementById("webrtc-audio-codec"),
    ke = document.getElementById("webrtc-audio-bitrate"),
    Pe = document.getElementById("webrtc-audio-sample-rate");
  Be && (Be.value = e.modules.video_muxer.encoder_mode || "auto"),
    xe && (xe.value = e.modules.video_muxer.video_codec || "h264"),
    Se && (Se.value = e.modules.video_muxer.video_bitrate || "1000k"),
    Ce &&
      e.modules.video_muxer.video_width &&
      e.modules.video_muxer.video_height &&
      (Ce.value = `${e.modules.video_muxer.video_width}x${e.modules.video_muxer.video_height}`),
    we &&
      e.modules.video_muxer.video_fps &&
      (we.value = String(e.modules.video_muxer.video_fps)),
    Le && (Le.value = e.modules.video_muxer.audio_codec || "opus"),
    ke &&
      (ke.value =
        e.modules.video_muxer.webrtc_audio_bitrate ||
        e.modules.video_muxer.audio_bitrate ||
        "64k"),
    Pe &&
      e.modules.video_muxer.audio_sample_rate &&
      (Pe.value = String(e.modules.video_muxer.audio_sample_rate));
}
function Pt() {
  const e = document.getElementById("input-type");
  e && (e.value = e.value);
}
function Tt() {
  const e = document.getElementById("output-type");
  e && (e.value = e.value);
}
let qe = !1;
function A(e, t = "") {
  (qe = e),
    document.body.classList.toggle("loading", e),
    e && t && y("INFO", `${t}...`);
}
function ue() {
  return qe;
}
async function Ye() {
  if (!ue()) {
    A(!0, "Iniciando pipeline");
    try {
      y("INFO", h.PIPELINE_STARTING), await mt();
      const e = await je();
      M(e), y("INFO", h.PIPELINE_STARTED);
    } catch (e) {
      y("ERROR", `Error: ${e.message}`);
    } finally {
      A(!1);
    }
  }
}
async function Ze() {
  if (confirm(h.PIPELINE_CONFIRM_STOP) && !ue()) {
    A(!0, "Deteniendo pipeline");
    try {
      y("INFO", h.PIPELINE_STOPPING), await pt();
      const e = await je();
      M(e), Ve(), y("INFO", h.PIPELINE_STOPPED);
    } catch (e) {
      y("ERROR", `Error: ${e.message}`);
    } finally {
      A(!1);
    }
  }
}
async function Je() {
  if (!ue()) {
    A(!0, "Guardando config");
    try {
      const e = Ke(),
        t = parseInt(
          document.getElementById("input-chunk-duration")?.value ||
            document.getElementById("input-rtmp-chunk")?.value ||
            document.getElementById("input-file-chunk")?.value ||
            String(E.CHUNK_DURATION),
        );
      await O("PUT", "/api/config", { config: e });
      try {
        await at(t), y("INFO", `Chunk synced: ${t}s`);
      } catch (o) {
        y("WARNING", `Chunk sync failed: ${o.message}`);
      }
      const n = await We();
      (Y.value = n),
        se(n),
        I(h.CONFIG_SAVED, "success"),
        y("INFO", "Configuración guardada");
    } catch (e) {
      const t = e.message;
      I(`${h.CONFIG_SAVE_ERROR}: ${t}`, "error"),
        y("ERROR", `Error al guardar: ${t}`);
    } finally {
      A(!1);
    }
  }
}
async function X() {
  try {
    await O("POST", "input/control/play"), I(h.INPUT_FILE_PLAY, "success");
  } catch (e) {
    I(`Error al reproducir: ${e.message}`, "error");
  }
}
async function Qe() {
  try {
    await O("POST", "input/control/pause"), I(h.INPUT_FILE_PAUSE, "success");
  } catch (e) {
    I(`Error al pausar: ${e.message}`, "error");
  }
}
async function ee(e) {
  try {
    await O("POST", "input/control/seek", { position: e });
  } catch (t) {
    I(`Error al buscar posición: ${t.message}`, "error");
  }
}
async function Xe() {
  try {
    const e = await fetch(`${window.location.origin}/api/input-info`, {
      headers: { Accept: "application/json" },
    });
    if (!e.ok) return null;
    const t = await e.json();
    return t.type === "file"
      ? {
          duration: t.duration || 0,
          position: t.position || 0,
          is_playing: t.is_playing || !1,
        }
      : null;
  } catch {
    return null;
  }
}
let Q = null;
function Rt() {
  Q && clearInterval(Q);
  const e = document.getElementById("input-file-position"),
    t = document.getElementById("file-time-current"),
    n = document.getElementById("file-time-total"),
    o = document.getElementById("btn-file-play"),
    i = document.getElementById("btn-file-pause");
  Q = setInterval(() => {
    Xe().then((u) => {
      u &&
        (e &&
          u.duration > 0 &&
          (e.value = ((u.position / u.duration) * 100).toString()),
        t && (t.textContent = Re(u.position)),
        n && (n.textContent = Re(u.duration)),
        o &&
          i &&
          (u.is_playing
            ? ((o.style.display = "none"), (i.style.display = "inline"))
            : ((o.style.display = "inline"), (i.style.display = "none"))));
    });
  }, ie.FILE_POLL);
}
function et() {
  const e = document.getElementById("btn-file-play"),
    t = document.getElementById("btn-file-pause"),
    n = document.getElementById("btn-file-restart"),
    o = document.getElementById("input-file-position");
  if (!e || !t || !n || !o) return;
  (e.style.display = "inline"),
    (t.style.display = "none"),
    e.addEventListener("click", () => {
      X().then(() => {
        (e.style.display = "none"), (t.style.display = "inline");
      });
    }),
    t.addEventListener("click", () => {
      Qe().then(() => {
        (t.style.display = "none"), (e.style.display = "inline");
      });
    }),
    n.addEventListener("click", () => {
      ee(0).then(() => {
        (o.value = "0"),
          X().then(() => {
            (e.style.display = "none"), (t.style.display = "inline");
          });
      });
    });
  let i = null;
  o.addEventListener("input", () => {
    i && clearTimeout(i);
    const u = parseInt(o.value);
    i = setTimeout(() => {
      Xe().then((r) => {
        r?.duration && ee((u / 100) * r.duration);
      });
    }, ie.SEEK_DEBOUNCE);
  }),
    Rt();
}
function tt() {
  const e = document.getElementById("input-rtmp-url");
  if (!e) return;
  const t = document.getElementById("input-rtmp-port"),
    n = document.getElementById("input-rtmp-app"),
    o = document.getElementById("input-rtmp-key"),
    i = t?.value || "1935",
    u = n?.value || "live",
    r = o?.value || "stream";
  e.value = `rtmp://127.0.0.1:${i}/${u}/${r}`;
}
let K = null,
  Ut = null;
async function nt() {
  yt(), y("INFO", h.LOADING);
  try {
    const e = await We();
    (Y.value = e), se(e);
    const t = document.getElementById("input-type");
    t?.value === "rtmp" && tt(),
      t?.value === "file" &&
        document.getElementById("input-file-path")?.value &&
        et();
    const n = await O("GET", "api/status");
    M(n), He();
    const o = ct("/ws/logs");
    (K = new dt(o)),
      K.onMessage((i) => {
        i.type === "log"
          ? y(i.level ?? "INFO", i.message ?? "")
          : i.type === "status" && i.status && M(i.status);
      }),
      K.onError(() => {
        y("ERROR", h.WS_ERROR);
      }),
      K.onClose(() => {
        (oe.value = !1), y("ERROR", h.WS_DISCONNECTED);
      }),
      K.connect(),
      (Ut = setInterval(async () => {
        try {
          const i = await O("GET", "api/status");
          M(i);
        } catch {}
      }, ie.STATUS_POLL)),
      y("INFO", h.SUCCESS);
  } catch (e) {
    y("ERROR", `Error de inicialización: ${e.message}`);
  }
}
function ot() {
  document.getElementById("btn-start")?.addEventListener("click", Ye),
    document.getElementById("btn-stop")?.addEventListener("click", Ze),
    document.getElementById("tts-engine")?.addEventListener("change", (e) => {
      const t = e.target.value === "edge-tts",
        n = document.getElementById("tts-voice-edge-group"),
        o = document.getElementById("tts-voice-piper-group");
      n && (n.style.display = t ? "block" : "none"),
        o && (o.style.display = t ? "none" : "block");
    });
}
async function it() {
  try {
    const n = (await (await fetch("/api/status")).json()).system || {},
      o = document.getElementById("metric-cpu-value"),
      i = document.getElementById("metric-cpu-bar"),
      u = document.getElementById("metric-memory-value"),
      r = document.getElementById("metric-memory-percent"),
      d = document.getElementById("metric-memory-bar"),
      a = document.getElementById("metric-gpu-value"),
      c = document.getElementById("metric-gpu-bar");
    o && (o.textContent = (n.cpu_percent || n.cpu_usage || 0) + "%"),
      i && (i.style.width = (n.cpu_percent || n.cpu_usage || 0) + "%"),
      u && (u.textContent = (n.memory_mb || 0).toFixed(0) + " MB"),
      r && (r.textContent = (n.memory_percent || n.memory_usage || 0) + "%"),
      d && (d.style.width = (n.memory_percent || n.memory_usage || 0) + "%"),
      a && (a.textContent = (n.gpu_usage || 0) + "%"),
      c && (c.style.width = (n.gpu_usage || 0) + "%");
  } catch (e) {
    console.error("Metrics refresh failed:", e);
  }
}
function Nt() {
  document.getElementById("btn-copy-emision")?.addEventListener("click", () => {
    const e = document.getElementById("url-emision");
    e?.textContent &&
      J(e.textContent)
        .then(() => I("URL de emisión copiada", "success"))
        .catch(() => I("Error al copiar URL", "error"));
  }),
    document
      .getElementById("btn-copy-stream")
      ?.addEventListener("click", () => {
        const e = document.getElementById("url-stream");
        e?.textContent &&
          J(e.textContent)
            .then(() => I("URL del stream copiada", "success"))
            .catch(() => I("Error al copiar URL", "error"));
      }),
    document
      .getElementById("btn-copy-player")
      ?.addEventListener("click", () => {
        const e = document.getElementById("url-player");
        if (e) {
          const t = e.getAttribute("href") || e.textContent;
          t &&
            J(t)
              .then(() => I("URL del player copiada", "success"))
              .catch(() => I("Error al copiar URL", "error"));
        }
      });
}
function st() {
  ot(),
    Nt(),
    setTimeout(() => {
      nt(), it();
    }, 100);
}
window.saveConfig = Je;
const Mt = Object.freeze(
  Object.defineProperty(
    {
      __proto__: null,
      applyConfigToUI: se,
      bootstrap: st,
      collectConfigFromUI: Ke,
      fileInputPause: Qe,
      fileInputPlay: X,
      fileInputSeek: ee,
      handleSaveConfig: Je,
      handleStart: Ye,
      handleStop: Ze,
      initDashboard: nt,
      refreshMetrics: it,
      setupEventListeners: ot,
      setupFilePlayerControls: et,
      updateRtmpUrl: tt,
    },
    Symbol.toStringTag,
    { value: "Module" },
  ),
);
document.addEventListener("DOMContentLoaded", st);
document.addEventListener("load", () => {
  setTimeout(() => {
    ze(
      async () => {
        const { initDashboard: e, refreshMetrics: t } =
          await Promise.resolve().then(() => Mt);
        return { initDashboard: e, refreshMetrics: t };
      },
      void 0,
    ).then(({ initDashboard: e, refreshMetrics: t }) => {
      e(), t();
    });
  }, 500);
});
ze(
  async () => {
    const { initKeyboardShortcuts: e } = await import(
      "./keyboard-shortcuts.mHPwB8P3.js"
    );
    return { initKeyboardShortcuts: e };
  },
  __vite__mapDeps([0, 1]),
).then(({ initKeyboardShortcuts: e }) => {
  e();
});
export { ze as _, Ze as a, Ye as b, Je as h, Dt as i };
