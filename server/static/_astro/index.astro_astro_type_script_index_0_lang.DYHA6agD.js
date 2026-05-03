const __vite__mapDeps = (
  i,
  m = __vite__mapDeps,
  d = m.f ||
    (m.f = [
      "_astro/keyboard-shortcuts.DWUtHfJE.js",
      "_astro/store.CIQbH6Sf.js",
      "_astro/index.BpSbb1Lw.js",
    ]),
) => i.map((i) => d[i]);
import {
  D as g,
  a as L,
  u as Ze,
  b as Re,
  M as _,
  c as Je,
  W as Qe,
  I as G,
  d as Xe,
  e as Te,
  f as et,
} from "./api.CUNSBO6C.js";
import { s as f, c as A } from "./index.BpSbb1Lw.js";
import { i as tt, f as Ce } from "./logpanel.Co3ahUsz.js";
import {
  j as h,
  p as N,
  a as Pe,
  s as nt,
  t as Ne,
  c as ot,
  w as Ue,
  b as it,
  d as st,
  e as V,
  f as E,
  u as U,
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
      let m = function (r) {
        return Promise.all(
          r.map((c) =>
            Promise.resolve(c).then(
              (y) => ({ status: "fulfilled", value: y }),
              (y) => ({ status: "rejected", reason: y }),
            ),
          ),
        );
      };
      document.getElementsByTagName("link");
      const l = document.querySelector("meta[property=csp-nonce]"),
        d = l?.nonce || l?.getAttribute("nonce");
      o = m(
        n.map((r) => {
          if (((r = rt(r)), r in we)) return;
          we[r] = !0;
          const c = r.endsWith(".css"),
            y = c ? '[rel="stylesheet"]' : "";
          if (document.querySelector(`link[href="${r}"]${y}`)) return;
          const p = document.createElement("link");
          if (
            ((p.rel = c ? "stylesheet" : lt),
            c || (p.as = "script"),
            (p.crossOrigin = ""),
            (p.href = r),
            d && p.setAttribute("nonce", d),
            document.head.appendChild(p),
            c)
          )
            return new Promise((b, a) => {
              p.addEventListener("load", b),
                p.addEventListener("error", () =>
                  a(new Error(`Unable to preload CSS for ${r}`)),
                );
            });
        }),
      );
    }
    function s(l) {
      const d = new Event("vite:preloadError", { cancelable: !0 });
      if (((d.payload = l), window.dispatchEvent(d), !d.defaultPrevented))
        throw l;
    }
    return o.then((l) => {
      for (const d of l || []) d.status === "rejected" && s(d.reason);
      return t().catch(s);
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
var k = ((e) => (
  (e.STOPPED = "stopped"),
  (e.RUNNING = "running"),
  (e.STARTING = "starting"),
  (e.STOPPING = "stopping"),
  (e.ERROR = "error"),
  e
))(k || {});
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
function u(e) {
  return document.getElementById(e);
}
function ct() {
  h(() => {
    const e = N.value,
      t = u("status-dot"),
      n = u("status-text");
    if (!t || !n) return;
    const i = dt(e?.state);
    t.classList.toggle("running", i === k.RUNNING),
      t.classList.toggle("error", i === k.ERROR),
      (n.textContent = i === k.RUNNING ? "ACTIVO" : "APAGADO");
    const o = u("btn-start"),
      s = u("btn-stop");
    if (o) {
      const l = i === k.RUNNING;
      (o.disabled = l), (o.style.opacity = l ? "0.5" : "1");
    }
    if (s) {
      const l = i === k.RUNNING;
      (s.disabled = !l), (s.style.opacity = l ? "1" : "0.5");
    }
  }),
    h(() => {
      const t = N.value?.modules ?? [],
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
        const s = i[o.name];
        if (!s) continue;
        const l = u(s);
        l && l.classList.toggle("active", n && o.enabled);
      }
    }),
    h(() => {
      const e = N.value,
        t = u("pipeline-indicator");
      t && t.classList.toggle("active", e?.state === "running");
    });
}
function F(e) {
  return e < 50 ? "low" : e < 80 ? "medium" : "high";
}
function mt() {
  h(() => {
    const e = nt.value,
      t = Ne.value,
      n = u("metric-cpu-bar"),
      i = u("metric-cpu-value");
    n &&
      ((n.style.width = `${e.cpu}%`),
      n.classList.remove("low", "medium", "high"),
      n.classList.add(F(e.cpu))),
      i && (i.textContent = `${e.cpu.toFixed(0)}%`);
    const o = u("metric-memory-bar"),
      s = u("metric-memory-value"),
      l = u("metric-memory-percent");
    o &&
      ((o.style.width = `${e.memoryPercent}%`),
      o.classList.remove("low", "medium", "high"),
      o.classList.add(F(e.memoryPercent))),
      s && (s.textContent = `${e.memoryMb.toFixed(0)} MB`),
      l && (l.textContent = `${e.memoryPercent.toFixed(0)}%`);
    const d = u("metric-gpu-bar"),
      m = u("metric-gpu-value"),
      r = u("metric-gpu-memory");
    d &&
      ((d.style.width = `${e.gpuUtil}%`),
      d.classList.remove("low", "medium", "high"),
      d.classList.add(F(e.gpuUtil))),
      m && (m.textContent = `${e.gpuUtil.toFixed(0)}%`),
      r &&
        (r.textContent =
          e.gpuMemMb > 0 ? `${e.gpuMemMb.toFixed(0)} MB` : "N/A");
    const c = u("metric-throughput-bar"),
      y = u("metric-throughput-value");
    c && (c.style.width = `${Math.min(t * 10, 100)}%`),
      y && (y.textContent = `${t.toFixed(2)}/s`);
  });
}
function pt() {
  h(() => {
    const e = N.value,
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
      const v = o[a],
        B = u(`module-time-${a}`),
        R = u(`module-chunks-${a}`),
        T = u(`module-encoder-${a}`);
      if (B)
        if (v?.last_process_time_ms !== void 0 && v.last_process_time_ms > 0) {
          const I = v.last_process_time_ms;
          B.textContent =
            I < 1e3 ? `${Math.round(I)}ms` : `${(I / 1e3).toFixed(1)}s`;
        } else if (n && i > 0) {
          const I = (1e3 / i).toFixed(0);
          B.textContent = `${I}ms`;
        } else B.textContent = "--";
      if (
        (R && (R.textContent = String(v?.processed_chunks ?? 0)), T && v?.extra)
      ) {
        const I = v.extra.encoder_label || (v.extra.using_gpu ? "GPU" : "CPU");
        T.textContent = I;
      }
      const x = u(`gpu-badge-${a}`);
      if (x && v?.extra) {
        const I = n && v.enabled && (v.processed_chunks ?? 0) > 0;
        v.extra.using_gpu
          ? ((x.style.display = "inline"), x.classList.toggle("active", I))
          : (x.style.display = "none");
      }
    }
    const s = u("module-time-video_muxer"),
      l = u("module-chunks-video_muxer"),
      d = u("module-encoder-video_muxer"),
      m = o.video_muxer ?? o.output;
    if (s)
      if (m?.last_process_time_ms !== void 0 && m.last_process_time_ms > 0) {
        const a = m.last_process_time_ms;
        s.textContent =
          a < 1e3 ? `${Math.round(a)}ms` : `${(a / 1e3).toFixed(1)}s`;
      } else
        n && i > 0
          ? (s.textContent = `${(1e3 / i).toFixed(0)}ms`)
          : (s.textContent = "--");
    if (
      (l &&
        (l.textContent = String(
          m?.processed_chunks ?? e?.chunks_processed ?? 0,
        )),
      d)
    ) {
      const a =
        m?.extra?.encoder_label ?? (m?.extra?.using_gpu ? "GPU" : "CPU");
      d.textContent = a;
    }
    const r =
        o.srt_input ??
        o.rtmp_input ??
        o.file_input ??
        o.audio_extractor ??
        o.input,
      c = u("module-time-input"),
      y = u("module-chunks-input"),
      p = u("gpu-badge-input"),
      b = u("module-encoder-input");
    if (c)
      if (r?.last_process_time_ms !== void 0 && r.last_process_time_ms > 0) {
        const a = r.last_process_time_ms;
        c.textContent =
          a < 1e3 ? `${Math.round(a)}ms` : `${(a / 1e3).toFixed(1)}s`;
      } else
        n && i > 0
          ? (c.textContent = `${(1e3 / i).toFixed(0)}ms`)
          : r?.enabled
            ? r?.state === "error"
              ? ((c.textContent = "ERROR"), (c.style.color = "var(--error)"))
              : (c.textContent = "IDLE")
            : (c.textContent = "--");
    if ((y && r && (y.textContent = String(r.processed_chunks ?? 0)), p && r)) {
      const a = r.extra?.using_gpu === !0,
        v = n && (r.processed_chunks ?? 0) > 0;
      r.enabled && a
        ? ((p.style.display = "inline"),
          p.classList.toggle("active", v),
          (p.textContent = "GPU"))
        : (p.style.display = "none");
    }
    if (b && r) {
      const a = r.extra?.encoder_label || (r.extra?.using_gpu ? "GPU" : "CPU");
      b.textContent = a;
    }
  });
}
function gt() {
  h(() => {
    const e = ot.value,
      t = u("url-emision-label"),
      n = u("url-emision"),
      i = u("url-stream"),
      o = u("url-player");
    t && (t.textContent = e.primaryLabel),
      n && (n.textContent = e.primaryUrl),
      i && (i.textContent = e.streamUrl),
      o && ((o.textContent = e.playerUrl), (o.href = e.playerUrl));
  });
}
function yt() {
  h(() => {
    const e = Ue.value,
      t = u("ws-status-badge");
    t &&
      ((t.textContent = e ? "WS ON" : "WS OFF"),
      t.classList.toggle("active", e));
  });
}
function vt() {
  h(() => {
    N.value;
    const e = u("live-clock");
    e &&
      (e.textContent = new Date().toLocaleTimeString("en-US", { hour12: !1 }));
  }),
    at();
}
function Et() {
  h(() => {
    const e = it.value,
      t = u("remote-config"),
      n = u("btn-mode-local"),
      i = u("btn-mode-remote");
    t && (t.style.display = e === "remote" ? "" : "none"),
      n && n.classList.toggle("active", e === "local"),
      i && i.classList.toggle("active", e === "remote");
  });
}
function ft() {
  h(() => {
    st.value, V.value;
  });
}
function _t() {
  ct(), mt(), pt(), gt(), yt(), vt(), Et(), ft();
}
function Ae() {
  const e = document.getElementById("input-type")?.value || "srt";
  document.getElementById("output-type")?.value;
  const t = parseInt(
      document.getElementById("input-chunk-duration")?.value ||
        document.getElementById("input-rtmp-chunk")?.value ||
        document.getElementById("input-file-chunk")?.value ||
        String(g.CHUNK_DURATION),
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
              String(g.TTS_SPEED),
          ),
          chunk_duration_sec: t,
        });
  const i = {
    audio_extractor: { enabled: !0 },
    transcriber: {
      enabled: document.getElementById("whisper-enabled")?.checked ?? !0,
      model: document.getElementById("whisper-model")?.value || g.WHISPER_MODEL,
      language:
        document.getElementById("whisper-lang")?.value || g.WHISPER_LANGUAGE,
      device: document.getElementById("whisper-device")?.value || "auto",
      beam_size: 2,
    },
    translator: {
      enabled: document.getElementById("translator-enabled")?.checked ?? !0,
      source_lang:
        document.getElementById("translator-source")?.value ||
        g.WHISPER_LANGUAGE,
      target_lang:
        document.getElementById("translator-target")?.value ||
        g.TRANSLATE_TARGET,
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
        document.getElementById("tts-speed")?.value || String(g.TTS_SPEED),
      ),
      device: document.getElementById("tts-device")?.value || "auto",
    },
    subtitle_generator: {
      enabled: document.getElementById("subtitle-enabled")?.checked ?? !0,
      format:
        document.getElementById("subtitle-format")?.value || g.SUBTITLE_FORMAT,
      use_translated:
        document.getElementById("subtitle-use-translated")?.value === "true",
      chunk_duration: t,
    },
    audio_mixer: {
      enabled: document.getElementById("audio-mixer-enabled")?.checked ?? !1,
      original_volume: parseFloat(
        document.getElementById("audio-mixer-original-volume")?.value ||
          String(g.ORIGINAL_VOLUME),
      ),
      tts_volume: parseFloat(
        document.getElementById("audio-mixer-dubbed-volume")?.value ||
          String(g.TTS_VOLUME),
      ),
      dubbed_volume: parseFloat(
        document.getElementById("audio-mixer-dubbed-volume")?.value ||
          String(g.TTS_VOLUME),
      ),
    },
    video_muxer: {
      enabled: document.getElementById("muxer-enabled")?.checked ?? !0,
      engine: document.getElementById("video-muxer-engine")?.value || "hls",
      hls_segment_duration: parseInt(
        document.getElementById("hls-segment")?.value ||
          String(g.SEGMENT_DURATION),
      ),
      hls_list_size: parseInt(
        document.getElementById("hls-list")?.value || String(g.LIST_SIZE),
      ),
      audio_offset_ms: parseInt(
        document.getElementById("hls-audio-offset")?.value ||
          String(g.AUDIO_OFFSET),
      ),
      encoder_mode: document.getElementById("hls-encoder")?.value || "auto",
      video_quality: "medium",
      video_crf: parseInt(
        document.getElementById("hls-crf")?.value || String(g.CRF),
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
          const [s, l] = o.value.split("x").map(Number);
          return { video_width: s, video_height: l };
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
function W(e) {
  const t = document.getElementById("input-type"),
    n = document.getElementById("output-type"),
    i = document.getElementById("whisper-enabled"),
    o = document.getElementById("whisper-model"),
    s = document.getElementById("whisper-lang"),
    l = document.getElementById("whisper-device"),
    d = document.getElementById("translator-enabled"),
    m = document.getElementById("translator-source"),
    r = document.getElementById("translator-target"),
    c = document.getElementById("tts-enabled"),
    y = document.getElementById("tts-engine"),
    p = document.getElementById("tts-device"),
    b = document.getElementById("tts-device-group"),
    a = document.getElementById("tts-voice-edge"),
    v = document.getElementById("tts-voice-piper"),
    B = document.getElementById("tts-voice-edge-group"),
    R = document.getElementById("tts-voice-piper-group"),
    T = document.getElementById("tts-speed"),
    x = document.getElementById("subtitle-enabled"),
    I = document.getElementById("subtitle-format"),
    j = document.getElementById("subtitle-use-translated"),
    z = document.getElementById("muxer-enabled"),
    H = document.getElementById("video-muxer-engine"),
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
    S = e.input?.srt;
  ee && S?.listen_port && (ee.value = String(S.listen_port)),
    te && S?.mode && (te.value = S.mode),
    ne && S?.latency_ms && (ne.value = String(S.latency_ms));
  const oe = document.getElementById("input-chunk-duration"),
    ie = document.getElementById("input-rtmp-chunk"),
    se = document.getElementById("input-file-chunk"),
    O = e.pipeline?.chunk_duration_sec || g.CHUNK_DURATION;
  oe && (oe.value = String(S?.chunk_duration_sec || O));
  const C = e.input?.rtmp,
    w = e.input?.file;
  ie && (ie.value = String(C?.chunk_duration_sec || O));
  const ue = document.getElementById("input-rtmp-url"),
    le = document.getElementById("input-rtmp-mode"),
    re = document.getElementById("input-rtmp-app");
  ue && C?.url && (ue.value = C.url),
    le && C?.mode && (le.value = C.mode),
    re && C?.app && (re.value = C.app);
  const ae = document.getElementById("input-file-path"),
    de = document.getElementById("input-file-loop"),
    ce = document.getElementById("input-file-speed");
  ae && w?.path && (ae.value = w.path),
    de && w?.loop !== void 0 && (de.value = w.loop ? "true" : "false"),
    ce && w?.speed && (ce.value = String(w.speed)),
    se && (se.value = String(w?.chunk_duration_sec || O));
  const Ye =
    e.output?.type === "web" ? "webplayer" : e.output?.type || "webplayer";
  if (
    (n && ((n.value = Ye), ht()),
    i && (i.checked = e.modules.transcriber.enabled),
    o && (o.value = e.modules.transcriber.model),
    s && (s.value = e.modules.transcriber.language),
    l && (l.value = e.modules.transcriber.device),
    d && (d.checked = e.modules.translator.enabled),
    m && (m.value = e.modules.translator.source_lang),
    r && (r.value = e.modules.translator.target_lang),
    c && (c.checked = e.modules.tts_engine.enabled),
    y &&
      ((y.value = e.modules.tts_engine.engine || "edge-tts"),
      b && (b.style.display = y.value === "piper" ? "block" : "none"),
      B && R))
  ) {
    const Se = y.value === "edge-tts";
    (B.style.display = Se ? "block" : "none"),
      (R.style.display = Se ? "none" : "block");
  }
  p && (p.value = e.modules.tts_engine.device || "auto"),
    a && (a.value = e.modules.tts_engine.voice || "es-ES-AlvaroNeural"),
    v && (v.value = e.modules.tts_engine.voice || "es_ES-sharvard-medium"),
    T && (T.value = String(e.modules.tts_engine.speed)),
    x && (x.checked = e.modules.subtitle_generator.enabled),
    I && (I.value = e.modules.subtitle_generator.format),
    j && (j.value = String(e.modules.subtitle_generator.use_translated)),
    z && (z.checked = e.modules.video_muxer.enabled),
    H && (H.value = e.modules.video_muxer.engine || "hls");
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
async function Fe() {
  try {
    E("INFO", _.PIPELINE_STARTING), await Xe();
    const e = await Te();
    U(e), E("INFO", _.PIPELINE_STARTED);
  } catch (e) {
    E("ERROR", `Error: ${e.message}`);
  }
}
async function Me() {
  if (confirm(_.PIPELINE_CONFIRM_STOP))
    try {
      E("INFO", _.PIPELINE_STOPPING), await et();
      const e = await Te();
      U(e), ut(), E("INFO", _.PIPELINE_STOPPED);
    } catch (e) {
      E("ERROR", `Error: ${e.message}`);
    }
}
async function $e() {
  try {
    const e = Ae(),
      t = parseInt(
        document.getElementById("input-chunk-duration")?.value ||
          document.getElementById("input-rtmp-chunk")?.value ||
          document.getElementById("input-file-chunk")?.value ||
          String(g.CHUNK_DURATION),
      );
    await L("PUT", "/api/config", { config: e });
    try {
      await Ze(t), E("INFO", `Chunk synced: ${t}s`);
    } catch (i) {
      E("WARNING", `Chunk sync failed: ${i.message}`);
    }
    const n = await Re();
    (V.value = n),
      W(n),
      f(_.CONFIG_SAVED, "success"),
      E("INFO", "Configuración guardada");
  } catch (e) {
    const t = e.message;
    f(`${_.CONFIG_SAVE_ERROR}: ${t}`, "error"),
      E("ERROR", `Error al guardar: ${t}`);
  }
}
async function $() {
  try {
    await L("POST", "input/control/play"), f(_.INPUT_FILE_PLAY, "success");
  } catch (e) {
    f(`Error al reproducir: ${e.message}`, "error");
  }
}
async function De() {
  try {
    await L("POST", "input/control/pause"), f(_.INPUT_FILE_PAUSE, "success");
  } catch (e) {
    f(`Error al pausar: ${e.message}`, "error");
  }
}
async function D(e) {
  try {
    await L("POST", "input/control/seek", { position: e });
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
let M = null;
function bt() {
  M && clearInterval(M);
  const e = document.getElementById("input-file-position"),
    t = document.getElementById("file-time-current"),
    n = document.getElementById("file-time-total"),
    i = document.getElementById("btn-file-play"),
    o = document.getElementById("btn-file-pause");
  M = setInterval(() => {
    Ge().then((s) => {
      s &&
        (e &&
          s.duration > 0 &&
          (e.value = ((s.position / s.duration) * 100).toString()),
        t && (t.textContent = Ce(s.position)),
        n && (n.textContent = Ce(s.duration)),
        i &&
          o &&
          (s.is_playing
            ? ((i.style.display = "none"), (o.style.display = "inline"))
            : ((i.style.display = "inline"), (o.style.display = "none"))));
    });
  }, G.FILE_POLL);
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
      $().then(() => {
        (e.style.display = "none"), (t.style.display = "inline");
      });
    }),
    t.addEventListener("click", () => {
      De().then(() => {
        (t.style.display = "none"), (e.style.display = "inline");
      });
    }),
    n.addEventListener("click", () => {
      D(0).then(() => {
        (i.value = "0"),
          $().then(() => {
            (e.style.display = "none"), (t.style.display = "inline");
          });
      });
    });
  let o = null;
  i.addEventListener("input", () => {
    o && clearTimeout(o);
    const s = parseInt(i.value);
    o = setTimeout(() => {
      Ge().then((l) => {
        l?.duration && D((s / 100) * l.duration);
      });
    }, G.SEEK_DEBOUNCE);
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
    s = n?.value || "live",
    l = i?.value || "stream";
  e.value = `rtmp://127.0.0.1:${o}/${s}/${l}`;
}
let P = null,
  Bt = null;
async function je() {
  tt(), E("INFO", _.LOADING);
  try {
    const e = await Re();
    (V.value = e), W(e);
    const t = document.getElementById("input-type");
    t?.value === "rtmp" && We(),
      t?.value === "file" &&
        document.getElementById("input-file-path")?.value &&
        Ve();
    const n = await L("GET", "api/status");
    U(n), _t();
    const i = Je("/ws/logs");
    (P = new Qe(i)),
      P.onMessage((o) => {
        o.type === "log"
          ? E(o.level ?? "INFO", o.message ?? "")
          : o.type === "status" && o.status && U(o.status);
      }),
      P.onError(() => {
        E("ERROR", _.WS_ERROR);
      }),
      P.onClose(() => {
        (Ue.value = !1), E("ERROR", _.WS_DISCONNECTED);
      }),
      P.connect(),
      (Bt = setInterval(async () => {
        try {
          const o = await L("GET", "api/status");
          U(o);
        } catch {}
      }, G.STATUS_POLL)),
      E("INFO", _.SUCCESS);
  } catch (e) {
    E("ERROR", `Error de inicialización: ${e.message}`);
  }
}
function ze() {
  document.getElementById("btn-start")?.addEventListener("click", Fe),
    document.getElementById("btn-stop")?.addEventListener("click", Me),
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
      s = document.getElementById("metric-memory-value"),
      l = document.getElementById("metric-memory-percent"),
      d = document.getElementById("metric-memory-bar"),
      m = document.getElementById("metric-gpu-value"),
      r = document.getElementById("metric-gpu-bar");
    i && (i.textContent = (n.cpu_percent || n.cpu_usage || 0) + "%"),
      o && (o.style.width = (n.cpu_percent || n.cpu_usage || 0) + "%"),
      s && (s.textContent = (n.memory_mb || 0).toFixed(0) + " MB"),
      l && (l.textContent = (n.memory_percent || n.memory_usage || 0) + "%"),
      d && (d.style.width = (n.memory_percent || n.memory_usage || 0) + "%"),
      m && (m.textContent = (n.gpu_usage || 0) + "%"),
      r && (r.style.width = (n.gpu_usage || 0) + "%");
  } catch (e) {
    console.error("Metrics refresh failed:", e);
  }
}
function xt() {
  document.getElementById("btn-copy-emision")?.addEventListener("click", () => {
    const e = document.getElementById("url-emision");
    e?.textContent &&
      A(e.textContent)
        .then(() => f("URL de emisión copiada", "success"))
        .catch(() => f("Error al copiar URL", "error"));
  }),
    document
      .getElementById("btn-copy-stream")
      ?.addEventListener("click", () => {
        const e = document.getElementById("url-stream");
        e?.textContent &&
          A(e.textContent)
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
            A(t)
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
      applyConfigToUI: W,
      bootstrap: Ke,
      collectConfigFromUI: Ae,
      fileInputPause: De,
      fileInputPlay: $,
      fileInputSeek: D,
      handleSaveConfig: $e,
      handleStart: Fe,
      handleStop: Me,
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
      "./keyboard-shortcuts.DWUtHfJE.js"
    );
    return { initKeyboardShortcuts: e };
  },
  __vite__mapDeps([0, 1, 2]),
).then(({ initKeyboardShortcuts: e }) => {
  e();
});
export { Oe as _, Me as a, Fe as b, $e as h, _t as s };
