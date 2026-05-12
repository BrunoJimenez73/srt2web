const __vite__mapDeps = (
  i,
  m = __vite__mapDeps,
  d = m.f ||
    (m.f = [
      "_astro/keyboard-shortcuts.BUCgNMeb.js",
      "_astro/index.BpSbb1Lw.js",
    ]),
) => i.map((i) => d[i]);
import {
  j as B,
  p as M,
  a as se,
  s as De,
  t as ue,
  c as Ve,
  w as le,
  b as We,
  d as je,
  e as Q,
  f as ze,
  g as f,
  u as $,
  r as He,
  i as ft,
  m as yt,
} from "./store.BQ17F1K4.js";
import {
  D as E,
  a as D,
  u as vt,
  b as Ke,
  M as h,
  c as Et,
  g as _t,
  W as It,
  d as ht,
  e as qe,
  f as bt,
  I as Ye,
} from "./api.BpNi2mzZ.js";
import { s as I, c as ee } from "./index.BpSbb1Lw.js";
import { a as Bt, i as xt, f as Ue } from "./logpanel.DVarbH4P.js";
const St = (function () {
    const t = typeof document < "u" && document.createElement("link").relList;
    return t && t.supports && t.supports("modulepreload")
      ? "modulepreload"
      : "preload";
  })(),
  Ct = function (e) {
    return "/" + e;
  },
  Me = {},
  kt = function (t, n, o) {
    let u = Promise.resolve();
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
      u = a(
        n.map((c) => {
          if (((c = Ct(c)), c in Me)) return;
          Me[c] = !0;
          const _ = c.endsWith(".css"),
            p = _ ? '[rel="stylesheet"]' : "";
          if (document.querySelector(`link[href="${c}"]${p}`)) return;
          const y = document.createElement("link");
          if (
            ((y.rel = _ ? "stylesheet" : St),
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
    function i(r) {
      const d = new Event("vite:preloadError", { cancelable: !0 });
      if (((d.payload = r), window.dispatchEvent(d), !d.defaultPrevented))
        throw r;
    }
    return u.then((r) => {
      for (const d of r || []) d.status === "rejected" && i(d.reason);
      return t().catch(i);
    });
  };
let Oe = !1;
function wt() {
  Oe ||
    ((Oe = !0),
    Ae(),
    setInterval(() => {
      Ae();
    }, 1e3));
}
function Ae() {
  const e = document.getElementById("live-clock");
  e && (e.textContent = new Date().toLocaleTimeString("en-US", { hour12: !1 }));
}
var A = ((e) => (
  (e.STOPPED = "stopped"),
  (e.RUNNING = "running"),
  (e.STARTING = "starting"),
  (e.STOPPING = "stopping"),
  (e.ERROR = "error"),
  e
))(A || {});
function Lt(e) {
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
let Ze = null,
  Je = null,
  Qe = null;
function Tt() {
  (Qe = B(() => {
    const e = M.value,
      t = s("status-dot"),
      n = s("status-text");
    if (!t || !n) return;
    const o = Lt(e?.state);
    t.classList.toggle("running", o === A.RUNNING),
      t.classList.toggle("error", o === A.ERROR),
      (n.textContent = o === A.RUNNING ? "ACTIVO" : "APAGADO");
    const u = s("btn-start"),
      i = s("btn-stop");
    if (u) {
      const r = o === A.RUNNING;
      (u.disabled = r), (u.style.opacity = r ? "0.5" : "1");
    }
    if (i) {
      const r = o === A.RUNNING;
      (i.disabled = !r), (i.style.opacity = r ? "1" : "0.5");
    }
  })),
    (Je = B(() => {
      const t = M.value?.modules ?? [],
        n = se.value,
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
      const u = s("indicator-output"),
        i = t.find((r) => r.name === "output");
      u && i && u.classList.toggle("active", n && i.enabled);
    })),
    (Ze = B(() => {
      const e = M.value,
        t = s("pipeline-indicator");
      t && t.classList.toggle("active", e?.state === "running");
    }));
}
function Pt() {
  Qe?.(), Je?.(), Ze?.();
}
let Xe = null;
function te(e) {
  return e < 40 ? "low" : e < 80 ? "medium" : "high";
}
function Rt(e) {
  return e < 80 ? "warning" : "critical";
}
function Nt() {
  Xe = B(() => {
    const e = De.value,
      t = ue.value,
      n = s("metric-cpu"),
      o = s("metric-cpu-bar"),
      u = s("metric-cpu-value");
    o &&
      ((o.style.width = `${e.cpu}%`),
      o.classList.remove("low", "medium", "high"),
      o.classList.add(te(e.cpu))),
      n &&
        (n.classList.remove("warning", "critical"), n.classList.add(Rt(e.cpu))),
      u && (u.textContent = `${e.cpu.toFixed(0)}%`);
    const i = s("metric-memory-bar"),
      r = s("metric-memory-value"),
      d = s("metric-memory-percent");
    i &&
      ((i.style.width = `${e.memoryPercent}%`),
      i.classList.remove("low", "medium", "high"),
      i.classList.add(te(e.memoryPercent))),
      r && (r.textContent = `${e.memoryMb.toFixed(0)} MB`),
      d && (d.textContent = `${e.memoryPercent.toFixed(0)}%`);
    const a = s("metric-gpu-bar"),
      c = s("metric-gpu-value"),
      _ = s("metric-gpu-memory");
    a &&
      ((a.style.width = `${e.gpuUtil}%`),
      a.classList.remove("low", "medium", "high"),
      a.classList.add(te(e.gpuUtil))),
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
function Ut() {
  Xe?.();
}
let et = null;
function Mt() {
  et = B(() => {
    const t = M.value?.modules ?? [],
      n = se.value,
      o = ue.value,
      u = Object.fromEntries(t.map((l) => [l.name, l]));
    for (const l of [
      "audio_extractor",
      "transcriber",
      "translator",
      "tts_engine",
      "subtitle_generator",
      "audio_mixer",
    ]) {
      const m = u[l],
        P = s(`module-time-${l}`),
        q = s(`module-chunks-${l}`),
        Y = s(`module-memory-${l}`),
        Z = s(`module-encoder-${l}`);
      if (P)
        if (m?.last_process_time_ms !== void 0 && m.last_process_time_ms > 0) {
          const b = m.last_process_time_ms;
          P.textContent =
            b < 1e3 ? `${Math.round(b)}ms` : `${(b / 1e3).toFixed(1)}s`;
        } else if (n && o > 0) {
          const b = (1e3 / o).toFixed(0);
          P.textContent = `${b}ms`;
        } else P.textContent = "--";
      if (
        (q && (q.textContent = String(m?.processed_chunks ?? 0)),
        Y &&
          (Y.textContent =
            m?.memory_mb !== void 0 ? `${Math.round(m.memory_mb)} MB` : "--"),
        Z && m?.extra)
      ) {
        const b = m.extra.encoder_label || (m.extra.using_gpu ? "GPU" : "CPU");
        Z.textContent = b;
      }
      const O = s(`gpu-badge-${l}`);
      if (O && m?.extra) {
        const b = n && m.enabled && (m.processed_chunks ?? 0) > 0;
        m.extra.using_gpu
          ? ((O.style.display = "inline"), O.classList.toggle("active", b))
          : (O.style.display = "none");
      }
    }
    const i = u.audio_extractor,
      r = s("module-device-audio_extractor"),
      d = s("gpu-badge-audio_extractor");
    if (
      (r &&
        i?.extra &&
        (r.textContent = i.extra.device || (i.extra.using_gpu ? "GPU" : "CPU")),
      d && i?.extra)
    ) {
      const l = n && i.enabled && (i.processed_chunks ?? 0) > 0;
      i.extra.using_gpu
        ? ((d.style.display = "inline"), d.classList.toggle("active", l))
        : (d.style.display = "none");
    }
    const a = u.input ?? u.srt_input ?? u.rtmp_input ?? u.file_input,
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
    const g = u.video_muxer,
      C = s("module-time-video_muxer"),
      V = s("module-memory-video_muxer"),
      W = s("module-chunks-video_muxer"),
      j = s("module-encoder-video_muxer"),
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
      (V &&
        g &&
        (V.textContent =
          g.memory_mb !== void 0 ? `${Math.round(g.memory_mb)} MB` : "--"),
      W && g && (W.textContent = String(g.processed_chunks ?? 0)),
      j && g?.extra)
    ) {
      const l = g.extra.encoder_label || (g.extra.using_gpu ? "GPU" : "CPU");
      j.textContent = l;
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
    const v = u.output,
      T = s("module-time-output"),
      z = s("module-memory-output"),
      H = s("module-chunks-output"),
      K = s("module-encoder-output"),
      S = s("gpu-badge-output");
    if (T)
      if (v?.last_process_time_ms !== void 0 && v.last_process_time_ms > 0) {
        const l = v.last_process_time_ms;
        T.textContent =
          l < 1e3 ? `${Math.round(l)}ms` : `${(l / 1e3).toFixed(1)}s`;
      } else
        n && o > 0
          ? (T.textContent = `${(1e3 / o).toFixed(0)}ms`)
          : (T.textContent = "--");
    if (
      (z &&
        v &&
        (z.textContent =
          v.memory_mb !== void 0 ? `${Math.round(v.memory_mb)} MB` : "--"),
      H && v && (H.textContent = String(v.processed_chunks ?? 0)),
      K && v?.extra)
    ) {
      const l = v.extra.encoder_label || (v.extra.using_gpu ? "GPU" : "CPU");
      K.textContent = l;
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
function Ot() {
  et?.();
}
let tt = null;
function At() {
  tt = B(() => {
    const e = Ve.value,
      t = s("url-emision-label"),
      n = s("url-emision"),
      o = s("url-stream"),
      u = s("url-player");
    t && (t.textContent = e.primaryLabel),
      n && (n.textContent = e.primaryUrl),
      o && (o.textContent = e.streamUrl),
      u && ((u.textContent = e.playerUrl), (u.href = e.playerUrl));
  });
}
function Ft() {
  tt?.();
}
let nt = null;
function $t() {
  nt = B(() => {
    const e = le.value,
      t = s("ws-status-badge");
    t &&
      ((t.textContent = e ? "WS ON" : "WS OFF"),
      t.classList.toggle("active", e));
  });
}
function Gt() {
  nt?.();
}
let ot = null;
function Dt() {
  (ot = B(() => {
    M.value;
    const e = s("live-clock");
    e &&
      (e.textContent = new Date().toLocaleTimeString("en-US", { hour12: !1 }));
  })),
    wt();
}
function Vt() {
  ot?.();
}
let it = null;
function Wt() {
  it = B(() => {
    const e = We.value,
      t = s("remote-config"),
      n = s("btn-mode-local"),
      o = s("btn-mode-remote");
    t && (t.style.display = e === "remote" ? "" : "none"),
      n && n.classList.toggle("active", e === "local"),
      o && o.classList.toggle("active", e === "remote");
  });
}
function jt() {
  it?.();
}
let st = null;
function zt() {
  st = B(() => {
    je.value, Q.value;
  });
}
function Ht() {
  st?.();
}
let ut = null,
  oe = 0;
function Kt() {
  ut = B(() => {
    const e = ze.value,
      t = e.slice(oe);
    for (const n of t) Bt(n.level, n.message, n.timestamp);
    oe = e.length;
  });
}
function qt() {
  ut?.(), (oe = 0);
}
function lt() {
  Tt(), Nt(), Mt(), At(), $t(), Dt(), Wt(), zt(), Kt();
}
function rt() {
  Pt(), Ut(), Ot(), Ft(), Gt(), Vt(), jt(), Ht(), qt();
}
const In = Object.freeze(
  Object.defineProperty(
    {
      __proto__: null,
      addLog: f,
      connectionMode: We,
      connectionUrls: Ve,
      inputType: ft,
      isPipelineRunning: se,
      moduleStates: yt,
      pipelineConfig: Q,
      pipelineLogs: ze,
      pipelineStatus: M,
      resetThroughput: He,
      startEffects: lt,
      stopEffects: rt,
      systemMetrics: De,
      throughputAvg: ue,
      throughputHistory: je,
      updateStatus: $,
      wsConnected: le,
    },
    Symbol.toStringTag,
    { value: "Module" },
  ),
);
function Yt() {
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
        const u = document.getElementById("webrtc-video-resolution");
        if (u?.value) {
          const [i, r] = u.value.split("x").map(Number);
          return { video_width: i, video_height: r };
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
function at(e) {
  const t = document.getElementById("input-type"),
    n = document.getElementById("output-type"),
    o = document.getElementById("whisper-enabled"),
    u = document.getElementById("whisper-model"),
    i = document.getElementById("whisper-lang"),
    r = document.getElementById("whisper-device"),
    d = document.getElementById("translator-enabled"),
    a = document.getElementById("translator-source"),
    c = document.getElementById("translator-target"),
    _ = document.getElementById("tts-enabled"),
    p = document.getElementById("tts-engine"),
    y = document.getElementById("tts-device"),
    g = document.getElementById("tts-device-group"),
    C = document.getElementById("tts-voice-edge"),
    V = document.getElementById("tts-voice-piper"),
    W = document.getElementById("tts-voice-edge-group"),
    j = document.getElementById("tts-voice-piper-group"),
    x = document.getElementById("tts-speed"),
    v = document.getElementById("subtitle-enabled"),
    T = document.getElementById("subtitle-format"),
    z = document.getElementById("subtitle-use-translated"),
    H = document.getElementById("muxer-enabled"),
    K = document.getElementById("video-muxer-engine"),
    S = document.getElementById("hls-segment"),
    l = document.getElementById("hls-list"),
    m = document.getElementById("hls-encoder"),
    P = document.getElementById("hls-crf"),
    q = document.getElementById("hls-audio-offset"),
    Y = document.getElementById("hls-audio-codec"),
    Z = document.getElementById("hls-audio-bitrate"),
    O = e.input?.type || "srt";
  t && ((t.value = O), Zt());
  const b = document.getElementById("input-srt-port"),
    ae = document.getElementById("input-srt-mode"),
    ce = document.getElementById("input-srt-latency"),
    R = e.input?.srt;
  b && R?.listen_port && (b.value = String(R.listen_port)),
    ae && R?.mode && (ae.value = R.mode),
    ce && R?.latency_ms && (ce.value = String(R.latency_ms));
  const de = document.getElementById("input-chunk-duration"),
    me = document.getElementById("input-rtmp-chunk"),
    pe = document.getElementById("input-file-chunk"),
    X = e.pipeline?.chunk_duration_sec || E.CHUNK_DURATION;
  de && (de.value = String(R?.chunk_duration_sec || X));
  const N = e.input?.rtmp,
    U = e.input?.file;
  me && (me.value = String(N?.chunk_duration_sec || X));
  const ge = document.getElementById("input-rtmp-url"),
    fe = document.getElementById("input-rtmp-mode"),
    ye = document.getElementById("input-rtmp-app");
  ge && N?.url && (ge.value = N.url),
    fe && N?.mode && (fe.value = N.mode),
    ye && N?.app && (ye.value = N.app);
  const ve = document.getElementById("input-file-path"),
    Ee = document.getElementById("input-file-loop"),
    _e = document.getElementById("input-file-speed");
  ve && U?.path && (ve.value = U.path),
    Ee && U?.loop !== void 0 && (Ee.value = U.loop ? "true" : "false"),
    _e && U?.speed && (_e.value = String(U.speed)),
    pe && (pe.value = String(U?.chunk_duration_sec || X));
  const gt =
    e.output?.type === "web" ? "webplayer" : e.output?.type || "webplayer";
  if (
    (n && ((n.value = gt), Jt()),
    o && (o.checked = e.modules.transcriber.enabled),
    u && (u.value = e.modules.transcriber.model),
    i && (i.value = e.modules.transcriber.language),
    r && (r.value = e.modules.transcriber.device),
    d && (d.checked = e.modules.translator.enabled),
    a && (a.value = e.modules.translator.source_lang),
    c && (c.value = e.modules.translator.target_lang),
    _ && (_.checked = e.modules.tts_engine.enabled),
    p &&
      ((p.value = e.modules.tts_engine.engine || "edge-tts"),
      g && (g.style.display = p.value === "piper" ? "block" : "none"),
      W && j))
  ) {
    const Ne = p.value === "edge-tts";
    (W.style.display = Ne ? "block" : "none"),
      (j.style.display = Ne ? "none" : "block");
  }
  y && (y.value = e.modules.tts_engine.device || "auto"),
    C && (C.value = e.modules.tts_engine.voice || "es-ES-AlvaroNeural"),
    V && (V.value = e.modules.tts_engine.voice || "es_ES-sharvard-medium"),
    x && (x.value = String(e.modules.tts_engine.speed)),
    v && (v.checked = e.modules.subtitle_generator.enabled),
    T && (T.value = e.modules.subtitle_generator.format),
    z && (z.value = String(e.modules.subtitle_generator.use_translated)),
    H && (H.checked = e.modules.video_muxer.enabled),
    K && (K.value = e.modules.video_muxer.engine || "hls");
  const Ie = document.getElementById("audio-mixer-enabled");
  Ie && (Ie.checked = e.modules.audio_mixer?.enabled ?? !1);
  const he = document.getElementById("audio-mixer-original-volume");
  he && (he.value = String(e.modules.audio_mixer?.original_volume ?? 0.3));
  const be = document.getElementById("audio-mixer-original-value");
  be &&
    (be.textContent = String(e.modules.audio_mixer?.original_volume ?? 0.3));
  const Be = document.getElementById("audio-mixer-dubbed-volume");
  Be &&
    (Be.value = String(
      e.modules.audio_mixer?.tts_volume ??
        e.modules.audio_mixer?.dubbed_volume ??
        1,
    ));
  const xe = document.getElementById("audio-mixer-dubbed-value");
  xe &&
    (xe.textContent = String(
      e.modules.audio_mixer?.tts_volume ??
        e.modules.audio_mixer?.dubbed_volume ??
        1,
    )),
    S && (S.value = String(e.modules.video_muxer.hls_segment_duration)),
    l && (l.value = String(e.modules.video_muxer.hls_list_size)),
    m && (m.value = e.modules.video_muxer.encoder_mode),
    P && (P.value = String(e.modules.video_muxer.video_crf)),
    q && (q.value = String(e.modules.video_muxer.audio_offset_ms || 0)),
    Y && (Y.value = e.modules.video_muxer.audio_codec || "aac"),
    Z && (Z.value = e.modules.video_muxer.audio_bitrate || "192k");
  const Se = document.getElementById("webrtc-encoder"),
    Ce = document.getElementById("webrtc-video-codec"),
    ke = document.getElementById("webrtc-video-bitrate"),
    we = document.getElementById("webrtc-video-resolution"),
    Le = document.getElementById("webrtc-video-fps"),
    Te = document.getElementById("webrtc-audio-codec"),
    Pe = document.getElementById("webrtc-audio-bitrate"),
    Re = document.getElementById("webrtc-audio-sample-rate");
  Se && (Se.value = e.modules.video_muxer.encoder_mode || "auto"),
    Ce && (Ce.value = e.modules.video_muxer.video_codec || "h264"),
    ke && (ke.value = e.modules.video_muxer.video_bitrate || "1000k"),
    we &&
      e.modules.video_muxer.video_width &&
      e.modules.video_muxer.video_height &&
      (we.value = `${e.modules.video_muxer.video_width}x${e.modules.video_muxer.video_height}`),
    Le &&
      e.modules.video_muxer.video_fps &&
      (Le.value = String(e.modules.video_muxer.video_fps)),
    Te && (Te.value = e.modules.video_muxer.audio_codec || "opus"),
    Pe &&
      (Pe.value =
        e.modules.video_muxer.webrtc_audio_bitrate ||
        e.modules.video_muxer.audio_bitrate ||
        "64k"),
    Re &&
      e.modules.video_muxer.audio_sample_rate &&
      (Re.value = String(e.modules.video_muxer.audio_sample_rate));
}
function Zt() {
  const e = document.getElementById("input-type");
  e && (e.value = e.value);
}
function Jt() {
  const e = document.getElementById("output-type");
  e && (e.value = e.value);
}
let ct = !1;
function G(e, t = "") {
  (ct = e),
    document.body.classList.toggle("loading", e),
    e && t && f("INFO", `${t}...`);
}
function re() {
  return ct;
}
async function Qt() {
  if (!re()) {
    G(!0, "Iniciando pipeline");
    try {
      f("INFO", h.PIPELINE_STARTING), await ht();
      const e = await qe();
      $(e), pt(), f("INFO", h.PIPELINE_STARTED);
    } catch (e) {
      f("ERROR", `Error: ${e.message}`);
    } finally {
      G(!1);
    }
  }
}
async function Xt() {
  if (confirm(h.PIPELINE_CONFIRM_STOP) && !re()) {
    G(!0, "Deteniendo pipeline");
    try {
      f("INFO", h.PIPELINE_STOPPING), await bt();
      const e = await qe();
      $(e),
        He(),
        (J = !1),
        L && clearTimeout(L),
        ie(),
        f("INFO", h.PIPELINE_STOPPED);
    } catch (e) {
      f("ERROR", `Error: ${e.message}`);
    } finally {
      G(!1);
    }
  }
}
async function en() {
  if (!re()) {
    G(!0, "Guardando config");
    try {
      const e = Yt(),
        t = parseInt(
          document.getElementById("input-chunk-duration")?.value ||
            document.getElementById("input-rtmp-chunk")?.value ||
            document.getElementById("input-file-chunk")?.value ||
            String(E.CHUNK_DURATION),
        );
      await D("PUT", "/api/config", { config: e });
      try {
        await vt(t), f("INFO", `Chunk synced: ${t}s`);
      } catch (o) {
        f("WARNING", `Chunk sync failed: ${o.message}`);
      }
      const n = await Ke();
      (Q.value = n),
        at(n),
        I(h.CONFIG_SAVED, "success"),
        f("INFO", "Configuración guardada");
    } catch (e) {
      const t = e.message;
      I(`${h.CONFIG_SAVE_ERROR}: ${t}`, "error"),
        f("ERROR", `Error al guardar: ${t}`);
    } finally {
      G(!1);
    }
  }
}
async function Fe() {
  try {
    await D("POST", "input/control/play"), I(h.INPUT_FILE_PLAY, "success");
  } catch (e) {
    I(`Error al reproducir: ${e.message}`, "error");
  }
}
async function tn() {
  try {
    await D("POST", "input/control/pause"), I(h.INPUT_FILE_PAUSE, "success");
  } catch (e) {
    I(`Error al pausar: ${e.message}`, "error");
  }
}
async function $e(e) {
  try {
    await D("POST", "input/control/seek", { position: e });
  } catch (t) {
    I(`Error al buscar posición: ${t.message}`, "error");
  }
}
async function dt() {
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
let F = null;
function nn() {
  F && clearInterval(F);
  const e = document.getElementById("input-file-position"),
    t = document.getElementById("file-time-current"),
    n = document.getElementById("file-time-total"),
    o = document.getElementById("btn-file-play"),
    u = document.getElementById("btn-file-pause");
  F = setInterval(() => {
    dt().then((i) => {
      i &&
        (e &&
          i.duration > 0 &&
          (e.value = ((i.position / i.duration) * 100).toString()),
        t && (t.textContent = Ue(i.position)),
        n && (n.textContent = Ue(i.duration)),
        o &&
          u &&
          (i.is_playing
            ? ((o.style.display = "none"), (u.style.display = "inline"))
            : ((o.style.display = "inline"), (u.style.display = "none"))));
    });
  }, Ye.FILE_POLL);
}
function on() {
  F && (clearInterval(F), (F = null));
}
function sn() {
  const e = document.getElementById("btn-file-play"),
    t = document.getElementById("btn-file-pause"),
    n = document.getElementById("btn-file-restart"),
    o = document.getElementById("input-file-position");
  if (!e || !t || !n || !o) return;
  (e.style.display = "inline"),
    (t.style.display = "none"),
    e.addEventListener("click", () => {
      Fe().then(() => {
        (e.style.display = "none"), (t.style.display = "inline");
      });
    }),
    t.addEventListener("click", () => {
      tn().then(() => {
        (t.style.display = "none"), (e.style.display = "inline");
      });
    }),
    n.addEventListener("click", () => {
      $e(0).then(() => {
        (o.value = "0"),
          Fe().then(() => {
            (e.style.display = "none"), (t.style.display = "inline");
          });
      });
    });
  let u = null;
  o.addEventListener("input", () => {
    u && clearTimeout(u);
    const i = parseInt(o.value);
    u = setTimeout(() => {
      dt().then((r) => {
        r?.duration && $e((i / 100) * r.duration);
      });
    }, Ye.SEEK_DEBOUNCE);
  }),
    nn();
}
function un() {
  const e = document.getElementById("input-rtmp-url");
  if (!e) return;
  const t = document.getElementById("input-rtmp-port"),
    n = document.getElementById("input-rtmp-app"),
    o = document.getElementById("input-rtmp-key"),
    u = t?.value || "1935",
    i = n?.value || "live",
    r = o?.value || "stream";
  e.value = `rtmp://127.0.0.1:${u}/${i}/${r}`;
}
const ne = { RUNNING: 3e3, STOPPED: 1e4, POST_START: 1e3 },
  ln = 5e3;
let k = null,
  J = !1,
  L = null;
function rn() {
  const e = M.value?.state;
  return J ? ne.POST_START : e === "running" ? ne.RUNNING : ne.STOPPED;
}
function mt() {
  k && clearInterval(k);
  const e = async () => {
    try {
      const t = await D("GET", "api/status");
      $(t);
    } catch {}
  };
  e(), (k = setInterval(e, rn()));
}
function ie() {
  k && (clearInterval(k), (k = null)), mt();
}
function pt() {
  (J = !0),
    ie(),
    L && clearTimeout(L),
    (L = setTimeout(() => {
      (J = !1), ie();
    }, ln));
}
let w = null;
async function an() {
  xt(), f("INFO", h.LOADING);
  try {
    const e = await Ke();
    (Q.value = e), at(e);
    const t = document.getElementById("input-type");
    t?.value === "rtmp" && un(),
      t?.value === "file" &&
        document.getElementById("input-file-path")?.value &&
        sn();
    const n = await D("GET", "api/status");
    $(n), lt();
    const o = Et("/ws/logs"),
      u = _t();
    (w = new It(o, {
      maxReconnectAttempts: 5,
      backoffBase: 1e3,
      authToken: u,
    })),
      w.onMessage((i) => {
        i.type === "log"
          ? f(i.level ?? "INFO", i.message ?? "")
          : i.type === "status" &&
            i.status &&
            ($(i.status), i.status.state === "running" && !J && pt());
      }),
      w.onError(() => {
        f("ERROR", h.WS_ERROR);
      }),
      w.onClose((i) => {
        (le.value = !1),
          i
            ? f("WARNING", "WebSocket connection failed")
            : f("ERROR", h.WS_DISCONNECTED);
      }),
      w.connect(),
      mt(),
      f("INFO", h.SUCCESS);
  } catch (e) {
    f("ERROR", `Error de inicialización: ${e.message}`);
  }
}
function cn() {
  k && (clearInterval(k), (k = null)),
    L && (clearTimeout(L), (L = null)),
    w && (w.close(), (w = null)),
    rt(),
    on();
}
function dn() {
  document.getElementById("btn-start")?.addEventListener("click", Qt),
    document.getElementById("btn-stop")?.addEventListener("click", Xt),
    document.getElementById("tts-engine")?.addEventListener("change", (e) => {
      const t = e.target.value === "edge-tts",
        n = document.getElementById("tts-voice-edge-group"),
        o = document.getElementById("tts-voice-piper-group");
      n && (n.style.display = t ? "block" : "none"),
        o && (o.style.display = t ? "none" : "block");
    });
}
async function mn() {
  try {
    const n = (await (await fetch("/api/status")).json()).system || {},
      o = document.getElementById("metric-cpu-value"),
      u = document.getElementById("metric-cpu-bar"),
      i = document.getElementById("metric-memory-value"),
      r = document.getElementById("metric-memory-percent"),
      d = document.getElementById("metric-memory-bar"),
      a = document.getElementById("metric-gpu-value"),
      c = document.getElementById("metric-gpu-bar");
    o && (o.textContent = (n.cpu_percent || n.cpu_usage || 0) + "%"),
      u && (u.style.width = (n.cpu_percent || n.cpu_usage || 0) + "%"),
      i && (i.textContent = (n.memory_mb || 0).toFixed(0) + " MB"),
      r && (r.textContent = (n.memory_percent || n.memory_usage || 0) + "%"),
      d && (d.style.width = (n.memory_percent || n.memory_usage || 0) + "%"),
      a && (a.textContent = (n.gpu_usage || 0) + "%"),
      c && (c.style.width = (n.gpu_usage || 0) + "%");
  } catch (e) {
    console.error("Metrics refresh failed:", e);
  }
}
function pn() {
  document.getElementById("btn-copy-emision")?.addEventListener("click", () => {
    const e = document.getElementById("url-emision");
    e?.textContent &&
      ee(e.textContent)
        .then(() => I("URL de emisión copiada", "success"))
        .catch(() => I("Error al copiar URL", "error"));
  }),
    document
      .getElementById("btn-copy-stream")
      ?.addEventListener("click", () => {
        const e = document.getElementById("url-stream");
        e?.textContent &&
          ee(e.textContent)
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
            ee(t)
              .then(() => I("URL del player copiada", "success"))
              .catch(() => I("Error al copiar URL", "error"));
        }
      });
}
let Ge = !1;
function gn() {
  Ge ||
    ((Ge = !0),
    dn(),
    pn(),
    setTimeout(() => {
      an(), mn();
    }, 100));
}
window.addEventListener("beforeunload", cn);
window.saveConfig = en;
document.addEventListener("DOMContentLoaded", gn);
kt(
  async () => {
    const { initKeyboardShortcuts: e } = await import(
      "./keyboard-shortcuts.BUCgNMeb.js"
    );
    return { initKeyboardShortcuts: e };
  },
  __vite__mapDeps([0, 1]),
).then(({ initKeyboardShortcuts: e }) => {
  e();
});
export { kt as _, Xt as a, Qt as b, en as h, In as i };
