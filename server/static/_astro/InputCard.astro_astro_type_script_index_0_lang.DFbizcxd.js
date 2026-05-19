import { y as l, g as v, j as m } from "./vendor-signals.DQU3zyvD.js";
const Os = 9999,
  it = { AUTH_TOKEN: "srt2web_auth_token", LANGUAGE: "srt2web_language" },
  Us = {
    CHUNK_DURATION: 3,
    SEGMENT_DURATION: 2,
    LIST_SIZE: 2,
    AUDIO_OFFSET: 0,
    CRF: 18,
    AUDIO_BITRATE: "192k",
    AUDIO_SAMPLE_RATE: 48e3,
    TTS_SPEED: 1,
    ORIGINAL_VOLUME: 0.8,
    TTS_VOLUME: 1,
    WHISPER_MODEL: "tiny",
    WHISPER_LANGUAGE: "en",
    TRANSLATE_TARGET: "es",
    SUBTITLE_FORMAT: "srt",
  },
  Bs = { FILE_POLL: 500 },
  p = l(null),
  z = l(null),
  B = l([]),
  lt = l(!1);
l(!1);
const nt = l("local");
l(!1);
const S = l([]),
  O = l("srt"),
  ut = l(""),
  pt = l(0),
  dt = l("in_sync"),
  gt = l(!1);
v(() => p.value?.state ?? "stopped");
const Ms = v(() => p.value?.state === "running");
v(() => p.value?.state === "stopping");
v(() => p.value?.chunks_processed ?? 0);
const mt = v(() => {
  const t = p.value?.modules;
  return t ? Object.fromEntries(t.map((e) => [e.name, e])) : {};
});
v(() => {
  const t = mt.value;
  return Object.entries(t)
    .filter(([, e]) => e.enabled)
    .map(([e]) => e);
});
const Ns = v(() => {
    const t = p.value,
      e = t?.system_metrics ?? t?.system ?? {},
      n = t?.uptime_seconds ?? 0,
      s = t?.chunks_processed ?? 0,
      r = n > 0 ? s / n : 0;
    return {
      cpu: e.cpu_percent ?? e.cpu_usage ?? 0,
      memoryMb: e.memory_mb ?? 0,
      memoryPercent: e.memory_percent ?? e.memory_usage ?? 0,
      gpuUtil: e.gpu_percent ?? e.gpu_usage ?? e.gpu_util ?? 0,
      gpuMemMb: e.gpu_memory_mb ?? e.gpu_memory ?? 0,
      gpuMemPercent: e.gpu_memory_percent ?? e.gpu_memory_usage ?? 0,
      chunksPerSec: r,
      totalChunks: s,
    };
  }),
  Ds = v(() => {
    const t = z.value,
      n = p.value?.network?.public_ip,
      s = ut.value || n || "",
      r = nt.value === "remote" ? s || "localhost" : "127.0.0.1",
      o = z.value?.input?.type ?? "srt";
    O.value = o;
    const c = t?.input?.srt?.port ?? 9e3;
    t?.input?.srt?.mode, t?.input?.srt?.latency_ms;
    const u = t?.input?.rtmp?.port ?? 1935,
      d = t?.server?.port ?? 9999,
      g = `srt://${r}:${c}`,
      E = `rtmp://${r}:${u}`,
      T = `http://${r}:${d}/hls/stream.m3u8`,
      C = `http://${r}:${d}/player`;
    return {
      host: r,
      inputType: o,
      srtUrl: g,
      rtmpUrl: E,
      streamUrl: T,
      playerUrl: C,
      srtLabel: o === "rtmp" ? "RTMP:" : "SRT:",
      primaryUrl: o === "rtmp" ? E : g,
      primaryLabel: o === "rtmp" ? "RTMP:" : "SRT:",
    };
  }),
  Gs = v(() => {
    const t = S.value;
    return t.length === 0 ? 0 : t.reduce((e, n) => e + n, 0) / t.length;
  }),
  Fs = v(() => {
    const t = p.value?.avg_processing_time_ms ?? 0;
    return t > 0 ? (t * 6) / 1e3 : 0;
  }),
  J = l([]),
  K = l([]),
  qs = l(!1),
  Hs = l("en"),
  js = l("dark"),
  Vs = l([]),
  Ws = l("");
