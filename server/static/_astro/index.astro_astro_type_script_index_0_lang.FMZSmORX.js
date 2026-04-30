import {
  b as qe,
  a as O,
  c as ft,
  W as vt,
  M as v,
  I as X,
  D as m,
  d as gt,
  e as Ye,
  f as yt,
  h as Y,
  u as ht,
} from "./api.0LLDw1WM.js";
import { c as J, s as B } from "./index.BpSbb1Lw.js";
import { a as Ge } from "./format.BguR9Uz2.js";
let Ve = !1;
function Et() {
  Ve ||
    ((Ve = !0),
    We(),
    setInterval(() => {
      We();
    }, 1e3));
}
function We() {
  const e = document.getElementById("live-clock");
  e && (e.textContent = new Date().toLocaleTimeString("en-US", { hour12: !1 }));
}
var _t = Symbol.for("preact-signals");
function ee() {
  if (P > 1) P--;
  else {
    var e,
      t = !1;
    for (
      (function () {
        var i = z;
        for (z = void 0; i !== void 0; )
          i.S.v === i.v && (i.S.i = i.i), (i = i.o);
      })();
      V !== void 0;

    ) {
      var n = V;
      for (V = void 0, H++; n !== void 0; ) {
        var o = n.u;
        if (((n.u = void 0), (n.f &= -3), !(8 & n.f) && Xe(n)))
          try {
            n.c();
          } catch (i) {
            t || ((e = i), (t = !0));
          }
        n = o;
      }
    }
    if (((H = 0), P--, t)) throw e;
  }
}
var l = void 0;
function Je(e) {
  var t = l;
  l = void 0;
  try {
    return e();
  } finally {
    l = t;
  }
}
var V = void 0,
  P = 0,
  H = 0,
  je = 0,
  z = void 0,
  K = 0;
