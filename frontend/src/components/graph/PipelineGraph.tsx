/**
 * Componente principal del editor visual de pipeline (`/graph`).
 *
 * Orquesta:
 * - Carga de la config actual (`GET /api/config`) → grafo inicial
 * - Sincronización del grafo → `PUT /api/config`
 * - Selección de nodo → InspectorPanel
 * - Toolbar: Start, Stop, Apply, Reset, Save preset, Load preset
 *
 * Es un componente React puro (sin estado de Astro) para que se pueda
 * hidratar con `client:only="react"` y compartir el árbol con
 * `PipelineCanvas` (que requiere `ReactFlowProvider`).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { PipelineCanvas } from "./PipelineCanvas";
import { InspectorPanel } from "./InspectorPanel";
import { Toolbar, type PresetSummary } from "./Toolbar";
import {
  configToGraph,
  graphToConfig,
  validateTopology,
  type GraphNodeData,
} from "../../lib/graph/serialize";
import {
  startPipeline,
  stopPipeline,
  updateConfig,
  getConfig,
  getStatus,
  fetchWithAuth,
} from "../../lib/api";
import type { Config, Status } from "../../lib/types/api";
import type { Edge, Node } from "@xyflow/react";

type ToastKind = "success" | "error" | "info";

function useToast(): {
  message: string | null;
  kind: ToastKind;
  show: (msg: string, kind?: ToastKind) => void;
} {
  const [toast, setToast] = useState<{
    message: string;
    kind: ToastKind;
  } | null>(null);
  useEffect(() => {
    if (!toast) return;
    const h = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(h);
  }, [toast]);
  return {
    message: toast?.message ?? null,
    kind: toast?.kind ?? "info",
    show: (message: string, kind: ToastKind = "info") =>
      setToast({ message, kind }),
  };
}

const TOAST_COLOR: Record<ToastKind, string> = {
  success: "var(--success)",
  error: "var(--error)",
  info: "var(--text-sec)",
};

export function PipelineGraph() {
  const [config, setConfig] = useState<Config | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [initialNodes, setInitialNodes] = useState<Node[]>([]);
  const [initialEdges, setInitialEdges] = useState<Edge[]>([]);
  const [currentNodes, setCurrentNodes] = useState<Node[]>([]);
  const [currentEdges, setCurrentEdges] = useState<Edge[]>([]);
  const [selectedData, setSelectedData] = useState<GraphNodeData | null>(null);
  const [isApplying, setIsApplying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const toast = useToast();

  // Carga inicial: GET /api/config
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [cfg, sts] = await Promise.all([getConfig(), getStatus()]);
        if (cancelled) return;
        setConfig(cfg);
        setStatus(sts);
        const { nodes, edges } = configToGraph(cfg);
        setInitialNodes(nodes);
        setInitialEdges(edges);
        setCurrentNodes(nodes);
        setCurrentEdges(edges);
      } catch (e) {
        toast.show(`Error cargando config: ${(e as Error).message}`, "error");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Detecta cambios pendientes comparando con initial
  const isDirty = useMemo(() => {
    if (currentNodes.length !== initialNodes.length) return true;
    if (currentEdges.length !== initialEdges.length) return true;
    for (let i = 0; i < currentNodes.length; i++) {
      const n = currentNodes[i],
        m = initialNodes[i];
      if (n.id !== m.id || n.type !== m.type) return true;
      if (n.position.x !== m.position.x || n.position.y !== m.position.y)
        return true;
    }
    for (let i = 0; i < currentEdges.length; i++) {
      const e = currentEdges[i],
        f = initialEdges[i];
      if (e.id !== f.id || e.source !== f.source || e.target !== f.target)
        return true;
      if (
        e.sourceHandle !== f.sourceHandle ||
        e.targetHandle !== f.targetHandle
      )
        return true;
    }
    return false;
  }, [currentNodes, currentEdges, initialNodes, initialEdges]);

  const topology = useMemo(
    () => validateTopology(currentNodes, currentEdges),
    [currentNodes, currentEdges],
  );

  const handleGraphChange = useCallback((nodes: Node[], edges: Edge[]) => {
    setCurrentNodes(nodes);
    setCurrentEdges(edges);
  }, []);

  const handleSelection = useCallback((data: GraphNodeData | null) => {
    setSelectedData(data);
  }, []);

  const handleInspectorChange = useCallback((next: GraphNodeData) => {
    setCurrentNodes((nodes) =>
      nodes.map((n) =>
        n.id === nodeIdForKind(next.kind) ? { ...n, data: next } : n,
      ),
    );
    setSelectedData(next);
  }, []);

  const handleStart = useCallback(async () => {
    try {
      await startPipeline();
      toast.show("Pipeline iniciado", "success");
    } catch (e) {
      toast.show(`No se pudo iniciar: ${(e as Error).message}`, "error");
    }
  }, [toast]);

  const handleStop = useCallback(async () => {
    try {
      await stopPipeline();
      toast.show("Pipeline detenido", "info");
    } catch (e) {
      toast.show(`No se pudo detener: ${(e as Error).message}`, "error");
    }
  }, [toast]);

  const handleApply = useCallback(async () => {
    if (!config) return;
    if (!topology.ok) {
      toast.show(`Topología inválida: ${topology.reason}`, "error");
      return;
    }
    setIsApplying(true);
    try {
      const result = graphToConfig(currentNodes, currentEdges, {
        pipelineMode: config.pipeline.mode,
        disableMissing: false,
      });
      if (!result.ok) {
        toast.show(`Error: ${result.reason}`, "error");
        return;
      }
      await updateConfig(result.config);
      const fresh = await getConfig();
      setConfig(fresh);
      setInitialNodes(currentNodes);
      setInitialEdges(currentEdges);
      toast.show("Configuración aplicada", "success");
    } catch (e) {
      toast.show(`Error aplicando: ${(e as Error).message}`, "error");
    } finally {
      setIsApplying(false);
    }
  }, [config, currentEdges, currentNodes, topology, toast]);

  const handleReset = useCallback(() => {
    setCurrentNodes(initialNodes);
    setCurrentEdges(initialEdges);
    toast.show("Grafo recargado desde la configuración actual", "info");
  }, [initialEdges, initialNodes, toast]);

  const handleSavePreset = useCallback(
    async (name: string) => {
      if (!topology.ok) {
        toast.show(`Topología inválida: ${topology.reason}`, "error");
        return;
      }
      try {
        // Aplica primero los cambios actuales al backend
        const result = graphToConfig(currentNodes, currentEdges, {
          pipelineMode: config?.pipeline.mode ?? "thread_parallel",
          disableMissing: false,
        });
        if (!result.ok) {
          toast.show(result.reason, "error");
          return;
        }
        await updateConfig(result.config);
        // POST /api/presets
        const res = await fetchWithAuth("/api/presets", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            name,
            description: "Saved from /graph editor",
          }),
        });
        if (!res.ok) {
          const errText = await res.text();
          throw new Error(errText || `HTTP ${res.status}`);
        }
        toast.show(`Preset "${name}" guardado`, "success");
      } catch (e) {
        toast.show(`Error guardando preset: ${(e as Error).message}`, "error");
      }
    },
    [config, currentEdges, currentNodes, toast, topology],
  );

  const handleLoadPreset = useCallback(
    async (name: string) => {
      try {
        const res = await fetchWithAuth(
          `/api/presets/${encodeURIComponent(name)}/apply`,
          {
            method: "POST",
            credentials: "include",
          },
        );
        if (!res.ok) {
          const errText = await res.text();
          throw new Error(errText || `HTTP ${res.status}`);
        }
        const data = (await res.json()) as { config: Config };
        setConfig(data.config);
        const { nodes, edges } = configToGraph(data.config);
        setInitialNodes(nodes);
        setInitialEdges(edges);
        setCurrentNodes(nodes);
        setCurrentEdges(edges);
        toast.show(`Preset "${name}" aplicado`, "success");
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        toast.show(`Error cargando preset: ${msg}`, "error");
      }
    },
    [toast],
  );

  if (isLoading) {
    return (
      <div
        style={{
          height: "100vh",
          display: "grid",
          placeItems: "center",
          color: "var(--text-sec)",
          fontFamily: "var(--font-mono, monospace)",
          fontSize: 13,
        }}
        data-testid="graph-loading"
      >
        Cargando configuración…
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateRows: "auto 1fr",
        height: "100vh",
        background: "var(--bg-deep)",
        color: "var(--text-prime)",
      }}
      data-testid="pipeline-graph"
    >
      <Toolbar
        isPipelineRunning={status?.state === "running"}
        isApplying={isApplying}
        isDirty={isDirty}
        onStart={handleStart}
        onStop={handleStop}
        onApply={handleApply}
        onReset={handleReset}
        onSavePreset={(n) => void handleSavePreset(n)}
        onLoadPreset={(n) => void handleLoadPreset(n)}
      />
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 320px",
          minHeight: 0,
        }}
      >
        <PipelineCanvas
          initialNodes={initialNodes}
          initialEdges={initialEdges}
          onChange={handleGraphChange}
          onSelection={handleSelection}
        />
        <aside
          style={{
            background: "var(--bg-surface)",
            borderLeft: "1px solid var(--border-dim)",
            overflowY: "auto",
          }}
        >
          <InspectorPanel
            selected={selectedData}
            onChange={handleInspectorChange}
          />
        </aside>
      </div>
      {!topology.ok ? (
        <div
          style={{
            position: "fixed",
            bottom: 12,
            left: 12,
            background: "var(--error)",
            color: "var(--text-pure, #fff)",
            padding: "6px 12px",
            borderRadius: "var(--radius-sm)",
            fontSize: 11,
            fontFamily: "var(--font-mono, monospace)",
            maxWidth: 480,
          }}
          role="alert"
          data-testid="topology-error"
        >
          {topology.reason}
        </div>
      ) : null}
      {toast.message ? (
        <div
          style={{
            position: "fixed",
            bottom: 12,
            right: 12,
            background: TOAST_COLOR[toast.kind],
            color: "var(--text-pure, #fff)",
            padding: "8px 14px",
            borderRadius: "var(--radius-sm)",
            fontSize: 12,
            fontFamily: "var(--font-mono, monospace)",
            boxShadow: "0 2px 12px rgba(0,0,0,0.4)",
            maxWidth: 480,
          }}
          role="status"
          data-testid="graph-toast"
        >
          {toast.message}
        </div>
      ) : null}
    </div>
  );
}

// Lookup: el id de nodo que `configToGraph` asigna a cada NodeKind.
function nodeIdForKind(kind: GraphNodeData["kind"]): string {
  const map: Record<GraphNodeData["kind"], string> = {
    input: "n_input",
    audio_extractor: "n_audio_extractor",
    transcriber: "n_transcriber",
    translator: "n_translator",
    subtitle_generator: "n_subtitle_generator",
    tts_engine: "n_tts_engine",
    audio_mixer: "n_audio_mixer",
    output: "n_output",
  };
  return map[kind];
}

export default PipelineGraph;
// Re-export para que el wrapper Astro pueda importar `PipelineGraph` y los tipos.
export type { Config, Status, PresetSummary };
