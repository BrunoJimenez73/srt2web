const h = { AUTH_TOKEN: "srt2web_auth_token" },
  S = {
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
  _ = {
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
  R = { FILE_POLL: 500, SEEK_DEBOUNCE: 100 },
  u = h.AUTH_TOKEN;
function d() {
  return typeof window > "u" ? null : localStorage.getItem(u);
}
function O(n) {
  typeof window > "u" ||
    (n ? localStorage.setItem(u, n) : localStorage.removeItem(u));
}
function p() {
  return typeof window > "u"
    ? "http://localhost:9999"
    : `${window.location.protocol}//${window.location.host}`;
}
function m(n = "/ws/logs") {
  return `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${
    window.location.host
  }${n}`;
}
async function T(n, t = {}, e = 15e3) {
  const s = d(),
    a = new Headers(t.headers);
  s && a.set("Authorization", `Bearer ${s}`);
  const r = new AbortController(),
    i = setTimeout(() => r.abort(), e);
  try {
    return await fetch(n, { ...t, headers: a, signal: r.signal });
  } finally {
    clearTimeout(i);
  }
}
class f extends Error {
  constructor(t, e, s) {
    super(t),
      (this.status = e),
      (this.statusText = s),
      (this.name = "ApiError");
  }
}
async function c(n, t, e, s = 15e3) {
  const a = p(),
    r = t.replace(/^\/+/, ""),
    i = r ? `${a}/${r}` : a,
    l = { method: n };
  e &&
    ((l.body = JSON.stringify(e)),
    (l.headers = { "Content-Type": "application/json" }));
  const o = await T(i, l, s);
  if (!o.ok) {
    const E = await o.text().catch(() => o.statusText);
    throw new f(`${o.status} ${o.statusText}: ${E}`, o.status, o.statusText);
  }
  return o.json();
}
async function I() {
  return c("GET", "/api/config");
}
async function P(n) {
  return c("POST", "/api/config/chunk", { chunk_duration_sec: n });
}
async function N() {
  return c("POST", "/api/start");
}
async function L() {
  return c("POST", "/api/stop");
}
async function g() {
  return c("GET", "/api/status");
}
const A = {
  maxReconnectAttempts: 5,
  backoffBase: 1e3,
  maxBackoff: 3e4,
  jitter: 500,
  authToken: null,
};
class w {
  ws = null;
  url;
  onMessageHandler;
  onErrorHandler;
  onCloseHandler;
  reconnectAttempts = 0;
  maxReconnectAttempts;
  backoffBase;
  maxBackoff;
  jitter;
  authToken;
  _isManualClose = !1;
  _authSent = !1;
  constructor(t, e = {}) {
    this.url = t;
    const s = { ...A, ...e };
    (this.maxReconnectAttempts = s.maxReconnectAttempts),
      (this.backoffBase = s.backoffBase),
      (this.maxBackoff = s.maxBackoff),
      (this.jitter = s.jitter),
      (this.authToken = s.authToken ?? null);
  }
  connect() {
    (this._isManualClose = !1),
      (this._authSent = !1),
      (this.ws = new WebSocket(this.url)),
      (this.ws.onopen = () => {
        (this.reconnectAttempts = 0),
          this.authToken && this.sendAuth(this.authToken);
      }),
      (this.ws.onmessage = (t) => {
        try {
          const e = JSON.parse(t.data);
          this.onMessageHandler?.(e);
        } catch {
          console.error("Failed to parse WebSocket message:", t.data);
        }
      }),
      (this.ws.onerror = (t) => {
        console.error("[WS] Error:", t), this.onErrorHandler?.(t);
      }),
      (this.ws.onclose = () => {
        if (!this._isManualClose) {
          const t = this.reconnectAttempts === 0;
          this.onCloseHandler?.(t), this.attemptReconnect();
        }
      });
  }
  calculateBackoff() {
    const t = this.backoffBase * Math.pow(2, this.reconnectAttempts),
      e = Math.random() * this.jitter;
    return Math.min(t + e, this.maxBackoff);
  }
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const t = this.calculateBackoff();
      console.log(
        `[WS] Reconnecting in ${t.toFixed(0)}ms (attempt ${
          this.reconnectAttempts
        }/${this.maxReconnectAttempts})`,
      ),
        setTimeout(() => {
          this.connect();
        }, t);
    } else console.warn("[WS] Max reconnection attempts reached");
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
    (this._isManualClose = !0),
      (this.reconnectAttempts = this.maxReconnectAttempts),
      this.ws?.close(),
      (this.ws = null);
  }
  isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
  getReconnectAttempts() {
    return this.reconnectAttempts;
  }
  sendAuth(t) {
    this.ws?.readyState === WebSocket.OPEN &&
      this.ws.send(JSON.stringify({ type: "auth", token: t }));
  }
}
export {
  _ as D,
  R as I,
  S as M,
  w as W,
  c as a,
  I as b,
  m as c,
  N as d,
  g as e,
  L as f,
  d as g,
  O as s,
  P as u,
};
