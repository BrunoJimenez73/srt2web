const __vite__mapDeps = (
  i,
  m = __vite__mapDeps,
  d = m.f ||
    (m.f = [
      "_astro/keyboard-shortcuts.DgyJLEf3.js",
      "_astro/store.CIQbH6Sf.js",
      "_astro/index.BpSbb1Lw.js",
    ]),
) => i.map((i) => d[i]);
import {
  D as y,
  a as R,
  u as Ze,
  b as Re,
  M as _,
  c as Je,
  W as Qe,
  I as j,
  d as Xe,
  e as Te,
  f as et,
} from "./api.CUNSBO6C.js";
import { s as f, c as $ } from "./index.BpSbb1Lw.js";
import { i as tt, f as Ce } from "./logpanel.Co3ahUsz.js";
import {
  j as b,
  p as M,
  a as Pe,
  s as nt,
  t as Ne,
  c as ot,
  w as Ue,
  b as it,
  d as st,
  e as z,
  f as v,
  u as A,
  r as ut,
} from "./store.CIQbH6Sf.js";
const lt = (function () {
    const t = typeof document < "u" && document.createElement("link").relList;
    return t && t.supports && t.supports("modulepreload")
      ? "modulepreload"
      : "preload";
  })(),
  rt = function (e) {
    return "/" + e;
  },
  we = {},
  Oe = function (t, n, i) {
    let o = Promise.resolve();
    if (n && n.length > 0) {
      let E = function (c) {
        return Promise.all(
          c.map((d) =>
            Promise.resolve(d).then(
              (r) => ({ status: "fulfilled", value: r }),
              (r) => ({ status: "rejected", reason: r }),
            ),
          ),
        );
      };
      document.getElementsByTagName("link");
      const l = document.querySelector("meta[property=csp-nonce]"),
        m = l?.nonce || l?.getAttribute("nonce");
      o = E(
        n.map((c) => {
          if (((c = rt(c)), c in we)) return;
          we[c] = !0;
          const d = c.endsWith(".css"),
            r = d ? '[rel="stylesheet"]' : "";
          if (document.querySelector(`link[href="${c}"]${r}`)) return;
          const p = document.createElement("link");
          if (
            ((p.rel = d ? "stylesheet" : lt),
            d || (p.as = "script"),
            (p.crossOrigin = ""),
            (p.href = c),
            m && p.setAttribute("nonce", m),
            document.head.appendChild(p),
            d)
          )
            return new Promise((B, h) => {
              p.addEventListener("load", B),
                p.addEventListener("error", () =>
                  h(new Error(`Unable to preload CSS for ${c}`)),
                );
            });
        }),
      );
    }
    function u(l) {
      const m = new Event("vite:preloadError", { cancelable: !0 });
      if (((m.payload = l), window.dispatchEvent(m), !m.defaultPrevented))
        throw l;
    }
    return o.then((l) => {
      for (const m of l || []) m.status === "rejected" && u(m.reason);
      return t().catch(u);
    });
  };
