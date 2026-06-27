import { logger } from "../utils/logger";

let ws: WebSocket | null = null;
let reconnectAttempts = 0;
let isManualClose = false;
const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_DELAY_MS = 2000;
const MAX_DELAY_MS = 30000;

function getFeedbackUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${protocol}//${window.location.host}/ws/player-feedback`;
  const token = new URLSearchParams(window.location.search).get("token");
  return token ? `${url}?token=${token}` : url;
}

function calculateBackoff(): number {
  const exp = BASE_DELAY_MS * Math.pow(2, reconnectAttempts);
  const jitter = Math.random() * 1000;
  return Math.min(exp + jitter, MAX_DELAY_MS);
}

export function connectFeedbackWs(): void {
  if (
    ws &&
    (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
  ) {
    return;
  }
  isManualClose = false;
  ws = new WebSocket(getFeedbackUrl());

  ws.onopen = () => {
    reconnectAttempts = 0;
    logger.debug("player-feedback", "Connected");
  };

  ws.onclose = () => {
    if (!isManualClose && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      const delay = calculateBackoff();
      reconnectAttempts++;
      logger.info(
        "player-feedback",
        `Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`,
      );
      setTimeout(connectFeedbackWs, delay);
    }
  };

  ws.onerror = () => {
    logger.warn("player-feedback", "WS error");
  };
}

export function disconnectFeedbackWs(): void {
  isManualClose = true;
  if (ws) {
    ws.close();
    ws = null;
  }
}

function send(msg: Record<string, unknown>): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  }
}

let lastBufferPing = 0;

export function sendBufferHealth(
  bufferMs: number,
  targetBufferMs: number,
): void {
  const now = Date.now();
  if (now - lastBufferPing < 2000) return; // throttle to 2s
  lastBufferPing = now;
  send({
    type: "feedback",
    data: {
      buffer_ms: Math.round(bufferMs),
      target_buffer_ms: Math.round(targetBufferMs),
    },
  });
}

export function sendStalled(durationMs: number): void {
  logger.warn("player-feedback", `Stalled ${durationMs}ms`);
  send({ type: "stalled", data: { duration_ms: Math.round(durationMs) } });
}

export function sendBandwidth(bps: number): void {
  send({ type: "bandwidth", data: { bps: Math.round(bps) } });
}

export function sendBuffered(levelMs: number): void {
  send({ type: "buffered", data: { level_ms: Math.round(levelMs) } });
}