function Qe(e) {
  if (l !== void 0) {
    var t = e.n;
    if (t === void 0 || t.t !== l)
      return (
        (t = {
          i: 0,
          S: e,
          p: l.s,
          n: void 0,
          t: l,
          e: void 0,
          x: void 0,
          r: t,
        }),
        l.s !== void 0 && (l.s.n = t),
        (l.s = t),
        (e.n = t),
        32 & l.f && e.S(t),
        t
      );
    if (t.i === -1)
      return (
        (t.i = 0),
        t.n !== void 0 &&
          ((t.n.p = t.p),
          t.p !== void 0 && (t.p.n = t.n),
          (t.p = l.s),
          (t.n = void 0),
          (l.s.n = t),
          (l.s = t)),
        t
      );
  }
}
function g(e, t) {
  (this.v = e),
    (this.i = 0),
    (this.n = void 0),
    (this.t = void 0),
    (this.l = 0),
    (this.W = t?.watched),
    (this.Z = t?.unwatched),
    (this.name = t?.name);
}
g.prototype.brand = _t;
g.prototype.h = function () {
  return !0;
};
g.prototype.S = function (e) {
  var t = this,
    n = this.t;
  n !== e &&
    e.e === void 0 &&
    ((e.x = n),
    (this.t = e),
    n !== void 0
      ? (n.e = e)
      : Je(function () {
          var o;
          (o = t.W) == null || o.call(t);
        }));
};
g.prototype.U = function (e) {
  var t = this;
  if (this.t !== void 0) {
    var n = e.e,
      o = e.x;
    n !== void 0 && ((n.x = o), (e.e = void 0)),
      o !== void 0 && ((o.e = n), (e.x = void 0)),
      e === this.t &&
        ((this.t = o),
        o === void 0 &&
          Je(function () {
            var i;
            (i = t.Z) == null || i.call(t);
          }));
  }
};
g.prototype.subscribe = function (e) {
  var t = this;
  return b(
    function () {
      var n = t.value,
        o = l;
      l = void 0;
      try {
        e(n);
      } finally {
        l = o;
      }
    },
    { name: "sub" },
  );
};
g.prototype.valueOf = function () {
  return this.value;
};
g.prototype.toString = function () {
  return this.value + "";
};
g.prototype.toJSON = function () {
  return this.value;
};
g.prototype.peek = function () {
  var e = l;
  l = void 0;
  try {
    return this.value;
  } finally {
    l = e;
  }
};
Object.defineProperty(g.prototype, "value", {
  get: function () {
    var e = Qe(this);
    return e !== void 0 && (e.i = this.i), this.v;
  },
  set: function (e) {
    if (e !== this.v) {
      if (H > 100) throw new Error("Cycle detected");
      (function (n) {
        P !== 0 &&
          H === 0 &&
          n.l !== je &&
          ((n.l = je), (z = { S: n, v: n.v, i: n.i, o: z }));
      })(this),
        (this.v = e),
        this.i++,
        K++,
        P++;
      try {
        for (var t = this.t; t !== void 0; t = t.x) t.t.N();
      } finally {
        ee();
      }
    }
  },
});
function C(e, t) {
  return new g(e, t);
}
function Xe(e) {
  for (var t = e.s; t !== void 0; t = t.n)
    if (t.S.i !== t.i || !t.S.h() || t.S.i !== t.i) return !0;
  return !1;
}
function et(e) {
  for (var t = e.s; t !== void 0; t = t.n) {
    var n = t.S.n;
    if ((n !== void 0 && (t.r = n), (t.S.n = t), (t.i = -1), t.n === void 0)) {
      e.s = t;
      break;
    }
  }
}
function tt(e) {
  for (var t = e.s, n = void 0; t !== void 0; ) {
    var o = t.p;
    t.i === -1
      ? (t.S.U(t), o !== void 0 && (o.n = t.n), t.n !== void 0 && (t.n.p = o))
      : (n = t),
      (t.S.n = t.r),
      t.r !== void 0 && (t.r = void 0),
      (t = o);
  }
  e.s = n;
}
function N(e, t) {
  g.call(this, void 0),
    (this.x = e),
    (this.s = void 0),
    (this.g = K - 1),
    (this.f = 4),
    (this.W = t?.watched),
    (this.Z = t?.unwatched),
    (this.name = t?.name);
}
N.prototype = new g();
N.prototype.h = function () {
  if (((this.f &= -3), 1 & this.f)) return !1;
  if ((36 & this.f) == 32 || ((this.f &= -5), this.g === K)) return !0;
  if (((this.g = K), (this.f |= 1), this.i > 0 && !Xe(this)))
    return (this.f &= -2), !0;
  var e = l;
  try {
    et(this), (l = this);
    var t = this.x();
    (16 & this.f || this.v !== t || this.i === 0) &&
      ((this.v = t), (this.f &= -17), this.i++);
  } catch (n) {
    (this.v = n), (this.f |= 16), this.i++;
  }
  return (l = e), tt(this), (this.f &= -2), !0;
};
N.prototype.S = function (e) {
  if (this.t === void 0) {
    this.f |= 36;
    for (var t = this.s; t !== void 0; t = t.n) t.S.S(t);
  }
  g.prototype.S.call(this, e);
};
N.prototype.U = function (e) {
  if (this.t !== void 0 && (g.prototype.U.call(this, e), this.t === void 0)) {
    this.f &= -33;
    for (var t = this.s; t !== void 0; t = t.n) t.S.U(t);
  }
};
N.prototype.N = function () {
  if (!(2 & this.f)) {
    this.f |= 6;
    for (var e = this.t; e !== void 0; e = e.x) e.t.N();
  }
};
Object.defineProperty(N.prototype, "value", {
  get: function () {
    if (1 & this.f) throw new Error("Cycle detected");
    var e = Qe(this);
    if ((this.h(), e !== void 0 && (e.i = this.i), 16 & this.f)) throw this.v;
    return this.v;
  },
});
function x(e, t) {
  return new N(e, t);
}
function nt(e) {
  var t = e.m;
  if (((e.m = void 0), typeof t == "function")) {
    P++;
    var n = l;
    l = void 0;
    try {
      t();
    } catch (o) {
      throw ((e.f &= -2), (e.f |= 8), te(e), o);
    } finally {
      (l = n), ee();
    }
  }
}
function te(e) {
  for (var t = e.s; t !== void 0; t = t.n) t.S.U(t);
  (e.x = void 0), (e.s = void 0), nt(e);
}
function It(e) {
  if (l !== this) throw new Error("Out-of-order effect");
  tt(this), (l = e), (this.f &= -2), 8 & this.f && te(this), ee();
}
function $(e, t) {
  (this.x = e),
    (this.m = void 0),
    (this.s = void 0),
    (this.u = void 0),
    (this.f = 32),
    (this.name = t?.name);
}
$.prototype.c = function () {
  var e = this.S();
  try {
    if (8 & this.f || this.x === void 0) return;
    var t = this.x();
    typeof t == "function" && (this.m = t);
  } finally {
    e();
  }
};
$.prototype.S = function () {
  if (1 & this.f) throw new Error("Cycle detected");
  (this.f |= 1), (this.f &= -9), nt(this), et(this), P++;
  var e = l;
  return (l = this), It.bind(this, e);
};
$.prototype.N = function () {
  2 & this.f || ((this.f |= 2), (this.u = V), (V = this));
};
$.prototype.d = function () {
  (this.f |= 8), 1 & this.f || te(this);
};
$.prototype.dispose = function () {
  this.d();
};
function b(e, t) {
  var n = new $(e, t);
  try {
    n.c();
  } catch (i) {
    throw (n.d(), i);
  }
  var o = n.d.bind(n);
  return (o[Symbol.dispose] = o), o;
}
const I = C(null),
  Z = C(null),
  He = C([]),
  ot = C(!1);
C(!1);
const it = C("local");
C(!1);
const j = C([]);
x(() => I.value?.state ?? "stopped");
const st = x(() => I.value?.state === "running");
x(() => I.value?.state === "stopping");
x(() => I.value?.chunks_processed ?? 0);
const bt = x(() => {
  const e = I.value?.modules;
  return e ? Object.fromEntries(e.map((t) => [t.name, t])) : {};
});
x(() => {
  const e = bt.value;
  return Object.entries(e)
    .filter(([, t]) => t.enabled)
    .map(([t]) => t);
});
const Bt = x(() => {
    const e = I.value,
      t = e?.system_metrics ?? e?.system ?? {},
      n = e?.uptime_seconds ?? 0,
      o = e?.chunks_processed ?? 0,
      i = n > 0 ? o / n : 0;
    return {
      cpu: t.cpu_percent ?? t.cpu_usage ?? 0,
      memoryMb: t.memory_mb ?? 0,
      memoryPercent: t.memory_percent ?? t.memory_usage ?? 0,
      gpuUtil: t.gpu_percent ?? t.gpu_usage ?? 0,
      gpuMemMb: t.gpu_memory_mb ?? 0,
      gpuMemPercent: t.gpu_memory_usage ?? 0,
      chunksPerSec: i,
      totalChunks: o,
    };
  }),
  St = x(() => {
    const e = Z.value,
      t =
        it.value === "remote"
          ? document.getElementById("emitter-address")?.value || "localhost"
          : "127.0.0.1",
      n = e?.input?.type ?? "srt",
      o = e?.input?.srt?.port ?? 9e3,
      i = e?.input?.rtmp?.port ?? 1935,
      s = e?.server?.port ?? 9999,
      r = `srt://${t}:${o}`,
      y = `rtmp://${t}:${i}`,
      d = `http://${t}:${s}/hls/stream.m3u8`,
      c = `http://${t}:${s}/player`;
    return {
      host: t,
      inputType: n,
      srtUrl: r,
      rtmpUrl: y,
      streamUrl: d,
      playerUrl: c,
      srtLabel: n === "rtmp" ? "RTMP:" : "SRT:",
      primaryUrl: n === "rtmp" ? y : r,
      primaryLabel: n === "rtmp" ? "RTMP:" : "SRT:",
    };
  }),
  ut = x(() => {
    const e = j.value;
    return e.length === 0 ? 0 : e.reduce((t, n) => t + n, 0) / e.length;
  });
