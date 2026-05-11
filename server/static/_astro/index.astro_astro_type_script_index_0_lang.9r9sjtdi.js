const __vite__mapDeps = (
  i,
  m = __vite__mapDeps,
  d = m.f ||
    (m.f = [
      "_astro/keyboard-shortcuts.Di-TQknN.js",
      "_astro/index.BpSbb1Lw.js",
    ]),
) => i.map((i) => d[i]);
import {
  j as B,
  p as N,
  a as te,
  s as Fe,
  t as ne,
  c as $e,
  w as oe,
  b as Ge,
  d as De,
  e as Z,
  f as Ve,
  g as f,
  u as O,
  r as We,
  i as at,
  m as ct,
} from "./store.YvzDn7sh.js";
import {
  D as E,
  a as F,
  u as dt,
  b as je,
  M as h,
  c as mt,
  W as pt,
  I as ie,
  d as gt,
  e as ze,
  f as ft,
} from "./api.ORjL4z5P.js";
import { s as I, c as Q } from "./index.BpSbb1Lw.js";
import { a as yt, i as vt, f as Te } from "./logpanel.DNPZhc8P.js";
const Et = (function () {
    const t = typeof document < "u" && document.createElement("link").relList;
    return t && t.supports && t.supports("modulepreload")
      ? "modulepreload"
      : "preload";
  })(),
  _t = function (e) {
    return "/" + e;
  },
  Re = {},
  It = function (t, n, o) {
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
          if (((c = _t(c)), c in Re)) return;
          Re[c] = !0;
          const _ = c.endsWith(".css"),
            p = _ ? '[rel="stylesheet"]' : "";
          if (document.querySelector(`link[href="${c}"]${p}`)) return;
          const y = document.createElement("link");
          if (
            ((y.rel = _ ? "stylesheet" : Et),
            _ || (y.as = "script"),
            (y.crossOrigin = ""),
            (y.href = c),
            d && y.setAttribute("nonce", d),
            document.head.appendChild(y),
            _)
          )
            return new Promise((g, C) => {
              y.addEventListener("load", g),
                y.addEventListener("error", () =>
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
let Ue = !1;
function ht() {
  Ue ||
    ((Ue = !0),
    Me(),
    setInterval(() => {
      Me();
    }, 1e3));
}
function Me() {
  const e = document.getElementById("live-clock");
  e && (e.textContent = new Date().toLocaleTimeString("en-US", { hour12: !1 }));
}
var M = ((e) => (
  (e.STOPPED = "stopped"),
  (e.RUNNING = "running"),
  (e.STARTING = "starting"),
  (e.STOPPING = "stopping"),
  (e.ERROR = "error"),
  e
))(M || {});
function bt(e) {
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
let He = null,
  Ke = null,
  qe = null;
function Bt() {
  (qe = B(() => {
    const e = N.value,
      t = s("status-dot"),
      n = s("status-text");
    if (!t || !n) return;
    const o = bt(e?.state);
    t.classList.toggle("running", o === M.RUNNING),
      t.classList.toggle("error", o === M.ERROR),
      (n.textContent = o === M.RUNNING ? "ACTIVO" : "APAGADO");
    const i = s("btn-start"),
      u = s("btn-stop");
    if (i) {
      const r = o === M.RUNNING;
      (i.disabled = r), (i.style.opacity = r ? "0.5" : "1");
    }
    if (u) {
      const r = o === M.RUNNING;
      (u.disabled = !r), (u.style.opacity = r ? "1" : "0.5");
    }
  })),
    (Ke = B(() => {
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
    })),
    (He = B(() => {
      const e = N.value,
        t = s("pipeline-indicator");
      t && t.classList.toggle("active", e?.state === "running");
    }));
}
function xt() {
  qe?.(), Ke?.(), He?.();
}
let Ye = null;
function X(e) {
  return e < 40 ? "low" : e < 80 ? "medium" : "high";
}
function St(e) {
  return e < 80 ? "warning" : "critical";
}
function Ct() {
  Ye = B(() => {
    const e = Fe.value,
      t = ne.value,
      n = s("metric-cpu"),
      o = s("metric-cpu-bar"),
      i = s("metric-cpu-value");
    o &&
      ((o.style.width = `${e.cpu}%`),
      o.classList.remove("low", "medium", "high"),
      o.classList.add(X(e.cpu))),
      n &&
        (n.classList.remove("warning", "critical"), n.classList.add(St(e.cpu))),
      i && (i.textContent = `${e.cpu.toFixed(0)}%`);
    const u = s("metric-memory-bar"),
      r = s("metric-memory-value"),
      d = s("metric-memory-percent");
    u &&
      ((u.style.width = `${e.memoryPercent}%`),
      u.classList.remove("low", "medium", "high"),
      u.classList.add(X(e.memoryPercent))),
      r && (r.textContent = `${e.memoryMb.toFixed(0)} MB`),
      d && (d.textContent = `${e.memoryPercent.toFixed(0)}%`);
    const a = s("metric-gpu-bar"),
      c = s("metric-gpu-value"),
      _ = s("metric-gpu-memory");
    a &&
      ((a.style.width = `${e.gpuUtil}%`),
      a.classList.remove("low", "medium", "high"),
      a.classList.add(X(e.gpuUtil))),
      c && (c.textContent = `${e.gpuUtil.toFixed(0)}%`),
      _ &&
        (_.textContent =
          e.gpuMemMb > 0 ? `${e.gpuMemMb.toFixed(0)} MB` : "N/A");
    const p = s("metric-throughput-bar"),
      y = s("metric-throughput-value");
    p && (p.style.width = `${Math.min(t * 10, 100)}%`),
      y && (y.textContent = `${t.toFixed(2)}/s`);
  });
}
function wt() {
  Ye?.();
}
let Ze = null;
function kt() {
  Ze = B(() => {
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
        H = s(`module-chunks-${l}`),
        K = s(`module-memory-${l}`),
        q = s(`module-encoder-${l}`);
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
        (H && (H.textContent = String(m?.processed_chunks ?? 0)),
        K &&
          (K.textContent =
            m?.memory_mb !== void 0 ? `${Math.round(m.memory_mb)} MB` : "--"),
        q && m?.extra)
      ) {
        const b = m.extra.encoder_label || (m.extra.using_gpu ? "GPU" : "CPU");
        q.textContent = b;
      }
      const U = s(`gpu-badge-${l}`);
      if (U && m?.extra) {
        const b = n && m.enabled && (m.processed_chunks ?? 0) > 0;
        m.extra.using_gpu
          ? ((U.style.display = "inline"), U.classList.toggle("active", b))
          : (U.style.display = "none");
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
      y = s("module-encoder-input");
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
    if (y && a) {
      const l = a.extra?.encoder_label || (a.extra?.using_gpu ? "GPU" : "CPU");
      y.textContent = l;
    }
    const g = i.video_muxer,
      C = s("module-time-video_muxer"),
      G = s("module-memory-video_muxer"),
      D = s("module-chunks-video_muxer"),
      V = s("module-encoder-video_muxer"),
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
      (G &&
        g &&
        (G.textContent =
          g.memory_mb !== void 0 ? `${Math.round(g.memory_mb)} MB` : "--"),
      D && g && (D.textContent = String(g.processed_chunks ?? 0)),
      V && g?.extra)
    ) {
      const l = g.extra.encoder_label || (g.extra.using_gpu ? "GPU" : "CPU");
      V.textContent = l;
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
    const v = i.output,
      k = s("module-time-output"),
      W = s("module-memory-output"),
      j = s("module-chunks-output"),
      z = s("module-encoder-output"),
      S = s("gpu-badge-output");
    if (k)
      if (v?.last_process_time_ms !== void 0 && v.last_process_time_ms > 0) {
        const l = v.last_process_time_ms;
        k.textContent =
          l < 1e3 ? `${Math.round(l)}ms` : `${(l / 1e3).toFixed(1)}s`;
      } else
        n && o > 0
          ? (k.textContent = `${(1e3 / o).toFixed(0)}ms`)
          : (k.textContent = "--");
    if (
      (W &&
        v &&
        (W.textContent =
          v.memory_mb !== void 0 ? `${Math.round(v.memory_mb)} MB` : "--"),
      j && v && (j.textContent = String(v.processed_chunks ?? 0)),
      z && v?.extra)
    ) {
      const l = v.extra.encoder_label || (v.extra.using_gpu ? "GPU" : "CPU");
      z.textContent = l;
    }
    if (S) {
      const l = n && v?.enabled && (v.processed_chunks ?? 0) > 0;
      v?.extra?.using_gpu ?? !1
        ? ((S.textContent = "GPU"),
          (S.style.display = "inline"),
          S.classList.toggle("active", l))
        : ((S.textContent = "CPU"),
          (S.style.display = "inline"),
          S.classList.remove("active"));
    }
  });
}
function Lt() {
  Ze?.();
}
let Je = null;
function Pt() {
  Je = B(() => {
    const e = $e.value,
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
function Tt() {
  Je?.();
}
let Qe = null;
function Rt() {
  Qe = B(() => {
    const e = oe.value,
      t = s("ws-status-badge");
    t &&
      ((t.textContent = e ? "WS ON" : "WS OFF"),
      t.classList.toggle("active", e));
  });
}
function Ut() {
  Qe?.();
}
let Xe = null;
function Mt() {
  (Xe = B(() => {
    N.value;
    const e = s("live-clock");
    e &&
      (e.textContent = new Date().toLocaleTimeString("en-US", { hour12: !1 }));
  })),
    ht();
}
function Nt() {
  Xe?.();
}
let et = null;
function Ot() {
  et = B(() => {
    const e = Ge.value,
      t = s("remote-config"),
      n = s("btn-mode-local"),
      o = s("btn-mode-remote");
    t && (t.style.display = e === "remote" ? "" : "none"),
      n && n.classList.toggle("active", e === "local"),
      o && o.classList.toggle("active", e === "remote");
  });
}
function At() {
  et?.();
}
let tt = null;
function Ft() {
  tt = B(() => {
    De.value, Z.value;
  });
}
function $t() {
  tt?.();
}
let nt = null,
  ee = 0;
function Gt() {
  nt = B(() => {
    const e = Ve.value,
      t = e.slice(ee);
    for (const n of t) yt(n.level, n.message, n.timestamp);
    ee = e.length;
  });
}
function Dt() {
  nt?.(), (ee = 0);
}
function ot() {
  Bt(), Ct(), kt(), Pt(), Rt(), Mt(), Ot(), Ft(), Gt();
}
function it() {
  xt(), wt(), Lt(), Tt(), Ut(), Nt(), At(), $t(), Dt();
}
const dn = Object.freeze(
  Object.defineProperty(
    {
      __proto__: null,
      addLog: f,
      connectionMode: Ge,
      connectionUrls: $e,
      inputType: at,
      isPipelineRunning: te,
      moduleStates: ct,
      pipelineConfig: Z,
      pipelineLogs: Ve,
      pipelineStatus: N,
      resetThroughput: We,
      startEffects: ot,
      stopEffects: it,
      systemMetrics: Fe,
      throughputAvg: ne,
      throughputHistory: De,
      updateStatus: O,
      wsConnected: oe,
    },
    Symbol.toStringTag,
    { value: "Module" },
  ),
);
function Vt() {
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
function st(e) {
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
    y = document.getElementById("tts-device"),
    g = document.getElementById("tts-device-group"),
    C = document.getElementById("tts-voice-edge"),
    G = document.getElementById("tts-voice-piper"),
    D = document.getElementById("tts-voice-edge-group"),
    V = document.getElementById("tts-voice-piper-group"),
    x = document.getElementById("tts-speed"),
    v = document.getElementById("subtitle-enabled"),
    k = document.getElementById("subtitle-format"),
    W = document.getElementById("subtitle-use-translated"),
    j = document.getElementById("muxer-enabled"),
    z = document.getElementById("video-muxer-engine"),
    S = document.getElementById("hls-segment"),
    l = document.getElementById("hls-list"),
    m = document.getElementById("hls-encoder"),
    L = document.getElementById("hls-crf"),
    H = document.getElementById("hls-audio-offset"),
    K = document.getElementById("hls-audio-codec"),
    q = document.getElementById("hls-audio-bitrate"),
    U = e.input?.type || "srt";
  t && ((t.value = U), Wt());
  const b = document.getElementById("input-srt-port"),
    ue = document.getElementById("input-srt-mode"),
    le = document.getElementById("input-srt-latency"),
    P = e.input?.srt;
  b && P?.listen_port && (b.value = String(P.listen_port)),
    ue && P?.mode && (ue.value = P.mode),
    le && P?.latency_ms && (le.value = String(P.latency_ms));
  const re = document.getElementById("input-chunk-duration"),
    ae = document.getElementById("input-rtmp-chunk"),
    ce = document.getElementById("input-file-chunk"),
    J = e.pipeline?.chunk_duration_sec || E.CHUNK_DURATION;
  re && (re.value = String(P?.chunk_duration_sec || J));
  const T = e.input?.rtmp,
    R = e.input?.file;
  ae && (ae.value = String(T?.chunk_duration_sec || J));
  const de = document.getElementById("input-rtmp-url"),
    me = document.getElementById("input-rtmp-mode"),
    pe = document.getElementById("input-rtmp-app");
  de && T?.url && (de.value = T.url),
    me && T?.mode && (me.value = T.mode),
    pe && T?.app && (pe.value = T.app);
  const ge = document.getElementById("input-file-path"),
    fe = document.getElementById("input-file-loop"),
    ye = document.getElementById("input-file-speed");
  ge && R?.path && (ge.value = R.path),
    fe && R?.loop !== void 0 && (fe.value = R.loop ? "true" : "false"),
    ye && R?.speed && (ye.value = String(R.speed)),
    ce && (ce.value = String(R?.chunk_duration_sec || J));
  const rt =
    e.output?.type === "web" ? "webplayer" : e.output?.type || "webplayer";
  if (
    (n && ((n.value = rt), jt()),
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
      D && V))
  ) {
    const Pe = p.value === "edge-tts";
    (D.style.display = Pe ? "block" : "none"),
      (V.style.display = Pe ? "none" : "block");
  }
  y && (y.value = e.modules.tts_engine.device || "auto"),
    C && (C.value = e.modules.tts_engine.voice || "es-ES-AlvaroNeural"),
    G && (G.value = e.modules.tts_engine.voice || "es_ES-sharvard-medium"),
    x && (x.value = String(e.modules.tts_engine.speed)),
    v && (v.checked = e.modules.subtitle_generator.enabled),
    k && (k.value = e.modules.subtitle_generator.format),
    W && (W.value = String(e.modules.subtitle_generator.use_translated)),
    j && (j.checked = e.modules.video_muxer.enabled),
    z && (z.value = e.modules.video_muxer.engine || "hls");
  const ve = document.getElementById("audio-mixer-enabled");
  ve && (ve.checked = e.modules.audio_mixer?.enabled ?? !1);
  const Ee = document.getElementById("audio-mixer-original-volume");
  Ee && (Ee.value = String(e.modules.audio_mixer?.original_volume ?? 0.3));
  const _e = document.getElementById("audio-mixer-original-value");
  _e &&
    (_e.textContent = String(e.modules.audio_mixer?.original_volume ?? 0.3));
  const Ie = document.getElementById("audio-mixer-dubbed-volume");
  Ie &&
    (Ie.value = String(
      e.modules.audio_mixer?.tts_volume ??
        e.modules.audio_mixer?.dubbed_volume ??
        1,
    ));
  const he = document.getElementById("audio-mixer-dubbed-value");
  he &&
    (he.textContent = String(
      e.modules.audio_mixer?.tts_volume ??
        e.modules.audio_mixer?.dubbed_volume ??
        1,
    )),
    S && (S.value = String(e.modules.video_muxer.hls_segment_duration)),
    l && (l.value = String(e.modules.video_muxer.hls_list_size)),
    m && (m.value = e.modules.video_muxer.encoder_mode),
    L && (L.value = String(e.modules.video_muxer.video_crf)),
    H && (H.value = String(e.modules.video_muxer.audio_offset_ms || 0)),
    K && (K.value = e.modules.video_muxer.audio_codec || "aac"),
    q && (q.value = e.modules.video_muxer.audio_bitrate || "192k");
  const be = document.getElementById("webrtc-encoder"),
    Be = document.getElementById("webrtc-video-codec"),
    xe = document.getElementById("webrtc-video-bitrate"),
    Se = document.getElementById("webrtc-video-resolution"),
    Ce = document.getElementById("webrtc-video-fps"),
    we = document.getElementById("webrtc-audio-codec"),
    ke = document.getElementById("webrtc-audio-bitrate"),
    Le = document.getElementById("webrtc-audio-sample-rate");
  be && (be.value = e.modules.video_muxer.encoder_mode || "auto"),
    Be && (Be.value = e.modules.video_muxer.video_codec || "h264"),
    xe && (xe.value = e.modules.video_muxer.video_bitrate || "1000k"),
    Se &&
      e.modules.video_muxer.video_width &&
      e.modules.video_muxer.video_height &&
      (Se.value = `${e.modules.video_muxer.video_width}x${e.modules.video_muxer.video_height}`),
    Ce &&
      e.modules.video_muxer.video_fps &&
      (Ce.value = String(e.modules.video_muxer.video_fps)),
    we && (we.value = e.modules.video_muxer.audio_codec || "opus"),
    ke &&
      (ke.value =
        e.modules.video_muxer.webrtc_audio_bitrate ||
        e.modules.video_muxer.audio_bitrate ||
        "64k"),
    Le &&
      e.modules.video_muxer.audio_sample_rate &&
      (Le.value = String(e.modules.video_muxer.audio_sample_rate));
}
function Wt() {
  const e = document.getElementById("input-type");
  e && (e.value = e.value);
}
function jt() {
  const e = document.getElementById("output-type");
  e && (e.value = e.value);
}
let ut = !1;
function $(e, t = "") {
  (ut = e),
    document.body.classList.toggle("loading", e),
    e && t && f("INFO", `${t}...`);
}
function se() {
  return ut;
}
async function zt() {
  if (!se()) {
    $(!0, "Iniciando pipeline");
    try {
      f("INFO", h.PIPELINE_STARTING), await gt();
      const e = await ze();
      O(e), f("INFO", h.PIPELINE_STARTED);
    } catch (e) {
      f("ERROR", `Error: ${e.message}`);
    } finally {
      $(!1);
    }
  }
}
async function Ht() {
  if (confirm(h.PIPELINE_CONFIRM_STOP) && !se()) {
    $(!0, "Deteniendo pipeline");
    try {
      f("INFO", h.PIPELINE_STOPPING), await ft();
      const e = await ze();
      O(e), We(), f("INFO", h.PIPELINE_STOPPED);
    } catch (e) {
      f("ERROR", `Error: ${e.message}`);
    } finally {
      $(!1);
    }
  }
}
async function Kt() {
  if (!se()) {
    $(!0, "Guardando config");
    try {
      const e = Vt(),
        t = parseInt(
          document.getElementById("input-chunk-duration")?.value ||
            document.getElementById("input-rtmp-chunk")?.value ||
            document.getElementById("input-file-chunk")?.value ||
            String(E.CHUNK_DURATION),
        );
      await F("PUT", "/api/config", { config: e });
      try {
        await dt(t), f("INFO", `Chunk synced: ${t}s`);
      } catch (o) {
        f("WARNING", `Chunk sync failed: ${o.message}`);
      }
      const n = await je();
      (Z.value = n),
        st(n),
        I(h.CONFIG_SAVED, "success"),
        f("INFO", "Configuración guardada");
    } catch (e) {
      const t = e.message;
      I(`${h.CONFIG_SAVE_ERROR}: ${t}`, "error"),
        f("ERROR", `Error al guardar: ${t}`);
    } finally {
      $(!1);
    }
  }
}
async function Ne() {
  try {
    await F("POST", "input/control/play"), I(h.INPUT_FILE_PLAY, "success");
  } catch (e) {
    I(`Error al reproducir: ${e.message}`, "error");
  }
}
async function qt() {
  try {
    await F("POST", "input/control/pause"), I(h.INPUT_FILE_PAUSE, "success");
  } catch (e) {
    I(`Error al pausar: ${e.message}`, "error");
  }
}
async function Oe(e) {
  try {
    await F("POST", "input/control/seek", { position: e });
  } catch (t) {
    I(`Error al buscar posición: ${t.message}`, "error");
  }
}
async function lt() {
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
let A = null;
function Yt() {
  A && clearInterval(A);
  const e = document.getElementById("input-file-position"),
    t = document.getElementById("file-time-current"),
    n = document.getElementById("file-time-total"),
    o = document.getElementById("btn-file-play"),
    i = document.getElementById("btn-file-pause");
  A = setInterval(() => {
    lt().then((u) => {
      u &&
        (e &&
          u.duration > 0 &&
          (e.value = ((u.position / u.duration) * 100).toString()),
        t && (t.textContent = Te(u.position)),
        n && (n.textContent = Te(u.duration)),
        o &&
          i &&
          (u.is_playing
            ? ((o.style.display = "none"), (i.style.display = "inline"))
            : ((o.style.display = "inline"), (i.style.display = "none"))));
    });
  }, ie.FILE_POLL);
}
function Zt() {
  A && (clearInterval(A), (A = null));
}
function Jt() {
  const e = document.getElementById("btn-file-play"),
    t = document.getElementById("btn-file-pause"),
    n = document.getElementById("btn-file-restart"),
    o = document.getElementById("input-file-position");
  if (!e || !t || !n || !o) return;
  (e.style.display = "inline"),
    (t.style.display = "none"),
    e.addEventListener("click", () => {
      Ne().then(() => {
        (e.style.display = "none"), (t.style.display = "inline");
      });
    }),
    t.addEventListener("click", () => {
      qt().then(() => {
        (t.style.display = "none"), (e.style.display = "inline");
      });
    }),
    n.addEventListener("click", () => {
      Oe(0).then(() => {
        (o.value = "0"),
          Ne().then(() => {
            (e.style.display = "none"), (t.style.display = "inline");
          });
      });
    });
  let i = null;
  o.addEventListener("input", () => {
    i && clearTimeout(i);
    const u = parseInt(o.value);
    i = setTimeout(() => {
      lt().then((r) => {
        r?.duration && Oe((u / 100) * r.duration);
      });
    }, ie.SEEK_DEBOUNCE);
  }),
    Yt();
}
function Qt() {
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
let w = null,
  Y = null;
async function Xt() {
  vt(), f("INFO", h.LOADING);
  try {
    const e = await je();
    (Z.value = e), st(e);
    const t = document.getElementById("input-type");
    t?.value === "rtmp" && Qt(),
      t?.value === "file" &&
        document.getElementById("input-file-path")?.value &&
        Jt();
    const n = await F("GET", "api/status");
    O(n), ot();
    const o = mt("/ws/logs");
    (w = new pt(o)),
      w.onMessage((i) => {
        i.type === "log"
          ? f(i.level ?? "INFO", i.message ?? "")
          : i.type === "status" && i.status && O(i.status);
      }),
      w.onError(() => {
        f("ERROR", h.WS_ERROR);
      }),
      w.onClose(() => {
        (oe.value = !1), f("ERROR", h.WS_DISCONNECTED);
      }),
      w.connect(),
      (Y = setInterval(async () => {
        try {
          const i = await F("GET", "api/status");
          O(i);
        } catch {}
      }, ie.STATUS_POLL)),
      f("INFO", h.SUCCESS);
  } catch (e) {
    f("ERROR", `Error de inicialización: ${e.message}`);
  }
}
function en() {
  Y && (clearInterval(Y), (Y = null)), w && (w.close(), (w = null)), it(), Zt();
}
function tn() {
  document.getElementById("btn-start")?.addEventListener("click", zt),
    document.getElementById("btn-stop")?.addEventListener("click", Ht),
    document.getElementById("tts-engine")?.addEventListener("change", (e) => {
      const t = e.target.value === "edge-tts",
        n = document.getElementById("tts-voice-edge-group"),
        o = document.getElementById("tts-voice-piper-group");
      n && (n.style.display = t ? "block" : "none"),
        o && (o.style.display = t ? "none" : "block");
    });
}
async function nn() {
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
function on() {
  document.getElementById("btn-copy-emision")?.addEventListener("click", () => {
    const e = document.getElementById("url-emision");
    e?.textContent &&
      Q(e.textContent)
        .then(() => I("URL de emisión copiada", "success"))
        .catch(() => I("Error al copiar URL", "error"));
  }),
    document
      .getElementById("btn-copy-stream")
      ?.addEventListener("click", () => {
        const e = document.getElementById("url-stream");
        e?.textContent &&
          Q(e.textContent)
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
            Q(t)
              .then(() => I("URL del player copiada", "success"))
              .catch(() => I("Error al copiar URL", "error"));
        }
      });
}
let Ae = !1;
function sn() {
  Ae ||
    ((Ae = !0),
    tn(),
    on(),
    setTimeout(() => {
      Xt(), nn();
    }, 100));
}
window.addEventListener("beforeunload", en);
window.saveConfig = Kt;
document.addEventListener("DOMContentLoaded", sn);
It(
  async () => {
    const { initKeyboardShortcuts: e } = await import(
      "./keyboard-shortcuts.Di-TQknN.js"
    );
    return { initKeyboardShortcuts: e };
  },
  __vite__mapDeps([0, 1]),
).then(({ initKeyboardShortcuts: e }) => {
  e();
});
export { It as _, Ht as a, zt as b, Kt as h, dn as i };