function zs(t) {
  p.value = t;
  const e = t?.uptime_seconds ?? 0,
    n = t?.chunks_processed ?? 0,
    s = t?.avg_processing_time_ms ?? 0,
    r = s > 0 ? 1e3 / s : e > 0 ? n / e : 0;
  if (r > 0) {
    const d = [...S.value, r];
    S.value = d.slice(-60);
  }
  const o = t.system_metrics ?? t.system ?? {},
    c = o.cpu_percent ?? o.cpu_usage ?? 0,
    u = o.gpu_percent ?? o.gpu_usage ?? o.gpu_util ?? 0;
  c > 0 && (J.value = [...J.value, c].slice(-60)),
    u > 0 && (K.value = [...K.value, u].slice(-60));
}
function Js(t, e) {
  const n = { timestamp: new Date().toISOString(), level: t, message: e };
  B.value = [...B.value.slice(-999), n];
}
function Ks() {
  S.value = [];
}
function Ys(t) {
  const e = Math.floor(t / 60),
    n = Math.floor(t % 60);
  return `${e}:${n.toString().padStart(2, "0")}`;
}
function ft(t) {
  return (typeof t == "string" ? new Date(t) : new Date(t)).toLocaleTimeString(
    "en-US",
    { hour12: !1 },
  );
}
async function Zs(t) {
  try {
    return await navigator.clipboard.writeText(t), !0;
  } catch {
    return !1;
  }
}
function Qs(t, e = "info") {
  const n = document.createElement("div");
  (n.className = `toast toast-${e}`),
    (n.textContent = t),
    document.body.appendChild(n),
    setTimeout(() => n.remove(), 3e3);
}
const _t = "ACTIVO",
  vt = "ERROR",
  yt = "DETENIENDO",
  ht = "APAGADO",
  Et = "WS ON",
  Lt = "WS OFF",
  St = "Iniciando pipeline...",
  $t = "Pipeline iniciado",
  Tt = "Deteniendo pipeline...",
  Ct = "Pipeline detenido",
  bt = "¿Estás seguro de que quieres detener el pipeline?",
  xt = "Reproduciendo archivo",
  It = "Archivo pausado",
  kt = "Error al buscar",
  wt = "Error",
  At = "Cargando...",
  Rt = "Éxito",
  Pt = "Error de inicialización",
  Ot = "URL copiada",
  Ut = "Error al copiar URL",
  Bt = "Error al cargar presets",
  Mt = "Aplicando preset",
  Nt = "Preset aplicado",
  Dt = "Error de preset",
  Gt = "Guardando preset",
  Ft = "Preset guardado",
  qt = "Error al guardar preset",
  Ht = "Guardando configuración...",
  jt = "Chunk sincronizado",
  Vt = "Configuración guardada",
  Wt = "Error al guardar configuración",
  zt = "Error al exportar configuración",
  Jt = "Configuración exportada",
  Kt = "Error de WebSocket",
  Yt = "Reconexión fallida",
  Zt = "WebSocket desconectado",
  Qt = "Entrada",
  Xt = "Tipo",
  te = "Archivo",
  ee = "Puerto SRT",
  ne = "Modo",
  se = "Escuchador",
  oe = "Llamador",
  re = "Rendezvous",
  ce = "Chunk",
  ae = "Latencia (ms)",
  ie = "Dirección del llamador",
  le = "Puerto",
  ue = "URL OBS",
  pe = "App",
  de = "Clave de stream",
  ge = "Ruta del archivo de video",
  me = "Seleccionar archivo",
  fe = "Selecciona un archivo de video para procesar",
  _e = "Reproducir",
  ve = "Pausar",
  ye = "Reiniciar",
  he = "Bucle",
  Ee = "No",
  Le = "Sí",
  Se = "Velocidad",
  $e = "Métricas",
  Te = "Tiempo",
  Ce = "Chunks",
  be = "Codificador",
  xe = "Selector de idioma",
  Ie = "Docs",
  ke = "Atajos de teclado",
  we = "Seguridad desactivada",
  Ae = "Token de autenticación",
  Re = "Cerrar panel",
  Pe = "Ingresa token...",
  Oe = "Mostrar/Ocultar",
  Ue = "Generar token",
  Be = "Guardar token",
  Me = "Guardar configuración",
  Ne = {
    status_active: _t,
    status_error: vt,
    status_stopping: yt,
    status_off: ht,
    ws_on: Et,
    ws_off: Lt,
    pipeline_starting: St,
    pipeline_started: $t,
    pipeline_stopping: Tt,
    pipeline_stopped: Ct,
    confirm_stop: bt,
    input_file_play: xt,
    input_file_pause: It,
    input_file_seek_error: kt,
    error: wt,
    loading: At,
    success: Rt,
    init_error: Pt,
    url_copied: Ot,
    url_copy_error: Ut,
    presets_load_error: Bt,
    preset_applying: Mt,
    preset_applied: Nt,
    preset_error: Dt,
    preset_saving: Gt,
    preset_saved: Ft,
    preset_save_error: qt,
    saving_config: Ht,
    chunk_synced: jt,
    config_saved: Vt,
    config_save_error: Wt,
    config_export_error: zt,
    config_exported: Jt,
    ws_error: Kt,
    reconnect_failed: Yt,
    ws_disconnected: Zt,
    input: Qt,
    type: Xt,
    file_input: te,
    srt_port: ee,
    mode: ne,
    listener: se,
    caller: oe,
    rendezvous: re,
    chunk: ce,
    latency_ms: ae,
    caller_address: ie,
    port: le,
    obs_url: ue,
    app: pe,
    stream_key: de,
    video_file_path: ge,
    select_file: me,
    file_hint: fe,
    play: _e,
    pause: ve,
    restart: ye,
    loop: he,
    no: Ee,
    yes: Le,
    speed: Se,
    metrics: $e,
    time: Te,
    chunks: Ce,
    encoder: be,
    language_selector: xe,
    docs: Ie,
    keyboard_shortcuts: ke,
    security_off: we,
    auth_token: Ae,
    close_panel: Re,
    token_placeholder: Pe,
    show_hide: Oe,
    generate_token: Ue,
    save_token: Be,
    save_config: Me,
  },
  De = "ACTIVO",
  Ge = "ERROR",
  Fe = "DETENIENDO",
  qe = "APAGADO",
  He = "WS ON",
  je = "WS OFF",
  Ve = "Iniciando pipeline...",
  We = "Pipeline iniciado",
  ze = "Deteniendo pipeline...",
  Je = "Pipeline detenido",
  Ke = "¿Estás seguro de que quieres detener el pipeline?",
  Ye = "Reproduciendo archivo",
  Ze = "Archivo pausado",
  Qe = "Error al buscar",
  Xe = "Error",
  tn = "Cargando...",
  en = "Éxito",
  nn = "Error de inicialización",
  sn = "URL copiada",
  on = "Error al copiar URL",
  rn = "Error al cargar presets",
  cn = "Aplicando preset",
  an = "Preset aplicado",
  ln = "Error de preset",
  un = "Guardando preset",
  pn = "Preset guardado",
  dn = "Error al guardar preset",
  gn = "Guardando configuración...",
  mn = "Chunk sincronizado",
  fn = "Configuración guardada",
  _n = "Error al guardar configuración",
  vn = "Error al exportar configuración",
  yn = "Configuración exportada",
  hn = "Error de WebSocket",
  En = "Reconexión fallida",
  Ln = "WebSocket desconectado",
  Sn = "Entrada",
  $n = "Tipo",
  Tn = "Archivo",
  Cn = "Puerto SRT",
  bn = "Modo",
  xn = "Escuchador",
  In = "Llamador",
  kn = "Rendezvous",
  wn = "Chunk",
  An = "Latencia (ms)",
  Rn = "Dirección del llamador",
  Pn = "Puerto",
  On = "URL OBS",
  Un = "App",
  Bn = "Clave de stream",
  Mn = "Ruta del archivo de video",
  Nn = "Seleccionar archivo",
  Dn = "Selecciona un archivo de video para procesar",
  Gn = "Reproducir",
  Fn = "Pausar",
  qn = "Reiniciar",
  Hn = "Bucle",
  jn = "No",
  Vn = "Sí",
  Wn = "Velocidad",
  zn = "Métricas",
  Jn = "Tiempo",
  Kn = "Chunks",
  Yn = "Codificador",
  Zn = "Selector de idioma",
  Qn = "Docs",
  Xn = "Atajos de teclado",
  ts = "Seguridad desactivada",
  es = "Token de autenticación",
  ns = "Cerrar panel",
  ss = "Ingresa token...",
  os = "Mostrar/Ocultar",
  rs = "Generar token",
  cs = "Guardar token",
  as = "Guardar configuración",
  is = {
    status_active: De,
    status_error: Ge,
    status_stopping: Fe,
    status_off: qe,
    ws_on: He,
    ws_off: je,
    pipeline_starting: Ve,
    pipeline_started: We,
    pipeline_stopping: ze,
    pipeline_stopped: Je,
    confirm_stop: Ke,
    input_file_play: Ye,
    input_file_pause: Ze,
    input_file_seek_error: Qe,
    error: Xe,
    loading: tn,
    success: en,
    init_error: nn,
    url_copied: sn,
    url_copy_error: on,
    presets_load_error: rn,
    preset_applying: cn,
    preset_applied: an,
    preset_error: ln,
    preset_saving: un,
    preset_saved: pn,
    preset_save_error: dn,
    saving_config: gn,
    chunk_synced: mn,
    config_saved: fn,
    config_save_error: _n,
    config_export_error: vn,
    config_exported: yn,
    ws_error: hn,
    reconnect_failed: En,
    ws_disconnected: Ln,
    input: Sn,
    type: $n,
    file_input: Tn,
    srt_port: Cn,
    mode: bn,
    listener: xn,
    caller: In,
    rendezvous: kn,
    chunk: wn,
    latency_ms: An,
    caller_address: Rn,
    port: Pn,
    obs_url: On,
    app: Un,
    stream_key: Bn,
    video_file_path: Mn,
    select_file: Nn,
    file_hint: Dn,
    play: Gn,
    pause: Fn,
    restart: qn,
    loop: Hn,
    no: jn,
    yes: Vn,
    speed: Wn,
    metrics: zn,
    time: Jn,
    chunks: Kn,
    encoder: Yn,
    language_selector: Zn,
    docs: Qn,
    keyboard_shortcuts: Xn,
    security_off: ts,
    auth_token: es,
    close_panel: ns,
    token_placeholder: ss,
    show_hide: os,
    generate_token: rs,
    save_token: cs,
    save_config: as,
  },
  ls = ["en", "es"],
  Y = { en: Ne, es: is };