function W(e) {
  I.value = e;
  const t = e?.uptime_seconds ?? 0,
    n = e?.chunks_processed ?? 0,
    o = e?.avg_processing_time_ms ?? 0,
    i = o > 0 ? 1e3 / o : t > 0 ? n / t : 0;
  if (i > 0) {
    const s = [...j.value, i];
    j.value = s.slice(-10);
  }
}
function f(e, t) {
  const n = { timestamp: new Date().toISOString(), level: e, message: t };
  He.value = [...He.value.slice(-499), n];
}
function xt() {
  j.value = [];
}
var M = ((e) => (
  (e.STOPPED = "stopped"),
  (e.RUNNING = "running"),
  (e.STARTING = "starting"),
  (e.STOPPING = "stopping"),
  (e.ERROR = "error"),
  e
))(M || {});
function wt(e) {
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
function Ct() {
  b(() => {
    const e = I.value,
      t = u("status-dot"),
      n = u("status-text");
    if (!t || !n) return;
    const o = wt(e?.state);
    t.classList.toggle("running", o === M.RUNNING),
      t.classList.toggle("error", o === M.ERROR),
      (n.textContent = o === M.RUNNING ? "ACTIVO" : "APAGADO");
    const i = u("btn-start"),
      s = u("btn-stop");
    if (i) {
      const r = o === M.RUNNING;
      (i.disabled = r), (i.style.opacity = r ? "0.5" : "1");
    }
    if (s) {
      const r = o === M.RUNNING;
      (s.disabled = !r), (s.style.opacity = r ? "1" : "0.5");
    }
  }),
    b(() => {
      const t = I.value?.modules ?? [],
        n = st.value,
        o = {
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
      for (const i of t) {
        const s = o[i.name];
        if (!s) continue;
        const r = u(s);
        r && r.classList.toggle("active", n && i.enabled);
      }
    }),
    b(() => {
      const e = I.value,
        t = u("pipeline-indicator");
      t && t.classList.toggle("active", e?.state === "running");
    });
}
function kt() {
  b(() => {
    const e = Bt.value,
      t = ut.value,
      n = u("metric-cpu-bar"),
      o = u("metric-cpu-value"),
      i = u("metric-cpu");
    n && (n.style.width = `${e.cpu}%`),
      o && (o.textContent = `${e.cpu.toFixed(0)}%`),
      i &&
        (i.classList.toggle("warning", e.cpu > 70),
        i.classList.toggle("critical", e.cpu > 90));
    const s = u("metric-memory-bar"),
      r = u("metric-memory-value"),
      y = u("metric-memory-percent"),
      d = u("metric-memory");
    s && (s.style.width = `${e.memoryPercent}%`),
      r && (r.textContent = `${e.memoryMb.toFixed(0)} MB`),
      y && (y.textContent = `${e.memoryPercent.toFixed(0)}%`),
      d &&
        (d.classList.toggle("warning", e.memoryPercent > 70),
        d.classList.toggle("critical", e.memoryPercent > 90));
    const c = u("metric-gpu-bar"),
      h = u("metric-gpu-value"),
      S = u("metric-gpu-memory"),
      E = u("metric-gpu");
    c && (c.style.width = `${e.gpuUtil}%`),
      h && (h.textContent = `${e.gpuUtil.toFixed(0)}%`),
      S &&
        (S.textContent =
          e.gpuMemMb > 0 ? `${e.gpuMemMb.toFixed(0)} MB` : "N/A"),
      E &&
        (E.classList.toggle("warning", e.gpuUtil > 80),
        E.classList.toggle("critical", e.gpuUtil > 95));
    const w = u("metric-throughput-bar"),
      a = u("metric-throughput-value");
    w && (w.style.width = `${Math.min(t * 10, 100)}%`),
      a && (a.textContent = `${t.toFixed(2)}/s`);
  });
}
function Tt() {
  b(() => {
    const e = I.value,
      t = e?.modules ?? [],
      n = st.value,
      o = ut.value,
      i = Object.fromEntries(t.map((a) => [a.name, a]));
    for (const a of [
      "transcriber",
      "translator",
      "tts_engine",
      "subtitle_generator",
      "audio_mixer",
    ]) {
      const p = i[a],
        k = u(`module-time-${a}`),
        A = u(`module-chunks-${a}`),
        D = u(`module-encoder-${a}`);
      if (k)
        if (p?.last_process_time_ms !== void 0 && p.last_process_time_ms > 0) {
          const _ = p.last_process_time_ms;
          k.textContent =
            _ < 1e3 ? `${Math.round(_)}ms` : `${(_ / 1e3).toFixed(1)}s`;
        } else if (n && o > 0) {
          const _ = (1e3 / o).toFixed(0);
          k.textContent = `${_}ms`;
        } else k.textContent = "--";
      if (
        (A && (A.textContent = String(p?.processed_chunks ?? 0)), D && p?.extra)
      ) {
        const _ = p.extra.encoder_label || (p.extra.using_gpu ? "GPU" : "CPU");
        D.textContent = _;
      }
      const T = u(`gpu-badge-${a}`);
      if (T && p?.extra) {
        const _ = n && p.enabled && (p.processed_chunks ?? 0) > 0;
        p.extra.using_gpu
          ? ((T.style.display = "inline"), T.classList.toggle("active", _))
          : (T.style.display = "none");
      }
    }
    const s = u("module-time-video_muxer"),
      r = u("module-chunks-video_muxer"),
      y = u("module-encoder-video_muxer"),
      d = i.video_muxer ?? i.output;
    if (s)
      if (d?.last_process_time_ms !== void 0 && d.last_process_time_ms > 0) {
        const a = d.last_process_time_ms;
        s.textContent =
          a < 1e3 ? `${Math.round(a)}ms` : `${(a / 1e3).toFixed(1)}s`;
      } else
        n && o > 0
          ? (s.textContent = `${(1e3 / o).toFixed(0)}ms`)
          : (s.textContent = "--");
    if (
      (r &&
        (r.textContent = String(
          d?.processed_chunks ?? e?.chunks_processed ?? 0,
        )),
      y)
    ) {
      const a =
        d?.extra?.encoder_label ?? (d?.extra?.using_gpu ? "GPU" : "CPU");
      y.textContent = a;
    }
    const c =
        i.srt_input ??
        i.rtmp_input ??
        i.file_input ??
        i.audio_extractor ??
        i.input,
      h = u("module-time-input"),
      S = u("module-chunks-input"),
      E = u("gpu-badge-input"),
      w = u("module-encoder-input");
    if (h)
      if (c?.last_process_time_ms !== void 0 && c.last_process_time_ms > 0) {
        const a = c.last_process_time_ms;
        h.textContent =
          a < 1e3 ? `${Math.round(a)}ms` : `${(a / 1e3).toFixed(1)}s`;
      } else
        n && o > 0
          ? (h.textContent = `${(1e3 / o).toFixed(0)}ms`)
          : c?.enabled
            ? c?.state === "error"
              ? ((h.textContent = "ERROR"), (h.style.color = "var(--error)"))
              : (h.textContent = "IDLE")
            : (h.textContent = "--");
    if ((S && c && (S.textContent = String(c.processed_chunks ?? 0)), E && c)) {
      const a = c.extra?.using_gpu === !0,
        p = n && (c.processed_chunks ?? 0) > 0;
      c.enabled && a
        ? ((E.style.display = "inline"),
          E.classList.toggle("active", p),
          (E.textContent = "GPU"))
        : (E.style.display = "none");
    }
    if (w && c) {
      const a = c.extra?.encoder_label || (c.extra?.using_gpu ? "GPU" : "CPU");
      w.textContent = a;
    }
  });
}
function Lt() {
  b(() => {
    const e = St.value,
      t = u("url-emision-label"),
      n = u("url-emision"),
      o = u("url-stream"),
      i = u("url-player");
    t && (t.textContent = e.primaryLabel),
      n && (n.textContent = e.primaryUrl),
      o && (o.textContent = e.streamUrl),
      i && ((i.textContent = e.playerUrl), (i.href = e.playerUrl));
  });
}
function Rt() {
  b(() => {
    const e = ot.value,
      t = u("ws-status-badge");
    t &&
      ((t.textContent = e ? "WS ON" : "WS OFF"),
      t.classList.toggle("active", e));
  });
}
function Ut() {
  b(() => {
    I.value;
    const e = u("live-clock");
    e &&
      (e.textContent = new Date().toLocaleTimeString("en-US", { hour12: !1 }));
  }),
    Et();
}
function Pt() {
  b(() => {
    const e = it.value,
      t = u("remote-config"),
      n = u("btn-mode-local"),
      o = u("btn-mode-remote");
    t && (t.style.display = e === "remote" ? "" : "none"),
      n && n.classList.toggle("active", e === "local"),
      o && o.classList.toggle("active", e === "remote");
  });
}
function Ot() {
  b(() => {
    j.value, Z.value;
  });
}
function Nt() {
  Ct(), kt(), Tt(), Lt(), Rt(), Ut(), Pt(), Ot();
}
const ze = {
  config: null,
  status: null,
  localMode: "local",
  wsConnected: !1,
  logs: [],
  isLoading: !1,
  error: null,
  outputs: [],
};
class Ft {
  state;
  listeners = new Set();
  history = [];
  maxHistoryLength = 20;
  constructor(t = {}) {
    this.state = { ...ze, ...t };
  }
  getState() {
    return Object.freeze({ ...this.state });
  }
  setState(t) {
    const n = this.state,
      o = { ...n, ...t };
    Object.keys(t).some((s) => n[s] !== o[s]) &&
      (this.history.push({ ...n }),
      this.history.length > this.maxHistoryLength && this.history.shift(),
      (this.state = o),
      this.notify());
  }
  subscribe(t) {
    return (
      this.listeners.add(t),
      t(this.getState()),
      () => {
        this.listeners.delete(t);
      }
    );
  }
  notify() {
    const t = this.getState();
    this.listeners.forEach((n) => {
      try {
        n(t);
      } catch (o) {
        console.error("[Store] Error in listener:", o);
      }
    });
  }
  reset() {
    (this.state = { ...ze }), this.notify();
  }
  getHistory() {
    return Object.freeze([...this.history]);
  }
  setConfig(t) {
    this.setState({ config: t });
  }
  setStatus(t) {
    this.setState({ status: t, error: null });
  }
  setWsConnected(t) {
    this.setState({ wsConnected: t });
  }
  addLog(t) {
    const n = [...this.state.logs, t].slice(-500);
    this.setState({ logs: n });
  }
  setLoading(t) {
    this.setState({ isLoading: t });
  }
  setError(t) {
    this.setState({ error: t, isLoading: !1 });
  }
  setOutputs(t) {
    this.setState({ outputs: t });
  }
  clearLogs() {
    this.setState({ logs: [] });
  }
}
new Ft();
function F(e, t = "info") {
  B(e, t);
}
async function Mt() {
  try {
    f("INFO", v.PIPELINE_STARTING), await gt();
    const e = await Ye();
    W(e), f("INFO", v.PIPELINE_STARTED);
  } catch (e) {
    f("ERROR", `Error: ${e.message}`);
  }
}
async function $t() {
  if (confirm(v.PIPELINE_CONFIRM_STOP))
    try {
      f("INFO", v.PIPELINE_STOPPING), await yt();
      const e = await Ye();
      W(e), xt(), f("INFO", v.PIPELINE_STOPPED);
    } catch (e) {
      f("ERROR", `Error: ${e.message}`);
    }
}
async function At() {
  try {
    const e = Dt(),
      t = parseInt(
        document.getElementById("input-chunk-duration")?.value ||
          document.getElementById("input-rtmp-chunk")?.value ||
          document.getElementById("input-file-chunk")?.value ||
          String(m.CHUNK_DURATION),
      );
    await O("PUT", "/api/config", { config: e });
    try {
      await ht(t), f("INFO", `Chunk synced: ${t}s`);
    } catch (o) {
      f("WARNING", `Chunk sync failed: ${o.message}`);
    }
    const n = await qe();
    (Z.value = n),
      rt(n),
      B(v.CONFIG_SAVED, "success"),
      f("INFO", "Configuración guardada");
  } catch (e) {
    const t = e.message;
    B(`${v.CONFIG_SAVE_ERROR}: ${t}`, "error"),
      f("ERROR", `Error al guardar: ${t}`);
  }
}
function Dt() {
  const e = document.getElementById("input-type")?.value || "srt";
  document.getElementById("output-type")?.value;
  const t = parseInt(
      document.getElementById("input-chunk-duration")?.value ||
        document.getElementById("input-rtmp-chunk")?.value ||
        document.getElementById("input-file-chunk")?.value ||
        String(m.CHUNK_DURATION),
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
              String(m.TTS_SPEED),
          ),
          chunk_duration_sec: t,
        });
  const o = {
    audio_extractor: { enabled: !0 },
    transcriber: {
      enabled: document.getElementById("whisper-enabled")?.checked ?? !0,
      model: document.getElementById("whisper-model")?.value || m.WHISPER_MODEL,
      language:
        document.getElementById("whisper-lang")?.value || m.WHISPER_LANGUAGE,
      device: document.getElementById("whisper-device")?.value || "auto",
      beam_size: 2,
    },
    translator: {
      enabled: document.getElementById("translator-enabled")?.checked ?? !0,
      source_lang:
        document.getElementById("translator-source")?.value ||
        m.WHISPER_LANGUAGE,
      target_lang:
        document.getElementById("translator-target")?.value ||
        m.TRANSLATE_TARGET,
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
        document.getElementById("tts-speed")?.value || String(m.TTS_SPEED),
      ),
      device: document.getElementById("tts-device")?.value || "auto",
    },
    subtitle_generator: {
      enabled: document.getElementById("subtitle-enabled")?.checked ?? !0,
      format:
        document.getElementById("subtitle-format")?.value || m.SUBTITLE_FORMAT,
      use_translated:
        document.getElementById("subtitle-use-translated")?.value === "true",
      chunk_duration: t,
    },
    audio_mixer: {
      enabled: document.getElementById("audio-mixer-enabled")?.checked ?? !1,
      original_volume: parseFloat(
        document.getElementById("audio-mixer-original-volume")?.value ||
          String(m.ORIGINAL_VOLUME),
      ),
      tts_volume: parseFloat(
        document.getElementById("audio-mixer-dubbed-volume")?.value ||
          String(m.TTS_VOLUME),
      ),
      dubbed_volume: parseFloat(
        document.getElementById("audio-mixer-dubbed-volume")?.value ||
          String(m.TTS_VOLUME),
      ),
    },
    video_muxer: {
      enabled: document.getElementById("muxer-enabled")?.checked ?? !0,
      engine: document.getElementById("video-muxer-engine")?.value || "hls",
      hls_segment_duration: parseInt(
        document.getElementById("hls-segment")?.value ||
          String(m.SEGMENT_DURATION),
      ),
      hls_list_size: parseInt(
        document.getElementById("hls-list")?.value || String(m.LIST_SIZE),
      ),
      audio_offset_ms: parseInt(
        document.getElementById("hls-audio-offset")?.value ||
          String(m.AUDIO_OFFSET),
      ),
      encoder_mode: document.getElementById("hls-encoder")?.value || "auto",
      video_quality: "medium",
      video_crf: parseInt(
        document.getElementById("hls-crf")?.value || String(m.CRF),
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
          const [s, r] = i.value.split("x").map(Number);
          return { video_width: s, video_height: r };
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
    modules: o,
  };
}
function rt(e) {
  const t = document.getElementById("input-type"),
    n = document.getElementById("output-type"),
    o = document.getElementById("whisper-enabled"),
    i = document.getElementById("whisper-model"),
    s = document.getElementById("whisper-lang"),
    r = document.getElementById("whisper-device"),
    y = document.getElementById("translator-enabled"),
    d = document.getElementById("translator-source"),
    c = document.getElementById("translator-target"),
    h = document.getElementById("tts-enabled"),
    S = document.getElementById("tts-engine"),
    E = document.getElementById("tts-device"),
    w = document.getElementById("tts-device-group"),
    a = document.getElementById("tts-voice-edge"),
    p = document.getElementById("tts-voice-piper"),
    k = document.getElementById("tts-voice-edge-group"),
    A = document.getElementById("tts-voice-piper-group"),
    D = document.getElementById("tts-speed"),
    T = document.getElementById("subtitle-enabled"),
    _ = document.getElementById("subtitle-format"),
    se = document.getElementById("subtitle-use-translated"),
    ue = document.getElementById("muxer-enabled"),
    re = document.getElementById("video-muxer-engine"),
    le = document.getElementById("hls-segment"),
    ae = document.getElementById("hls-list"),
    ce = document.getElementById("hls-encoder"),
    de = document.getElementById("hls-crf"),
    me = document.getElementById("hls-audio-offset"),
    pe = document.getElementById("hls-audio-codec"),
    fe = document.getElementById("hls-audio-bitrate"),
    mt = e.input?.type || "srt";
  t && ((t.value = mt), ne());
  const ve = document.getElementById("input-srt-port"),
    ge = document.getElementById("input-srt-mode"),
    ye = document.getElementById("input-srt-latency"),
    L = e.input?.srt;
  ve && L?.listen_port && (ve.value = String(L.listen_port)),
    ge && L?.mode && (ge.value = L.mode),
    ye && L?.latency_ms && (ye.value = String(L.latency_ms));
  const he = document.getElementById("input-chunk-duration"),
    Ee = document.getElementById("input-rtmp-chunk"),
    _e = document.getElementById("input-file-chunk"),
    q = e.pipeline?.chunk_duration_sec || m.CHUNK_DURATION;
  he && (he.value = String(L?.chunk_duration_sec || q));
  const R = e.input?.rtmp,
    U = e.input?.file;
  Ee && (Ee.value = String(R?.chunk_duration_sec || q));
  const Ie = document.getElementById("input-rtmp-url"),
    be = document.getElementById("input-rtmp-mode"),
    Be = document.getElementById("input-rtmp-app");
  Ie && R?.url && (Ie.value = R.url),
    be && R?.mode && (be.value = R.mode),
    Be && R?.app && (Be.value = R.app);
  const Se = document.getElementById("input-file-path"),
    xe = document.getElementById("input-file-loop"),
    we = document.getElementById("input-file-speed");
  Se && U?.path && (Se.value = U.path),
    xe && U?.loop !== void 0 && (xe.value = U.loop ? "true" : "false"),
    we && U?.speed && (we.value = String(U.speed)),
    _e && (_e.value = String(U?.chunk_duration_sec || q));
  const pt =
    e.output?.type === "web" ? "webplayer" : e.output?.type || "webplayer";
  if (
    (n && ((n.value = pt), lt()),
    o && (o.checked = e.modules.transcriber.enabled),
    i && (i.value = e.modules.transcriber.model),
    s && (s.value = e.modules.transcriber.language),
    r && (r.value = e.modules.transcriber.device),
    y && (y.checked = e.modules.translator.enabled),
    d && (d.value = e.modules.translator.source_lang),
    c && (c.value = e.modules.translator.target_lang),
    h && (h.checked = e.modules.tts_engine.enabled),
    S &&
      ((S.value = e.modules.tts_engine.engine || "edge-tts"),
      w && (w.style.display = S.value === "piper" ? "block" : "none"),
      k && A))
  ) {
    const De = S.value === "edge-tts";
    (k.style.display = De ? "block" : "none"),
      (A.style.display = De ? "none" : "block");
  }
  E && (E.value = e.modules.tts_engine.device || "auto"),
    a && (a.value = e.modules.tts_engine.voice || "es-ES-AlvaroNeural"),
    p && (p.value = e.modules.tts_engine.voice || "es_ES-sharvard-medium"),
    D && (D.value = String(e.modules.tts_engine.speed)),
    T && (T.checked = e.modules.subtitle_generator.enabled),
    _ && (_.value = e.modules.subtitle_generator.format),
    se && (se.value = String(e.modules.subtitle_generator.use_translated)),
    ue && (ue.checked = e.modules.video_muxer.enabled),
    re && (re.value = e.modules.video_muxer.engine || "hls");
  const Ce = document.getElementById("audio-mixer-enabled");
  Ce && (Ce.checked = e.modules.audio_mixer?.enabled ?? !1);
  const ke = document.getElementById("audio-mixer-original-volume");
  ke && (ke.value = String(e.modules.audio_mixer?.original_volume ?? 0.3));
  const Te = document.getElementById("audio-mixer-original-value");
  Te &&
    (Te.textContent = String(e.modules.audio_mixer?.original_volume ?? 0.3));
  const Le = document.getElementById("audio-mixer-dubbed-volume");
  Le &&
    (Le.value = String(
      e.modules.audio_mixer?.tts_volume ??
        e.modules.audio_mixer?.dubbed_volume ??
        1,
    ));
  const Re = document.getElementById("audio-mixer-dubbed-value");
  Re &&
    (Re.textContent = String(
      e.modules.audio_mixer?.tts_volume ??
        e.modules.audio_mixer?.dubbed_volume ??
        1,
    )),
    le && (le.value = String(e.modules.video_muxer.hls_segment_duration)),
    ae && (ae.value = String(e.modules.video_muxer.hls_list_size)),
    ce && (ce.value = e.modules.video_muxer.encoder_mode),
    de && (de.value = String(e.modules.video_muxer.video_crf)),
    me && (me.value = String(e.modules.video_muxer.audio_offset_ms || 0)),
    pe && (pe.value = e.modules.video_muxer.audio_codec || "aac"),
    fe && (fe.value = e.modules.video_muxer.audio_bitrate || "192k");
  const Ue = document.getElementById("webrtc-encoder"),
    Pe = document.getElementById("webrtc-video-codec"),
    Oe = document.getElementById("webrtc-video-bitrate"),
    Ne = document.getElementById("webrtc-video-resolution"),
    Fe = document.getElementById("webrtc-video-fps"),
    Me = document.getElementById("webrtc-audio-codec"),
    $e = document.getElementById("webrtc-audio-bitrate"),
    Ae = document.getElementById("webrtc-audio-sample-rate");
  Ue && (Ue.value = e.modules.video_muxer.encoder_mode || "auto"),
    Pe && (Pe.value = e.modules.video_muxer.video_codec || "h264"),
    Oe && (Oe.value = e.modules.video_muxer.video_bitrate || "1000k"),
    Ne &&
      e.modules.video_muxer.video_width &&
      e.modules.video_muxer.video_height &&
      (Ne.value = `${e.modules.video_muxer.video_width}x${e.modules.video_muxer.video_height}`),
    Fe &&
      e.modules.video_muxer.video_fps &&
      (Fe.value = String(e.modules.video_muxer.video_fps)),
    Me && (Me.value = e.modules.video_muxer.audio_codec || "opus"),
    $e &&
      ($e.value =
        e.modules.video_muxer.webrtc_audio_bitrate ||
        e.modules.video_muxer.audio_bitrate ||
        "64k"),
    Ae &&
      e.modules.video_muxer.audio_sample_rate &&
      (Ae.value = String(e.modules.video_muxer.audio_sample_rate));
}
function ne() {
  const e = document.getElementById("input-type");
  e && (e.value = e.value);
}
function lt() {
  const e = document.getElementById("output-type");
  e && (e.value = e.value);
}
function Gt(e) {
  const t = document.getElementById("tts-engine");
  t && (t.value = e);
}
function Vt(e) {
  if ((ne(), e === "rtmp" && oe(), e === "file")) {
    const n = document.getElementById("input-file-path"),
      o = document.getElementById("file-player-controls");
    n && n.value && o && ((o.style.display = "flex"), ct());
  }
  const t = document.getElementById("input-process-title");
  if (t) {
    const n = {
      srt: `${Y.input} (SRT)`,
      rtmp: `${Y.input} (RTMP)`,
      file: `${Y.input} (File)`,
    };
    t.textContent = n[e] || "📥 INPUT";
  }
}
function Wt(e) {}
function oe() {
  const e = document.getElementById("input-rtmp-url");
  if (!e) return;
  const t = document.getElementById("input-rtmp-port"),
    n = document.getElementById("input-rtmp-app"),
    o = document.getElementById("input-rtmp-key"),
    i = t?.value || "1935",
    s = n?.value || "live",
    r = o?.value || "stream";
  e.value = `rtmp://127.0.0.1:${i}/${s}/${r}`;
}
function jt() {
  const e = document.getElementById("input-rtmp-url");
  e?.value &&
    navigator.clipboard
      .writeText(e.value)
      .then(() => {
        B(v.URL_COPIED, "success");
      })
      .catch(() => {
        B(v.URL_COPY_ERROR, "error");
      });
}
async function Ke() {
  try {
    await O("POST", "input/control/play"), B(v.INPUT_FILE_PLAY, "success");
  } catch (e) {
    B(`Error al reproducir: ${e.message}`, "error");
  }
}
async function Ht() {
  try {
    await O("POST", "input/control/pause"), B(v.INPUT_FILE_PAUSE, "success");
  } catch (e) {
    B(`Error al pausar: ${e.message}`, "error");
  }
}
async function Ze(e) {
  try {
    await O("POST", "input/control/seek", { position: e });
  } catch (t) {
    B(`Error al buscar posición: ${t.message}`, "error");
  }
}
async function at() {
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
function zt() {
  Q && clearInterval(Q);
  const e = document.getElementById("input-file-position"),
    t = document.getElementById("file-time-current"),
    n = document.getElementById("file-time-total"),
    o = document.getElementById("btn-file-play"),
    i = document.getElementById("btn-file-pause");
  Q = setInterval(() => {
    at().then((s) => {
      s &&
        (e &&
          s.duration > 0 &&
          (e.value = ((s.position / s.duration) * 100).toString()),
        t && (t.textContent = Ge(s.position)),
        n && (n.textContent = Ge(s.duration)),
        o &&
          i &&
          (s.is_playing
            ? ((o.style.display = "none"), (i.style.display = "inline"))
            : ((o.style.display = "inline"), (i.style.display = "none"))));
    });
  }, X.FILE_POLL);
}
function ct() {
  const e = document.getElementById("btn-file-play"),
    t = document.getElementById("btn-file-pause"),
    n = document.getElementById("btn-file-restart"),
    o = document.getElementById("input-file-position");
  if (!e || !t || !n || !o) return;
  (e.style.display = "inline"),
    (t.style.display = "none"),
    e.addEventListener("click", () => {
      Ke().then(() => {
        (e.style.display = "none"), (t.style.display = "inline");
      });
    }),
    t.addEventListener("click", () => {
      Ht().then(() => {
        (t.style.display = "none"), (e.style.display = "inline");
      });
    }),
    n.addEventListener("click", () => {
      Ze(0).then(() => {
        (o.value = "0"),
          Ke().then(() => {
            (e.style.display = "none"), (t.style.display = "inline");
          });
      });
    });
  let i = null;
  o.addEventListener("input", () => {
    i && clearTimeout(i);
    const s = parseInt(o.value);
    i = setTimeout(() => {
      at().then((r) => {
        r?.duration && Ze((s / 100) * r.duration);
      });
    }, X.SEEK_DEBOUNCE);
  }),
    zt();
}
function Kt() {
  document.getElementById("btn-start")?.addEventListener("click", Mt),
    document.getElementById("btn-stop")?.addEventListener("click", $t);
}
function Zt() {
  document.getElementById("btn-copy-emision")?.addEventListener("click", () => {
    const e = document.getElementById("url-emision");
    e?.textContent &&
      J(e.textContent)
        .then(() => F("URL de emisión copiada", "success"))
        .catch(() => F("Error al copiar URL", "error"));
  }),
    document
      .getElementById("btn-copy-stream")
      ?.addEventListener("click", () => {
        const e = document.getElementById("url-stream");
        e?.textContent &&
          J(e.textContent)
            .then(() => F("URL del stream copiada", "success"))
            .catch(() => F("Error al copiar URL", "error"));
      }),
    document
      .getElementById("btn-copy-player")
      ?.addEventListener("click", () => {
        const e = document.getElementById("url-player");
        if (e) {
          const t = e.getAttribute("href") || e.textContent;
          t &&
            J(t)
              .then(() => F("URL del player copiada", "success"))
              .catch(() => F("Error al copiar URL", "error"));
        }
      });
}
let G = null,
  qt = null;
async function ie() {
  f("INFO", v.LOADING);
  try {
    const e = await qe();
    (Z.value = e), rt(e);
    const t = document.getElementById("input-type");
    t?.value === "rtmp" && oe(),
      t?.value === "file" &&
        document.getElementById("input-file-path")?.value &&
        ct();
    const n = await O("GET", "api/status");
    W(n), Nt();
    const o = ft("/ws/logs");
    (G = new vt(o)),
      G.onMessage((i) => {
        i.type === "log"
          ? f(i.level ?? "INFO", i.message ?? "")
          : i.type === "status" && i.status && W(i.status);
      }),
      G.onError(() => {
        f("ERROR", v.WS_ERROR);
      }),
      G.onClose(() => {
        (ot.value = !1), f("ERROR", v.WS_DISCONNECTED);
      }),
      G.connect(),
      (qt = setInterval(async () => {
        try {
          const i = await O("GET", "api/status");
          W(i);
        } catch {}
      }, X.STATUS_POLL)),
      f("INFO", v.SUCCESS);
  } catch (e) {
    f("ERROR", `Error de inicialización: ${e.message}`);
  }
}
function Yt() {
  (window.toggleModule = Jt),
    (window.updateInputFields = ne),
    (window.updateOutputFields = lt),
    (window.handleTtsEngineChange = Gt),
    (window.handleInputTypeChange = Vt),
    (window.updateRtmpUrl = oe),
    (window.copyRtmpUrl = jt),
    (window.handleOutputFormatChange = Wt),
    (window.saveConfig = At),
    (window.init = ie);
}
async function Jt(e, t) {
  try {
    await O("PUT", `modules/${e}/toggle`, { enabled: t });
  } catch (n) {
    B(`Failed to toggle ${e}: ${n.message}`, "error");
  }
}
async function dt() {
  try {
    const n = (await (await fetch("/api/status")).json()).system || {},
      o = document.getElementById("metric-cpu-value"),
      i = document.getElementById("metric-cpu-bar"),
      s = document.getElementById("metric-memory-value"),
      r = document.getElementById("metric-memory-percent"),
      y = document.getElementById("metric-memory-bar"),
      d = document.getElementById("metric-gpu-value"),
      c = document.getElementById("metric-gpu-bar");
    o && (o.textContent = (n.cpu_percent || n.cpu_usage || 0) + "%"),
      i && (i.style.width = (n.cpu_percent || n.cpu_usage || 0) + "%"),
      s && (s.textContent = (n.memory_mb || 0).toFixed(0) + " MB"),
      r && (r.textContent = (n.memory_percent || n.memory_usage || 0) + "%"),
      y && (y.style.width = (n.memory_percent || n.memory_usage || 0) + "%"),
      d && (d.textContent = (n.gpu_usage || 0) + "%"),
      c && (c.style.width = (n.gpu_usage || 0) + "%");
  } catch (e) {
    console.error("Metrics refresh failed:", e);
  }
}
function Qt() {
  Kt(),
    Zt(),
    Yt(),
    setTimeout(() => {
      ie(), dt();
    }, 100);
}
document.addEventListener("DOMContentLoaded", Qt);
document.addEventListener("load", () => {
  setTimeout(() => {
    ie(), dt();
  }, 500);
});