let ke = !1;
function at() {
  ke ||
    ((ke = !0),
    Le(),
    setInterval(() => {
      Le();
    }, 1e3));
}
function Le() {
  const e = document.getElementById("live-clock");
  e && (e.textContent = new Date().toLocaleTimeString("en-US", { hour12: !1 }));
}
var L = ((e) => (
  (e.STOPPED = "stopped"),
  (e.RUNNING = "running"),
  (e.STARTING = "starting"),
  (e.STOPPING = "stopping"),
  (e.ERROR = "error"),
  e
))(L || {});
function dt(e) {
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
function ct() {
  b(() => {
    const e = M.value,
      t = s("status-dot"),
      n = s("status-text");
    if (!t || !n) return;
    const i = dt(e?.state);
    t.classList.toggle("running", i === L.RUNNING),
      t.classList.toggle("error", i === L.ERROR),
      (n.textContent = i === L.RUNNING ? "ACTIVO" : "APAGADO");
    const o = s("btn-start"),
      u = s("btn-stop");
    if (o) {
      const l = i === L.RUNNING;
      (o.disabled = l), (o.style.opacity = l ? "0.5" : "1");
    }
    if (u) {
      const l = i === L.RUNNING;
      (u.disabled = !l), (u.style.opacity = l ? "1" : "0.5");
    }
  }),
    b(() => {
      const t = M.value?.modules ?? [],
        n = Pe.value,
        i = {
          srt_input: "indicator-input",
          rtmp_input: "indicator-input",
          file_input: "indicator-input",
          audio_extractor: "indicator-input",
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
      for (const o of t) {
        const u = i[o.name];
        if (!u) continue;
        const l = s(u);
        l && l.classList.toggle("active", n && o.enabled);
      }
    }),
    b(() => {
      const e = M.value,
        t = s("pipeline-indicator");
      t && t.classList.toggle("active", e?.state === "running");
    });
}
function D(e) {
  return e < 50 ? "low" : e < 80 ? "medium" : "high";
}
function mt() {
  b(() => {
    const e = nt.value,
      t = Ne.value,
      n = s("metric-cpu-bar"),
      i = s("metric-cpu-value");
    n &&
      ((n.style.width = `${e.cpu}%`),
      n.classList.remove("low", "medium", "high"),
      n.classList.add(D(e.cpu))),
      i && (i.textContent = `${e.cpu.toFixed(0)}%`);
    const o = s("metric-memory-bar"),
      u = s("metric-memory-value"),
      l = s("metric-memory-percent");
    o &&
      ((o.style.width = `${e.memoryPercent}%`),
      o.classList.remove("low", "medium", "high"),
      o.classList.add(D(e.memoryPercent))),
      u && (u.textContent = `${e.memoryMb.toFixed(0)} MB`),
      l && (l.textContent = `${e.memoryPercent.toFixed(0)}%`);
    const m = s("metric-gpu-bar"),
      E = s("metric-gpu-value"),
      c = s("metric-gpu-memory");
    m &&
      ((m.style.width = `${e.gpuUtil}%`),
      m.classList.remove("low", "medium", "high"),
      m.classList.add(D(e.gpuUtil))),
      E && (E.textContent = `${e.gpuUtil.toFixed(0)}%`),
      c &&
        (c.textContent =
          e.gpuMemMb > 0 ? `${e.gpuMemMb.toFixed(0)} MB` : "N/A");
    const d = s("metric-throughput-bar"),
      r = s("metric-throughput-value");
    d && (d.style.width = `${Math.min(t * 10, 100)}%`),
      r && (r.textContent = `${t.toFixed(2)}/s`);
  });
}
function pt() {
  b(() => {
    const e = M.value,
      t = e?.modules ?? [],
      n = Pe.value,
      i = Ne.value,
      o = Object.fromEntries(t.map((a) => [a.name, a]));
    for (const a of [
      "transcriber",
      "translator",
      "tts_engine",
      "subtitle_generator",
      "audio_mixer",
    ]) {
      const g = o[a],
        x = s(`module-time-${a}`),
        P = s(`module-chunks-${a}`),
        N = s(`module-memory-${a}`),
        U = s(`module-encoder-${a}`);
      if (x)
        if (g?.last_process_time_ms !== void 0 && g.last_process_time_ms > 0) {
          const I = g.last_process_time_ms;
          x.textContent =
            I < 1e3 ? `${Math.round(I)}ms` : `${(I / 1e3).toFixed(1)}s`;
        } else if (n && i > 0) {
          const I = (1e3 / i).toFixed(0);
          x.textContent = `${I}ms`;
        } else x.textContent = "--";
      if (
        (P && (P.textContent = String(g?.processed_chunks ?? 0)),
        N &&
          (N.textContent =
            g?.memory_mb !== void 0 ? `${Math.round(g.memory_mb)} MB` : "--"),
        U && g?.extra)
      ) {
        const I = g.extra.encoder_label || (g.extra.using_gpu ? "GPU" : "CPU");
        U.textContent = I;
      }
      const S = s(`gpu-badge-${a}`);
      if (S && g?.extra) {
        const I = n && g.enabled && (g.processed_chunks ?? 0) > 0;
        g.extra.using_gpu
          ? ((S.style.display = "inline"), S.classList.toggle("active", I))
          : (S.style.display = "none");
      }
    }
    const u = s("module-time-video_muxer"),
      l = s("module-memory-video_muxer"),
      m = s("module-chunks-video_muxer"),
      E = s("module-encoder-video_muxer"),
      c = s("gpu-badge-video_muxer"),
      d = o.video_muxer ?? o.output;
    if (u)
      if (d?.last_process_time_ms !== void 0 && d.last_process_time_ms > 0) {
        const a = d.last_process_time_ms;
        u.textContent =
          a < 1e3 ? `${Math.round(a)}ms` : `${(a / 1e3).toFixed(1)}s`;
      } else
        n && i > 0
          ? (u.textContent = `${(1e3 / i).toFixed(0)}ms`)
          : (u.textContent = "--");
    if (
      (l &&
        (l.textContent =
          d?.memory_mb !== void 0 ? `${Math.round(d.memory_mb)} MB` : "--"),
      m &&
        (m.textContent = String(
          d?.processed_chunks ?? e?.chunks_processed ?? 0,
        )),
      E)
    ) {
      const a =
        d?.extra?.encoder_label ?? (d?.extra?.using_gpu ? "GPU" : "CPU");
      E.textContent = a;
    }
    if (c && d?.extra) {
      const a = n && d.enabled && (d.processed_chunks ?? 0) > 0;
      d.extra.using_gpu
        ? ((c.style.display = "inline"), c.classList.toggle("active", a))
        : (c.style.display = "none");
    }
    const r =
        o.srt_input ??
        o.rtmp_input ??
        o.file_input ??
        o.audio_extractor ??
        o.input,
      p = s("module-time-input"),
      B = s("module-chunks-input"),
      h = s("gpu-badge-input"),
      T = s("module-encoder-input");
    if (p)
      if (r?.last_process_time_ms !== void 0 && r.last_process_time_ms > 0) {
        const a = r.last_process_time_ms;
        p.textContent =
          a < 1e3 ? `${Math.round(a)}ms` : `${(a / 1e3).toFixed(1)}s`;
      } else
        n && i > 0
          ? (p.textContent = `${(1e3 / i).toFixed(0)}ms`)
          : r?.enabled
            ? r?.state === "error"
              ? ((p.textContent = "ERROR"), (p.style.color = "var(--error)"))
              : (p.textContent = "IDLE")
            : (p.textContent = "--");
    if ((B && r && (B.textContent = String(r.processed_chunks ?? 0)), h && r)) {
      const a = r.extra?.using_gpu === !0,
        g = n && (r.processed_chunks ?? 0) > 0;
      r.enabled && a
        ? ((h.style.display = "inline"),
          h.classList.toggle("active", g),
          (h.textContent = "GPU"))
        : (h.style.display = "none");
    }
    if (T && r) {
      const a = r.extra?.encoder_label || (r.extra?.using_gpu ? "GPU" : "CPU");
      T.textContent = a;
    }
  });
}
function gt() {
  b(() => {
    const e = ot.value,
      t = s("url-emision-label"),
      n = s("url-emision"),
      i = s("url-stream"),
      o = s("url-player");
    t && (t.textContent = e.primaryLabel),
      n && (n.textContent = e.primaryUrl),
      i && (i.textContent = e.streamUrl),
      o && ((o.textContent = e.playerUrl), (o.href = e.playerUrl));
  });
}
function yt() {
  b(() => {
    const e = Ue.value,
      t = s("ws-status-badge");
    t &&
      ((t.textContent = e ? "WS ON" : "WS OFF"),
      t.classList.toggle("active", e));
  });
}
function vt() {
  b(() => {
    M.value;
    const e = s("live-clock");
    e &&
      (e.textContent = new Date().toLocaleTimeString("en-US", { hour12: !1 }));
  }),
    at();
}
function Et() {
  b(() => {
    const e = it.value,
      t = s("remote-config"),
      n = s("btn-mode-local"),
      i = s("btn-mode-remote");
    t && (t.style.display = e === "remote" ? "" : "none"),
      n && n.classList.toggle("active", e === "local"),
      i && i.classList.toggle("active", e === "remote");
  });
}
function ft() {
  b(() => {
    st.value, z.value;
  });
}
function _t() {
  ct(), mt(), pt(), gt(), yt(), vt(), Et(), ft();
}
function Me() {
  const e = document.getElementById("input-type")?.value || "srt";
  document.getElementById("output-type")?.value;
  const t = parseInt(
      document.getElementById("input-chunk-duration")?.value ||
        document.getElementById("input-rtmp-chunk")?.value ||
        document.getElementById("input-file-chunk")?.value ||
        String(y.CHUNK_DURATION),
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
              String(y.TTS_SPEED),
          ),
          chunk_duration_sec: t,
        });
  const i = {
    audio_extractor: { enabled: !0 },
    transcriber: {
      enabled: document.getElementById("whisper-enabled")?.checked ?? !0,
      model: document.getElementById("whisper-model")?.value || y.WHISPER_MODEL,
      language:
        document.getElementById("whisper-lang")?.value || y.WHISPER_LANGUAGE,
      device: document.getElementById("whisper-device")?.value || "auto",
      beam_size: 2,
    },
    translator: {
      enabled: document.getElementById("translator-enabled")?.checked ?? !0,
      source_lang:
        document.getElementById("translator-source")?.value ||
        y.WHISPER_LANGUAGE,
      target_lang:
        document.getElementById("translator-target")?.value ||
        y.TRANSLATE_TARGET,
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
        document.getElementById("tts-speed")?.value || String(y.TTS_SPEED),
      ),
      device: document.getElementById("tts-device")?.value || "auto",
    },
    subtitle_generator: {
      enabled: document.getElementById("subtitle-enabled")?.checked ?? !0,
      format:
        document.getElementById("subtitle-format")?.value || y.SUBTITLE_FORMAT,
      use_translated:
        document.getElementById("subtitle-use-translated")?.value === "true",
      chunk_duration: t,
    },
    audio_mixer: {
      enabled: document.getElementById("audio-mixer-enabled")?.checked ?? !1,
      original_volume: parseFloat(
        document.getElementById("audio-mixer-original-volume")?.value ||
          String(y.ORIGINAL_VOLUME),
      ),
      tts_volume: parseFloat(
        document.getElementById("audio-mixer-dubbed-volume")?.value ||
          String(y.TTS_VOLUME),
      ),
      dubbed_volume: parseFloat(
        document.getElementById("audio-mixer-dubbed-volume")?.value ||
          String(y.TTS_VOLUME),
      ),
    },
    video_muxer: {
      enabled: document.getElementById("muxer-enabled")?.checked ?? !0,
      engine: document.getElementById("video-muxer-engine")?.value || "hls",
      hls_segment_duration: parseInt(
        document.getElementById("hls-segment")?.value ||
          String(y.SEGMENT_DURATION),
      ),
      hls_list_size: parseInt(
        document.getElementById("hls-list")?.value || String(y.LIST_SIZE),
      ),
      audio_offset_ms: parseInt(
        document.getElementById("hls-audio-offset")?.value ||
          String(y.AUDIO_OFFSET),
      ),
      encoder_mode: document.getElementById("hls-encoder")?.value || "auto",
      video_quality: "medium",
      video_crf: parseInt(
        document.getElementById("hls-crf")?.value || String(y.CRF),
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
        const o = document.getElementById("webrtc-video-resolution");
        if (o?.value) {
          const [u, l] = o.value.split("x").map(Number);
          return { video_width: u, video_height: l };
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
      retry_delay: 1e3,
    },
    modules: i,
  };
}
function H(e) {
  const t = document.getElementById("input-type"),
    n = document.getElementById("output-type"),
    i = document.getElementById("whisper-enabled"),
    o = document.getElementById("whisper-model"),
    u = document.getElementById("whisper-lang"),
    l = document.getElementById("whisper-device"),
    m = document.getElementById("translator-enabled"),
    E = document.getElementById("translator-source"),
    c = document.getElementById("translator-target"),
    d = document.getElementById("tts-enabled"),
    r = document.getElementById("tts-engine"),
    p = document.getElementById("tts-device"),
    B = document.getElementById("tts-device-group"),
    h = document.getElementById("tts-voice-edge"),
    T = document.getElementById("tts-voice-piper"),
    a = document.getElementById("tts-voice-edge-group"),
    g = document.getElementById("tts-voice-piper-group"),
    x = document.getElementById("tts-speed"),
    P = document.getElementById("subtitle-enabled"),
    N = document.getElementById("subtitle-format"),
    U = document.getElementById("subtitle-use-translated"),
    S = document.getElementById("muxer-enabled"),
    I = document.getElementById("video-muxer-engine"),
    K = document.getElementById("hls-segment"),
    q = document.getElementById("hls-list"),
    Y = document.getElementById("hls-encoder"),
    Z = document.getElementById("hls-crf"),
    J = document.getElementById("hls-audio-offset"),
    Q = document.getElementById("hls-audio-codec"),
    X = document.getElementById("hls-audio-bitrate"),
    qe = e.input?.type || "srt";
  t && ((t.value = qe), It());
  const ee = document.getElementById("input-srt-port"),
    te = document.getElementById("input-srt-mode"),
    ne = document.getElementById("input-srt-latency"),
    C = e.input?.srt;
  ee && C?.listen_port && (ee.value = String(C.listen_port)),
    te && C?.mode && (te.value = C.mode),
    ne && C?.latency_ms && (ne.value = String(C.latency_ms));
  const oe = document.getElementById("input-chunk-duration"),
    ie = document.getElementById("input-rtmp-chunk"),
    se = document.getElementById("input-file-chunk"),
    F = e.pipeline?.chunk_duration_sec || y.CHUNK_DURATION;
  oe && (oe.value = String(C?.chunk_duration_sec || F));
  const w = e.input?.rtmp,
    k = e.input?.file;
  ie && (ie.value = String(w?.chunk_duration_sec || F));
  const ue = document.getElementById("input-rtmp-url"),
    le = document.getElementById("input-rtmp-mode"),
    re = document.getElementById("input-rtmp-app");
  ue && w?.url && (ue.value = w.url),
    le && w?.mode && (le.value = w.mode),
    re && w?.app && (re.value = w.app);
  const ae = document.getElementById("input-file-path"),
    de = document.getElementById("input-file-loop"),
    ce = document.getElementById("input-file-speed");
  ae && k?.path && (ae.value = k.path),
    de && k?.loop !== void 0 && (de.value = k.loop ? "true" : "false"),
    ce && k?.speed && (ce.value = String(k.speed)),
    se && (se.value = String(k?.chunk_duration_sec || F));
  const Ye =
    e.output?.type === "web" ? "webplayer" : e.output?.type || "webplayer";
  if (
    (n && ((n.value = Ye), ht()),
    i && (i.checked = e.modules.transcriber.enabled),
    o && (o.value = e.modules.transcriber.model),
    u && (u.value = e.modules.transcriber.language),
    l && (l.value = e.modules.transcriber.device),
    m && (m.checked = e.modules.translator.enabled),
    E && (E.value = e.modules.translator.source_lang),
    c && (c.value = e.modules.translator.target_lang),
    d && (d.checked = e.modules.tts_engine.enabled),
    r &&
      ((r.value = e.modules.tts_engine.engine || "edge-tts"),
      B && (B.style.display = r.value === "piper" ? "block" : "none"),
      a && g))
  ) {
    const Se = r.value === "edge-tts";
    (a.style.display = Se ? "block" : "none"),
      (g.style.display = Se ? "none" : "block");
  }
  p && (p.value = e.modules.tts_engine.device || "auto"),
    h && (h.value = e.modules.tts_engine.voice || "es-ES-AlvaroNeural"),
    T && (T.value = e.modules.tts_engine.voice || "es_ES-sharvard-medium"),
    x && (x.value = String(e.modules.tts_engine.speed)),
    P && (P.checked = e.modules.subtitle_generator.enabled),
    N && (N.value = e.modules.subtitle_generator.format),
    U && (U.value = String(e.modules.subtitle_generator.use_translated)),
    S && (S.checked = e.modules.video_muxer.enabled),
    I && (I.value = e.modules.video_muxer.engine || "hls");
  const me = document.getElementById("audio-mixer-enabled");
  me && (me.checked = e.modules.audio_mixer?.enabled ?? !1);
  const pe = document.getElementById("audio-mixer-original-volume");
  pe && (pe.value = String(e.modules.audio_mixer?.original_volume ?? 0.3));
  const ge = document.getElementById("audio-mixer-original-value");
  ge &&
    (ge.textContent = String(e.modules.audio_mixer?.original_volume ?? 0.3));
  const ye = document.getElementById("audio-mixer-dubbed-volume");
  ye &&
    (ye.value = String(
      e.modules.audio_mixer?.tts_volume ??
        e.modules.audio_mixer?.dubbed_volume ??
        1,
    ));
  const ve = document.getElementById("audio-mixer-dubbed-value");
  ve &&
    (ve.textContent = String(
      e.modules.audio_mixer?.tts_volume ??
        e.modules.audio_mixer?.dubbed_volume ??
        1,
    )),
    K && (K.value = String(e.modules.video_muxer.hls_segment_duration)),
    q && (q.value = String(e.modules.video_muxer.hls_list_size)),
    Y && (Y.value = e.modules.video_muxer.encoder_mode),
    Z && (Z.value = String(e.modules.video_muxer.video_crf)),
    J && (J.value = String(e.modules.video_muxer.audio_offset_ms || 0)),
    Q && (Q.value = e.modules.video_muxer.audio_codec || "aac"),
    X && (X.value = e.modules.video_muxer.audio_bitrate || "192k");
  const Ee = document.getElementById("webrtc-encoder"),
    fe = document.getElementById("webrtc-video-codec"),
    _e = document.getElementById("webrtc-video-bitrate"),
    Ie = document.getElementById("webrtc-video-resolution"),
    he = document.getElementById("webrtc-video-fps"),
    be = document.getElementById("webrtc-audio-codec"),
    Be = document.getElementById("webrtc-audio-bitrate"),
    xe = document.getElementById("webrtc-audio-sample-rate");
  Ee && (Ee.value = e.modules.video_muxer.encoder_mode || "auto"),
    fe && (fe.value = e.modules.video_muxer.video_codec || "h264"),
    _e && (_e.value = e.modules.video_muxer.video_bitrate || "1000k"),
    Ie &&
      e.modules.video_muxer.video_width &&
      e.modules.video_muxer.video_height &&
      (Ie.value = `${e.modules.video_muxer.video_width}x${e.modules.video_muxer.video_height}`),
    he &&
      e.modules.video_muxer.video_fps &&
      (he.value = String(e.modules.video_muxer.video_fps)),
    be && (be.value = e.modules.video_muxer.audio_codec || "opus"),
    Be &&
      (Be.value =
        e.modules.video_muxer.webrtc_audio_bitrate ||
        e.modules.video_muxer.audio_bitrate ||
        "64k"),
    xe &&
      e.modules.video_muxer.audio_sample_rate &&
      (xe.value = String(e.modules.video_muxer.audio_sample_rate));
}
function It() {
  const e = document.getElementById("input-type");
  e && (e.value = e.value);
}
function ht() {
  const e = document.getElementById("output-type");
  e && (e.value = e.value);
}
async function Ae() {
  try {
    v("INFO", _.PIPELINE_STARTING), await Xe();
    const e = await Te();
    A(e), v("INFO", _.PIPELINE_STARTED);
  } catch (e) {
    v("ERROR", `Error: ${e.message}`);
  }
}
async function Fe() {
  if (confirm(_.PIPELINE_CONFIRM_STOP))
    try {
      v("INFO", _.PIPELINE_STOPPING), await et();
      const e = await Te();
      A(e), ut(), v("INFO", _.PIPELINE_STOPPED);
    } catch (e) {
      v("ERROR", `Error: ${e.message}`);
    }
}
async function $e() {
  try {
    const e = Me(),
      t = parseInt(
        document.getElementById("input-chunk-duration")?.value ||
          document.getElementById("input-rtmp-chunk")?.value ||
          document.getElementById("input-file-chunk")?.value ||
          String(y.CHUNK_DURATION),
      );
    await R("PUT", "/api/config", { config: e });
    try {
      await Ze(t), v("INFO", `Chunk synced: ${t}s`);
    } catch (i) {
      v("WARNING", `Chunk sync failed: ${i.message}`);
    }
    const n = await Re();
    (z.value = n),
      H(n),
      f(_.CONFIG_SAVED, "success"),
      v("INFO", "Configuración guardada");
  } catch (e) {
    const t = e.message;
    f(`${_.CONFIG_SAVE_ERROR}: ${t}`, "error"),
      v("ERROR", `Error al guardar: ${t}`);
  }
}
async function V() {
  try {
    await R("POST", "input/control/play"), f(_.INPUT_FILE_PLAY, "success");
  } catch (e) {
    f(`Error al reproducir: ${e.message}`, "error");
  }
}
async function De() {
  try {
    await R("POST", "input/control/pause"), f(_.INPUT_FILE_PAUSE, "success");
  } catch (e) {
    f(`Error al pausar: ${e.message}`, "error");
  }
}
async function W(e) {
  try {
    await R("POST", "input/control/seek", { position: e });
  } catch (t) {
    f(`Error al buscar posición: ${t.message}`, "error");
  }
}
async function Ge() {
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
let G = null;
function bt() {
  G && clearInterval(G);
  const e = document.getElementById("input-file-position"),
    t = document.getElementById("file-time-current"),
    n = document.getElementById("file-time-total"),
    i = document.getElementById("btn-file-play"),
    o = document.getElementById("btn-file-pause");
  G = setInterval(() => {
    Ge().then((u) => {
      u &&
        (e &&
          u.duration > 0 &&
          (e.value = ((u.position / u.duration) * 100).toString()),
        t && (t.textContent = Ce(u.position)),
        n && (n.textContent = Ce(u.duration)),
        i &&
          o &&
          (u.is_playing
            ? ((i.style.display = "none"), (o.style.display = "inline"))
            : ((i.style.display = "inline"), (o.style.display = "none"))));
    });
  }, j.FILE_POLL);
}
function Ve() {
  const e = document.getElementById("btn-file-play"),
    t = document.getElementById("btn-file-pause"),
    n = document.getElementById("btn-file-restart"),
    i = document.getElementById("input-file-position");
  if (!e || !t || !n || !i) return;
  (e.style.display = "inline"),
    (t.style.display = "none"),
    e.addEventListener("click", () => {
      V().then(() => {
        (e.style.display = "none"), (t.style.display = "inline");
      });
    }),
    t.addEventListener("click", () => {
      De().then(() => {
        (t.style.display = "none"), (e.style.display = "inline");
      });
    }),
    n.addEventListener("click", () => {
      W(0).then(() => {
        (i.value = "0"),
          V().then(() => {
            (e.style.display = "none"), (t.style.display = "inline");
          });
      });
    });
  let o = null;
  i.addEventListener("input", () => {
    o && clearTimeout(o);
    const u = parseInt(i.value);
    o = setTimeout(() => {
      Ge().then((l) => {
        l?.duration && W((u / 100) * l.duration);
      });
    }, j.SEEK_DEBOUNCE);
  }),
    bt();
}
function We() {
  const e = document.getElementById("input-rtmp-url");
  if (!e) return;
  const t = document.getElementById("input-rtmp-port"),
    n = document.getElementById("input-rtmp-app"),
    i = document.getElementById("input-rtmp-key"),
    o = t?.value || "1935",
    u = n?.value || "live",
    l = i?.value || "stream";
  e.value = `rtmp://127.0.0.1:${o}/${u}/${l}`;
}
let O = null,
  Bt = null;
async function je() {
  tt(), v("INFO", _.LOADING);
  try {
    const e = await Re();
    (z.value = e), H(e);
    const t = document.getElementById("input-type");
    t?.value === "rtmp" && We(),
      t?.value === "file" &&
        document.getElementById("input-file-path")?.value &&
        Ve();
    const n = await R("GET", "api/status");
    A(n), _t();
    const i = Je("/ws/logs");
    (O = new Qe(i)),
      O.onMessage((o) => {
        o.type === "log"
          ? v(o.level ?? "INFO", o.message ?? "")
          : o.type === "status" && o.status && A(o.status);
      }),
      O.onError(() => {
        v("ERROR", _.WS_ERROR);
      }),
      O.onClose(() => {
        (Ue.value = !1), v("ERROR", _.WS_DISCONNECTED);
      }),
      O.connect(),
      (Bt = setInterval(async () => {
        try {
          const o = await R("GET", "api/status");
          A(o);
        } catch {}
      }, j.STATUS_POLL)),
      v("INFO", _.SUCCESS);
  } catch (e) {
    v("ERROR", `Error de inicialización: ${e.message}`);
  }
}
function ze() {
  document.getElementById("btn-start")?.addEventListener("click", Ae),
    document.getElementById("btn-stop")?.addEventListener("click", Fe),
    document.getElementById("tts-engine")?.addEventListener("change", (e) => {
      const t = e.target.value === "edge-tts",
        n = document.getElementById("tts-voice-edge-group"),
        i = document.getElementById("tts-voice-piper-group");
      n && (n.style.display = t ? "block" : "none"),
        i && (i.style.display = t ? "none" : "block");
    });
}
async function He() {
  try {
    const n = (await (await fetch("/api/status")).json()).system || {},
      i = document.getElementById("metric-cpu-value"),
      o = document.getElementById("metric-cpu-bar"),
      u = document.getElementById("metric-memory-value"),
      l = document.getElementById("metric-memory-percent"),
      m = document.getElementById("metric-memory-bar"),
      E = document.getElementById("metric-gpu-value"),
      c = document.getElementById("metric-gpu-bar");
    i && (i.textContent = (n.cpu_percent || n.cpu_usage || 0) + "%"),
      o && (o.style.width = (n.cpu_percent || n.cpu_usage || 0) + "%"),
      u && (u.textContent = (n.memory_mb || 0).toFixed(0) + " MB"),
      l && (l.textContent = (n.memory_percent || n.memory_usage || 0) + "%"),
      m && (m.style.width = (n.memory_percent || n.memory_usage || 0) + "%"),
      E && (E.textContent = (n.gpu_usage || 0) + "%"),
      c && (c.style.width = (n.gpu_usage || 0) + "%");
  } catch (e) {
    console.error("Metrics refresh failed:", e);
  }
}
function xt() {
  document.getElementById("btn-copy-emision")?.addEventListener("click", () => {
    const e = document.getElementById("url-emision");
    e?.textContent &&
      $(e.textContent)
        .then(() => f("URL de emisión copiada", "success"))
        .catch(() => f("Error al copiar URL", "error"));
  }),
    document
      .getElementById("btn-copy-stream")
      ?.addEventListener("click", () => {
        const e = document.getElementById("url-stream");
        e?.textContent &&
          $(e.textContent)
            .then(() => f("URL del stream copiada", "success"))
            .catch(() => f("Error al copiar URL", "error"));
      }),
    document
      .getElementById("btn-copy-player")
      ?.addEventListener("click", () => {
        const e = document.getElementById("url-player");
        if (e) {
          const t = e.getAttribute("href") || e.textContent;
          t &&
            $(t)
              .then(() => f("URL del player copiada", "success"))
              .catch(() => f("Error al copiar URL", "error"));
        }
      });
}
function Ke() {
  ze(),
    xt(),
    setTimeout(() => {
      je(), He();
    }, 100);
}
window.saveConfig = $e;
const St = Object.freeze(
  Object.defineProperty(
    {
      __proto__: null,
      applyConfigToUI: H,
      bootstrap: Ke,
      collectConfigFromUI: Me,
      fileInputPause: De,
      fileInputPlay: V,
      fileInputSeek: W,
      handleSaveConfig: $e,
      handleStart: Ae,
      handleStop: Fe,
      initDashboard: je,
      refreshMetrics: He,
      setupEventListeners: ze,
      setupFilePlayerControls: Ve,
      updateRtmpUrl: We,
    },
    Symbol.toStringTag,
    { value: "Module" },
  ),
);
document.addEventListener("DOMContentLoaded", Ke);
document.addEventListener("load", () => {
  setTimeout(() => {
    Oe(
      async () => {
        const { initDashboard: e, refreshMetrics: t } =
          await Promise.resolve().then(() => St);
        return { initDashboard: e, refreshMetrics: t };
      },
      void 0,
    ).then(({ initDashboard: e, refreshMetrics: t }) => {
      e(), t();
    });
  }, 500);
});
Oe(
  async () => {
    const { initKeyboardShortcuts: e } = await import(
      "./keyboard-shortcuts.DgyJLEf3.js"
    );
    return { initKeyboardShortcuts: e };
  },
  __vite__mapDeps([0, 1, 2]),
).then(({ initKeyboardShortcuts: e }) => {
  e();
});
export { Oe as _, Fe as a, Ae as b, $e as h, _t as s };