let M = "en";
function Xs() {
  if (typeof window < "u") {
    const t = localStorage.getItem(it.LANGUAGE);
    t && ls.includes(t) && (M = t);
  }
  return M;
}
function _(t) {
  return Y[M][t] || Y.en[t] || t;
}
let i = null,
  N = null,
  f = null,
  k = null,
  D = null,
  w = null,
  Z = null,
  Q = null;
const us = 1e3;
let y = "",
  h = "ALL",
  b = !0,
  U = null;
function ps() {
  N &&
    ((b = !b),
    N.classList.toggle("collapsed", b),
    D && (D.textContent = b ? "▶" : "▼"));
}
function ds(t) {
  const e = document.createElement("div");
  return (e.textContent = t), e.innerHTML;
}
function gs(t, e, n) {
  if (!i) return;
  f && f.parentElement === i && (f.remove(), (f = null));
  const s = document.createElement("div");
  (s.className = "log-entry"),
    s.setAttribute("role", "listitem"),
    (s.dataset.level = t),
    (s.dataset.message = e.toLowerCase());
  const r = n ? ft(n) : new Date().toLocaleTimeString("es-ES"),
    o = t.toLowerCase();
  for (
    s.innerHTML = `
    <span class="log-timestamp">${r}</span>
    <span class="log-level ${o}">[${t}]</span>
    <span class="log-message">${ds(e)}</span>
  `,
      ms(t, e) || (s.style.display = "none"),
      i.appendChild(s);
    i.children.length > us;

  )
    i.firstChild && i.removeChild(i.firstChild);
  (i.scrollTop = i.scrollHeight), st();
}
function ms(t, e) {
  const n = t.toUpperCase();
  return !(
    (h !== "ALL" && n !== h) ||
    (y && !e.toLowerCase().includes(y.toLowerCase()))
  );
}
function st() {
  if (!i) return;
  const t = i.querySelectorAll(".log-entry"),
    e = { ALL: 0, INFO: 0, WARNING: 0, ERROR: 0 };
  t.forEach((s) => {
    const r = s.dataset.level?.toUpperCase() || "INFO";
    e[r] !== void 0 && e[r]++, e.ALL++;
  }),
    i.parentElement?.querySelectorAll(".level-badge")?.forEach((s) => {
      const r = s.dataset.level;
      r && r in e && (s.textContent = String(e[r]));
    });
}
function fs(t) {
  U && clearTimeout(U),
    (U = setTimeout(() => {
      (y = t.toLowerCase()), ot();
    }, 200));
}
function _s(t) {
  (h = t), ot();
}
function ot() {
  i?.querySelectorAll(".log-entry")?.forEach((e) => {
    const n = e,
      s = (n.dataset.level || "INFO").toUpperCase(),
      r = n.dataset.message || "",
      o = h === "ALL" || s === h,
      c = !y || r.includes(y);
    n.style.display = o && c ? "" : "none";
  }),
    st();
}
function X() {
  const t = i?.querySelectorAll(".log-entry:not([style*='display: none'])");
  if (!t || t.length === 0) {
    alert(_("no_logs"));
    return;
  }
  const e = [];
  t.forEach((r) => {
    const o = r,
      c = o.querySelector(".log-timestamp")?.textContent || "",
      u = o.querySelector(".log-level")?.textContent || "",
      d = o.querySelector(".log-message")?.textContent || "";
    e.push({
      timestamp: c,
      level: u.replace("[", "").replace("]", ""),
      message: d,
    });
  });
  const n = new Blob([JSON.stringify(e, null, 2)], {
      type: "application/json",
    }),
    s = new Date().toISOString().split("T")[0];
  rt(n, `srt2web-logs-${s}.json`);
}
function tt() {
  const t = i?.querySelectorAll(".log-entry:not([style*='display: none'])");
  if (!t || t.length === 0) {
    alert(_("no_logs"));
    return;
  }
  const e = [];
  t.forEach((r) => {
    const o = r,
      c = o.querySelector(".log-timestamp")?.textContent || "",
      u = o.querySelector(".log-level")?.textContent || "",
      d = o.querySelector(".log-message")?.textContent || "";
    e.push(`[${c}] ${u} ${d}`);
  });
  const n = new Blob(
      [
        e.join(`
`),
      ],
      { type: "text/plain" },
    ),
    s = new Date().toISOString().split("T")[0];
  rt(n, `srt2web-logs-${s}.txt`);
}
function rt(t, e) {
  const n = URL.createObjectURL(t),
    s = document.createElement("a");
  (s.href = n), (s.download = e), s.click(), URL.revokeObjectURL(n);
}
function vs() {
  const t = i?.querySelectorAll(".log-entry").length || 0;
  (t > 50 && !confirm(`${_("confirm_delete")} (${t})`)) ||
    (i &&
      ((i.innerHTML = ""),
      (f = document.createElement("div")),
      (f.className = "log-empty"),
      (f.id = "log-empty"),
      (f.innerHTML = `
    <span class="log-empty-icon">📝</span>
    <span class="log-empty-text">${_("no_logs_yet")}</span>
  `),
      i.appendChild(f),
      (y = ""),
      (h = "ALL"),
      k && (k.value = ""),
      w && (w.value = "ALL")));
}
function to() {
  (i = document.getElementById("log-content")),
    (N = document.querySelector(".log-panel")),
    (f = document.getElementById("log-empty")),
    (k = document.getElementById("log-search")),
    (D = document.getElementById("log-collapse-icon")),
    (w = document.getElementById("log-level-filter")),
    (Z = document.getElementById("btn-export-json")),
    (Q = document.getElementById("btn-export-txt")),
    k?.addEventListener("input", (t) => {
      const e = t.target.value;
      fs(e);
    }),
    w?.addEventListener("change", (t) => {
      const e = t.target.value;
      _s(e);
    }),
    Z?.addEventListener("click", (t) => {
      t.stopPropagation(), X();
    }),
    Q?.addEventListener("click", (t) => {
      t.stopPropagation(), tt();
    }),
    (window.toggleLogPanel = ps),
    (window.clearLogs = vs),
    (window.exportLogsJson = X),
    (window.exportLogsTxt = tt);
}
function a(t) {
  return document.getElementById(t);
}
function ys() {
  m(() => {
    const t = p.value,
      e = a("status-dot"),
      n = a("status-text"),
      s = a("btn-start"),
      r = a("btn-stop");
    if (!e || !n) return;
    const o = t?.state === "running",
      c = t?.state === "stopping",
      u = t?.state === "error";
    (e.className = "status-dot"),
      e.classList.toggle("running", o),
      e.classList.toggle("error", u),
      e.classList.toggle("stopped", !o && !u && !c),
      (n.textContent = _(
        o
          ? "status_active"
          : u
            ? "status_error"
            : c
              ? "status_stopping"
              : "status_off",
      )),
      s && ((s.disabled = o), (s.style.opacity = o ? "0.5" : "1")),
      r && ((r.disabled = !o), (r.style.opacity = o ? "1" : "0.5"));
  });
}
function hs() {
  m(() => {
    const t = p.value,
      e = t?.modules || [],
      n = t?.state === "running",
      s = [
        "indicator-input",
        "indicator-whisper",
        "indicator-translate",
        "indicator-tts",
        "indicator-subtitles",
        "indicator-mixer",
        "indicator-muxer",
        "indicator-output",
      ];
    for (const r of s) {
      const o = a(r);
      if (!o) continue;
      const c = r.replace("indicator-", ""),
        u = e.find(
          (g) =>
            g.name === c ||
            (c === "input" && g.name === "input") ||
            (c === "whisper" && g.name === "transcriber") ||
            (c === "translate" && g.name === "translator") ||
            (c === "tts" && g.name === "tts_engine") ||
            (c === "subtitles" && g.name === "subtitle_generator") ||
            (c === "mixer" && g.name === "audio_mixer") ||
            (c === "muxer" && g.name === "video_muxer") ||
            (c === "output" && g.name === "output"),
        ),
        d = n && u?.enabled;
      o.classList.toggle("active", !!d), o.classList.toggle("inactive", !d);
    }
  });
}
function Es() {
  m(() => {
    const t = p.value,
      e = t?.system || t?.system_metrics || {},
      n = a("metric-cpu"),
      s = a("metric-cpu-value"),
      r = a("metric-cpu-bar"),
      o = e.cpu_percent ?? e.cpu_usage ?? 0;
    s && (s.textContent = `${o}%`),
      r && (r.style.width = `${o}%`),
      n &&
        (n.classList.toggle("warning", o > 70 && o <= 90),
        n.classList.toggle("critical", o > 90));
    const c = a("metric-memory-value"),
      u = a("metric-memory-percent"),
      d = a("metric-memory-bar"),
      g = e.memory_mb ?? 0,
      E = e.memory_percent ?? e.memory_usage ?? 0;
    c && (c.textContent = `${g.toFixed(0)} MB`),
      u && (u.textContent = `${E}%`),
      d && (d.style.width = `${E}%`);
    const T = a("metric-gpu-value"),
      C = a("metric-gpu-bar"),
      W = e.gpu_usage ?? 0;
    T && (T.textContent = `${W}%`), C && (C.style.width = `${W}%`);
  });
}
function Ls() {
  m(() => {
    const e = p.value?.modules || [];
    for (const n of e) {
      const s = a(`module-time-${n.name}`),
        r = a(`module-chunks-${n.name}`);
      if (s) {
        const o = n.last_process_time_ms ?? 0;
        s.textContent =
          o > 0 ? (o >= 1e3 ? `${(o / 1e3).toFixed(1)}s` : `${o}ms`) : "--";
      }
      r && (r.textContent = String(n.processed_chunks ?? 0));
    }
  });
}
function Ss() {
  m(() => {
    const t = S.value,
      e = a("metric-throughput-value");
    if (e && t.length > 0) {
      const n = t.reduce((s, r) => s + r, 0) / t.length;
      e.textContent = `${n.toFixed(2)}/s`;
    } else e && (e.textContent = "0.00/s");
  });
}
function $s() {
  m(() => {
    const e = p.value?.modules || [];
    for (const n of e) {
      const s = a(`gpu-badge-${n.name}`);
      if (!s) continue;
      const r =
        n.extra?.using_gpu ||
        n.extra?.device === "cuda" ||
        n.extra?.device === "mps";
      (s.style.display = r ? "inline" : "none"),
        s.classList.toggle("active", !!r);
    }
  });
}
function Ts() {
  m(() => {
    const t = a("ws-status-badge");
    t &&
      (lt.value
        ? ((t.textContent = _("ws_on")), t.classList.add("active"))
        : ((t.textContent = _("ws_off")), t.classList.remove("active")));
  });
}
function Cs() {
  m(() => {
    const t = nt.value,
      e = a("remote-config"),
      n = a("btn-mode-local"),
      s = a("btn-mode-remote");
    e && (e.style.display = t === "remote" ? "" : "none"),
      n && n.classList.toggle("active", t === "local"),
      s && s.classList.toggle("active", t === "remote");
  });
}
let x = null;
function bs() {
  const t = () => {
    const e = a("live-clock");
    e &&
      (e.textContent = new Date().toLocaleTimeString("en-US", { hour12: !1 }));
  };
  t(),
    (x = setInterval(t, 1e3)),
    m(() => {
      p.value;
    });
}
function xs() {
  m(() => {
    const t = p.value?.sync;
    t &&
      ((pt.value = t.drift_ms ?? 0),
      (dt.value = t.state ?? "in_sync"),
      (gt.value = t.correction_active ?? !1));
  });
}
let G = 0;
function Is() {
  m(() => {
    const t = B.value,
      e = t.slice(G);
    for (const n of e) gs(n.level, n.message, n.timestamp);
    G = t.length;
  });
}
function ks() {
  m(() => {
    const t = a("pipeline-indicator");
    t && t.classList.toggle("active", p.value?.state === "running");
  });
}
function eo() {
  ys(), hs(), Es(), Ls(), Ss(), $s(), Ts(), Cs(), bs(), xs(), Is(), ks();
}
function no() {
  x && (clearInterval(x), (x = null)), (G = 0);
}
const et = {
  config: null,
  status: null,
  localMode: "local",
  wsConnected: !1,
  logs: [],
  isLoading: !1,
  error: null,
  outputs: [],
};
class ws {
  state;
  listeners = new Set();
  history = [];
  maxHistoryLength = 20;
  constructor(e = {}) {
    this.state = { ...et, ...e };
  }
  getState() {
    return Object.freeze({ ...this.state });
  }
  setState(e) {
    const n = this.state,
      s = { ...n, ...e };
    Object.keys(e).some((o) => n[o] !== s[o]) &&
      (this.history.push({ ...n }),
      this.history.length > this.maxHistoryLength && this.history.shift(),
      (this.state = s),
      this.notify());
  }
  subscribe(e) {
    return (
      this.listeners.add(e),
      e(this.getState()),
      () => {
        this.listeners.delete(e);
      }
    );
  }
  notify() {
    const e = this.getState();
    this.listeners.forEach((n) => {
      try {
        n(e);
      } catch (s) {
        console.error("[Store] Error in listener:", s);
      }
    });
  }
  reset() {
    (this.state = { ...et }), this.notify();
  }
  getHistory() {
    return Object.freeze([...this.history]);
  }
  setConfig(e) {
    this.setState({ config: e });
  }
  setStatus(e) {
    this.setState({ status: e, error: null });
  }
  setWsConnected(e) {
    this.setState({ wsConnected: e });
  }
  addLog(e) {
    const n = [...this.state.logs, e].slice(-500);
    this.setState({ logs: n });
  }
  setLoading(e) {
    this.setState({ isLoading: e });
  }
  setError(e) {
    this.setState({ error: e, isLoading: !1 });
  }
  setOutputs(e) {
    this.setState({ outputs: e });
  }
  clearLogs() {
    this.setState({ logs: [] });
  }
}
new ws();
let F = null,
  q = null,
  H = null,
  j = null,
  $ = null,
  A = null,
  R = null,
  P = null,
  L = null,
  I = null,
  V = null;
