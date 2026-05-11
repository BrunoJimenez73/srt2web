const d = { AUTH_TOKEN: "srt2web_auth_token" },
  A = {
    PIPELINE_STARTING: "Iniciando pipeline...",
    PIPELINE_STARTED: "Pipeline iniciado correctamente",
    PIPELINE_STOPPING: "Deteniendo pipeline...",
    PIPELINE_STOPPED: "Pipeline detenido",
    PIPELINE_CONFIRM_STOP: "¿Está seguro que desea detener el pipeline?",
    CONFIG_SAVED: "Configuración guardada correctamente",
    CONFIG_SAVE_ERROR: "Error al guardar configuración",
    CONFIG_LOAD_ERROR: "Error al cargar configuración",
    INPUT_FILE_SELECTED:
      "Archivo seleccionado. Ingrese la ruta completa manualmente.",
    INPUT_FILE_PLAY: "Reproducción reanudada",
    INPUT_FILE_PAUSE: "Reproducción pausada",
    INPUT_FILE_SEEK_ERROR: "Error al buscar posición",
    URL_COPIED: "URL copiada al portapapeles",
    URL_COPY_ERROR: "Error al copiar URL",
    WS_CONNECTED: "Conectado al servidor",
    WS_DISCONNECTED: "WebSocket desconectado",
    WS_ERROR: "Error de conexión WebSocket",
    LOADING: "Cargando...",
    ERROR: "Ha ocurrido un error",
    SUCCESS: "Operación completada correctamente",
    WARNING: "Advertencia",
    INFO: "Información",
    TOAST_DURATION: 3e3,
    LOG_PANEL_PLACEHOLDER: "Esperando logs...",
    LOG_SEARCH_PLACEHOLDER: "Buscar en logs...",
    LOG_CLEAR: "Limpiar logs",
    OUTPUT_CREATED: "Salida creada correctamente",
    OUTPUT_REMOVED: "Salida eliminada",
    OUTPUT_TOGGLED: "Estado de salida actualizado",
  },
  O = {
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
  R = {
    STATUS_POLL: 5e3,
    FILE_POLL: 500,
    SEEK_DEBOUNCE: 100,
    RECONNECT_BASE: 1e3,
    MAX_RECONNECT_ATTEMPTS: 5,
  },
  l = d.AUTH_TOKEN;
function u() {
  return typeof window > "u" ? null : localStorage.getItem(l);
}
function h(e) {
  typeof window > "u" ||
    (e ? localStorage.setItem(l, e) : localStorage.removeItem(l));
}
function S() {
  return typeof window > "u"
    ? "http://localhost:9999"
    : `${window.location.protocol}//${window.location.host}`;
}
function I(e = "/ws/logs") {
  const t = window.location.protocol === "https:" ? "wss:" : "ws:",
    n = u(),
    o = `${t}//${window.location.host}${e}`;
  return n ? `${o}?token=${encodeURIComponent(n)}` : o;
}
async function _(e, t = {}, n = 15e3) {
  const o = u(),
    r = new Headers(t.headers);
  o && r.set("Authorization", `Bearer ${o}`);
  const a = new AbortController(),
    i = setTimeout(() => a.abort(), n);
  try {
    return await fetch(e, { ...t, headers: r, signal: a.signal });
  } finally {
    clearTimeout(i);
  }
}
class p extends Error {
  constructor(t, n, o) {
    super(t),
      (this.status = n),
      (this.statusText = o),
      (this.name = "ApiError");
  }
}
async function c(e, t, n, o = 15e3) {
  const r = S(),
    a = t.replace(/^\/+/, ""),
    i = a ? `${r}/${a}` : r,
    E = { method: e };
  n &&
    ((E.body = JSON.stringify(n)),
    (E.headers = { "Content-Type": "application/json" }));
  const s = await _(i, E, o);
  if (!s.ok) {
    const T = await s.text().catch(() => s.statusText);
    throw new p(`${s.status} ${s.statusText}: ${T}`, s.status, s.statusText);
  }
  return s.json();
}
async function P() {
  return c("GET", "/api/config");
}
async function N(e) {
  return c("POST", "/api/config/chunk", { chunk_duration_sec: e });
}
async function L() {
  return c("POST", "/api/start");
}
async function C() {
  return c("POST", "/api/stop");
}
async function f() {
  return c("GET", "/api/status");
}
class m {
  ws = null;
  url;
  onMessageHandler;
  onErrorHandler;
  onCloseHandler;
  reconnectAttempts = 0;
  maxReconnectAttempts = 5;
  reconnectDelay = 1e3;
  constructor(t) {
    this.url = t;
  }
  connect() {
    (this.ws = new WebSocket(this.url)),
      (this.ws.onopen = () => {
        this.reconnectAttempts = 0;
      }),
      (this.ws.onmessage = (t) => {
        try {
          const n = JSON.parse(t.data);
          this.onMessageHandler?.(n);
        } catch {
          console.error("Failed to parse WebSocket message:", t.data);
        }
      }),
      (this.ws.onerror = (t) => {
        console.error("[WS] Error:", t), this.onErrorHandler?.(t);
      }),
      (this.ws.onclose = () => {
        this.onCloseHandler?.(), this.attemptReconnect();
      });
  }
  attemptReconnect() {
    this.reconnectAttempts < this.maxReconnectAttempts &&
      (this.reconnectAttempts++,
      setTimeout(() => {
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts));
  }
  onMessage(t) {
    return (this.onMessageHandler = t), this;
  }
  onError(t) {
    return (this.onErrorHandler = t), this;
  }
  onClose(t) {
    return (this.onCloseHandler = t), this;
  }
  send(t) {
    this.ws?.send(JSON.stringify(t));
  }
  close() {
    (this.reconnectAttempts = this.maxReconnectAttempts),
      this.ws?.close(),
      (this.ws = null);
  }
  isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
export {
  O as D,
  R as I,
  A as M,
  m as W,
  c as a,
  P as b,
  I as c,
  L as d,
  f as e,
  C as f,
  u as g,
  h as s,
  N as u,
};
