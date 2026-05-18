/**
 * WebSocket Manager - Handles WebSocket connection for logs and status updates.
 */

import { WSClient, getWebSocketUrl, getAuthToken } from "../api";
import type { WebSocketMessage } from "../api";
import { wsConnected } from "../store/index";
import { addLog, updateStatus, resetThroughput } from "../store/index";
import { t } from "../i18n";
import { enterPostStartMode } from "./polling";

let wsClient: WSClient | null = null;

export function getWSClient(): WSClient | null {
  return wsClient;
}

export function connectWebSocket(): void {
  const wsUrl = getWebSocketUrl("/ws/logs");
  const token = getAuthToken();
  wsClient = new WSClient(wsUrl, {
    maxReconnectAttempts: 5,
    backoffBase: 1000,
    authToken: token,
  });

  wsClient.onMessage((data: WebSocketMessage) => {
    if (data.type === "log") {
      addLog(data.level ?? "INFO", data.message ?? "");
    } else if (data.type === "status" && data.status) {
      updateStatus(data.status);
      if (data.status.state === "running") {
        enterPostStartMode();
      }
    }
  });

  wsClient.onError(() => {
    addLog("ERROR", t("ws_error"));
  });

  wsClient.onClose((wasFirstAttempt: boolean) => {
    wsConnected.value = false;
    if (wasFirstAttempt) {
      addLog("WARNING", t("reconnect_failed"));
    } else {
      addLog("ERROR", t("ws_disconnected"));
    }
  });

  wsClient.connect();
}

export function disconnectWebSocket(): void {
  if (wsClient) {
    wsClient.close();
    wsClient = null;
  }
}