function As() {
  (F = document.getElementById("input-type")),
    (q = document.getElementById("input-srt-settings")),
    (H = document.getElementById("input-rtmp-settings")),
    (j = document.getElementById("input-file-settings")),
    ($ = document.getElementById("input-rtmp-url")),
    (A = document.getElementById("input-rtmp-port")),
    (R = document.getElementById("input-rtmp-app")),
    (P = document.getElementById("input-rtmp-key")),
    (L = document.getElementById("btn-copy-rtmp")),
    (I = document.getElementById("input-file-select")),
    (V = document.getElementById("btn-file-select")),
    document.getElementById("input-file-chunk"),
    document.getElementById("input-rtmp-chunk"),
    Rs(),
    ct(O.value);
}
function Rs() {
  F &&
    F.addEventListener("change", (e) => {
      const n = e.target.value;
      O.value = n;
    });
  function t() {
    at();
  }
  [A, R, P].forEach((e) => {
    e?.addEventListener("input", t), e?.addEventListener("change", t);
  }),
    L &&
      L.addEventListener("click", () => {
        $?.value &&
          navigator.clipboard &&
          navigator.clipboard.writeText($.value).then(() => {
            (L.textContent = "✓"),
              setTimeout(() => (L.textContent = "📋"), 1e3);
          });
      }),
    V &&
      I &&
      (V.addEventListener("click", () => I?.click()),
      I.addEventListener("change", (e) => {
        const n = e.target;
        if (n.files && n.files.length > 0) {
          const s = n.value || n.files[0].name,
            r = document.getElementById("input-file-path");
          r && (r.value = s);
        }
      }));
}
m(() => {
  const t = O.value;
  ct(t);
});
function ct(t) {
  q && (q.style.display = t === "srt" ? "flex" : "none"),
    H && (H.style.display = t === "rtmp" ? "flex" : "none"),
    j && (j.style.display = t === "file" ? "flex" : "none");
  const e = document.getElementById("input-process-title"),
    n = {
      srt: "📥 INPUT (SRT)",
      rtmp: "📥 INPUT (RTMP)",
      file: "📥 INPUT (Archivo)",
    };
  e && (e.textContent = n[t] || "📥 INPUT"), t === "rtmp" && at();
}
function at() {
  if (!$ || !A || !R || !P) return;
  const t = A.value || "1935",
    e = R.value || "live",
    n = P.value || "stream";
  $.value = `rtmp://127.0.0.1:${t}/${e}/${n}`;
}
document.addEventListener("DOMContentLoaded", As);
export {
  K as A,
  S as B,
  Ms as C,
  Us as D,
  Os as E,
  Bs as I,
  it as S,
  js as a,
  Js as b,
  Hs as c,
  z as d,
  Qs as e,
  Ys as f,
  p as g,
  nt as h,
  Xs as i,
  ut as j,
  Zs as k,
  to as l,
  eo as m,
  no as n,
  Ds as o,
  Vs as p,
  Ns as q,
  Ks as r,
  Ws as s,
  _ as t,
  zs as u,
  Gs as v,
  lt as w,
  Fs as x,
  qs as y,
  J as z,
};
