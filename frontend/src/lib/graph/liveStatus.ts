/**
 * Hook de React para estado en vivo de los módulos del pipeline.
 *
 * Combina dos fuentes:
 * 1. Polling a `GET /api/modules` cada 2s para `state`, `processed_chunks`,
 *    `last_process_time_ms`, `extra.gpu_info`, etc.
 * 2. WebSocket `WS /ws/logs` para eventos de log por módulo. Cuando llega
 *    un log con `module` y un `correlation_id`, marca ese módulo como
 *    `pulse=true` durante `PULSE_DURATION_MS` ms.
 *
 * El hook retorna un `Map<NodeKind, LiveNodeStatus>` que `ModuleNode`
 * consume para pintar su badge y su borde pulsante.
 */
import { useEffect, useRef, useState } from "react";
import { getModules } from "../api";
import { WSClient, getAuthToken, getWebSocketUrl } from "../api";
import type { ModuleStatus, WebSocketMessage } from "../types/api";
import type { NodeKind } from "./nodeCatalog";

export interface LiveNodeStatus {
  /** Estado textual del backend (`idle`, `running`, `error`, etc.). */
  state: ModuleStatus["state"] | "unknown";
  /** Total de chunks procesados por el módulo. */
  processedChunks: number;
  /** Timestamp (ms epoch) del último log recibido para este módulo. */
  lastActiveMs: number;
  /** `true` durante `PULSE_DURATION_MS` ms tras recibir un log. */
  pulse: boolean;
  /** El módulo está habilitado en la config. */
  enabled: boolean;
  /** Info extra (GPU, encoder, etc.) para mostrar en tooltip. */
  extra?: ModuleStatus["extra"];
  /** Error reportado por el módulo. */
  error?: string;
}

export type LiveStatusMap = ReadonlyMap<NodeKind, LiveNodeStatus>;

const PULSE_DURATION_MS = 1500;
const POLL_INTERVAL_MS = 2000;

/** Mapea `ModuleName` (backend, devuelve nombres como "input", "whisper", ...)
 *  a `NodeKind` (frontend, canonical: "transcriber", "tts_engine", ...). */
const MODULE_NAME_TO_KIND: Readonly<Record<string, NodeKind>> = {
  input: "input",
  audio_extractor: "audio_extractor",
  whisper: "transcriber",
  transcriber: "transcriber",
  translator: "translator",
  subtitles: "subtitle_generator",
  subtitle_generator: "subtitle_generator",
  tts: "tts_engine",
  tts_engine: "tts_engine",
  mixer: "audio_mixer",
  audio_mixer: "audio_mixer",
  muxer: "output",
  video_muxer: "output",
  outputs: "output",
};

function moduleNameToKind(name: string | undefined): NodeKind | null {
  if (!name) return null;
  return MODULE_NAME_TO_KIND[name] ?? null;
}

/** Estado inicial vacío para los 8 nodos del catálogo. */
function emptyStatusMap(): Map<NodeKind, LiveNodeStatus> {
  const map = new Map<NodeKind, LiveNodeStatus>();
  const all: NodeKind[] = [
    "input",
    "audio_extractor",
    "transcriber",
    "translator",
    "subtitle_generator",
    "tts_engine",
    "audio_mixer",
    "output",
  ];
  for (const k of all) {
    map.set(k, {
      state: "unknown",
      processedChunks: 0,
      lastActiveMs: 0,
      pulse: false,
      enabled: true,
    });
  }
  return map;
}

export interface UseLiveModuleStatusOptions {
  /** Si true, no inicia polling ni WS (útil para tests / SSR-safety). */
  disabled?: boolean;
}

export function useLiveModuleStatus(
  options: UseLiveModuleStatusOptions = {},
): LiveStatusMap {
  const { disabled = false } = options;
  const [status, setStatus] = useState<Map<NodeKind, LiveNodeStatus>>(() =>
    emptyStatusMap(),
  );
  const statusRef = useRef(status);
  statusRef.current = status;

  useEffect(() => {
    if (disabled) return;
    let cancelled = false;
    const pulseTimers = new Map<NodeKind, ReturnType<typeof setTimeout>>();

    const applyPulse = (kind: NodeKind) => {
      const prev = pulseTimers.get(kind);
      if (prev) clearTimeout(prev);
      setStatus((prevMap) => {
        const next = new Map(prevMap);
        const cur = next.get(kind);
        next.set(kind, {
          state: cur?.state ?? "unknown",
          processedChunks: cur?.processedChunks ?? 0,
          lastActiveMs: Date.now(),
          pulse: true,
          enabled: cur?.enabled ?? true,
          extra: cur?.extra,
          error: cur?.error,
        });
        return next;
      });
      const timer = setTimeout(() => {
        pulseTimers.delete(kind);
        setStatus((prevMap) => {
          const next = new Map(prevMap);
          const cur = next.get(kind);
          if (!cur || !cur.pulse) return prevMap;
          next.set(kind, { ...cur, pulse: false });
          return next;
        });
      }, PULSE_DURATION_MS);
      pulseTimers.set(kind, timer);
    };

    const applyModules = (modules: ModuleStatus[]) => {
      setStatus((prevMap) => {
        const next = new Map(prevMap);
        for (const m of modules) {
          const kind = moduleNameToKind(m.name);
          if (!kind) continue;
          const cur = next.get(kind);
          next.set(kind, {
            state: m.state,
            processedChunks: m.processed_chunks ?? cur?.processedChunks ?? 0,
            lastActiveMs: cur?.lastActiveMs ?? 0,
            pulse: cur?.pulse ?? false,
            enabled: m.enabled,
            extra: m.extra,
            error: cur?.error,
          });
        }
        return next;
      });
    };

    const fetchOnce = async (): Promise<void> => {
      try {
        const res = await getModules();
        if (!cancelled && res?.modules) applyModules(res.modules);
      } catch {
        // Silenciar errores transitorios de polling
      }
    };

    // Polling inicial + cada POLL_INTERVAL_MS
    void fetchOnce();
    const pollHandle = setInterval(() => {
      void fetchOnce();
    }, POLL_INTERVAL_MS);

    // WebSocket para eventos de log → pulse
    const ws = new WSClient(getWebSocketUrl("/ws/logs"), {
      authToken: getAuthToken(),
    });
    ws.onMessage((msg: WebSocketMessage) => {
      if (msg.type !== "log" || !msg.module) return;
      const kind = moduleNameToKind(msg.module);
      if (!kind) return;
      applyPulse(kind);
    });
    ws.connect();
    void pulseTimers; // (referenced for future teardown)

    return () => {
      cancelled = true;
      clearInterval(pollHandle);
      ws.close();
      for (const t of pulseTimers.values()) clearTimeout(t);
      pulseTimers.clear();
    };
  }, [disabled]);

  return status;
}
