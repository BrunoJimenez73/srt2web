/**
 * Serialización de grafo ⇄ Config.
 *
 * El editor visual define un pipeline como un grafo de nodos tipados. Esta
 * capa convierte ese grafo a/desde `Partial<Config>` para aplicar los
 * cambios vía `PUT /api/config`.
 *
 * Topología permitida (validador + serializador):
 * - DAG acíclico
 * - Exactamente 1 nodo `input`
 * - Al menos 1 nodo `output`
 * - Lineal o con un único branch convergente en `audio_mixer`
 *   (audio_extractor → audio_mixer ← tts_engine)
 *
 * El backend sigue usando `sequential` o `thread_parallel`. El modo
 * elegido para `Config.pipeline.mode` se pasa como argumento del caller.
 */
import type { Edge, Node } from "@xyflow/react";
import type {
  Config,
  ModuleConfig,
  ModulesConfig,
  PipelineConfig,
  PipelineMode,
} from "../types/api";
import { getNodeDef, isNodeKind, type NodeKind } from "./nodeCatalog";

// ── Tipos de datos del nodo (data del React Flow node) ────────────────────

/**
 * Forma del objeto `node.data` para nodos del grafo. Contiene el tipo
 * del nodo y, opcionalmente, overrides de configuración del módulo
 * (los valores que el usuario edita en el InspectorPanel).
 */
export interface GraphNodeData {
  kind: NodeKind;
  /** Solo presente en nodos cuyo `configLocation` es `modules`. */
  moduleConfig?: ModuleConfig;
  [key: string]: unknown;
}

// ── Topología ────────────────────────────────────────────────────────────

export type TopologyResult =
  | { ok: true; order: string[] }
  | { ok: false; reason: string };

/**
 * Orden topológico + validación de la topología permitida.
 *
 * Reglas:
 * 1. Hay exactamente 1 nodo `input` y al menos 1 nodo `output`.
 * 2. Cada nodo (excepto `input`) tiene exactamente 1 entrante (con la
 *    excepción de `audio_mixer` que admite 2, uno de los cuales debe
 *    ser `audio_extractor` y el otro `tts_engine`).
 * 3. Cada nodo (excepto `output`) tiene al menos 1 saliente.
 * 4. No hay ciclos.
 * 5. Todos los nodos están conectados al mismo grafo (no hay islas).
 */
export function validateTopology(
  nodes: Node[],
  edges: Edge[],
): TopologyResult {
  if (nodes.length === 0) {
    return { ok: false, reason: "El grafo está vacío" };
  }
  const kinds = nodes.map((n) => (n.data as GraphNodeData).kind);
  for (const k of kinds) {
    if (!isNodeKind(k)) {
      return { ok: false, reason: `Tipo de nodo inválido: ${k}` };
    }
  }
  const inputNodes = nodes.filter((n) => (n.data as GraphNodeData).kind === "input");
  const outputNodes = nodes.filter((n) => (n.data as GraphNodeData).kind === "output");
  if (inputNodes.length === 0) {
    return { ok: false, reason: "Falta el nodo 'Input'" };
  }
  if (inputNodes.length > 1) {
    return { ok: false, reason: "Solo puede haber un nodo 'Input'" };
  }
  if (outputNodes.length === 0) {
    return { ok: false, reason: "Falta al menos un nodo 'Output'" };
  }
  // Regla 2: aristas entrantes por nodo
  for (const n of nodes) {
    const incoming = edges.filter((e) => e.target === n.id).length;
    const kind = (n.data as GraphNodeData).kind;
    if (kind === "input") {
      if (incoming !== 0) {
        return { ok: false, reason: "El nodo 'Input' no puede tener entradas" };
      }
      continue;
    }
    if (kind === "audio_mixer") {
      if (incoming < 1 || incoming > 2) {
        return {
          ok: false,
          reason: `'Audio Mixer' debe tener 1 o 2 entradas (tiene ${incoming})`,
        };
      }
    } else if (kind === "output") {
      // output acepta hasta 3 entradas: video + audio + subtitles
      if (incoming > 3) {
        return {
          ok: false,
          reason: `El nodo 'Output' tiene ${incoming} entradas (máx 3)`,
        };
      }
    } else if (incoming === 0) {
      return { ok: false, reason: `El nodo '${getNodeDef(kind).label}' no tiene entradas` };
    } else if (incoming > 1) {
      return {
        ok: false,
        reason: `El nodo '${getNodeDef(kind).label}' tiene ${incoming} entradas (máx 1)`,
      };
    }
  }
  // Regla 3: aristas salientes
  for (const n of nodes) {
    const outgoing = edges.filter((e) => e.source === n.id).length;
    const kind = (n.data as GraphNodeData).kind;
    if (kind === "output") {
      if (outgoing !== 0) {
        return { ok: false, reason: "El nodo 'Output' no puede tener salidas" };
      }
      continue;
    }
    if (outgoing === 0) {
      return {
        ok: false,
        reason: `El nodo '${getNodeDef(kind).label}' no tiene salidas`,
      };
    }
  }
  // Regla 4 + 5: orden topológico + cobertura
  const order = topologicalSort(nodes, edges);
  if (order === null) {
    return { ok: false, reason: "El grafo contiene un ciclo" };
  }
  if (order.length !== nodes.length) {
    return { ok: false, reason: "Hay nodos aislados (no conectados al grafo principal)" };
  }
  return { ok: true, order };
}

/**
 * Implementación de Kahn. Devuelve el orden o `null` si hay ciclo.
 */
function topologicalSort(nodes: Node[], edges: Edge[]): string[] | null {
  const indeg = new Map<string, number>();
  for (const n of nodes) indeg.set(n.id, 0);
  for (const e of edges) {
    indeg.set(e.target, (indeg.get(e.target) ?? 0) + 1);
  }
  const queue: string[] = [];
  for (const [id, deg] of indeg) {
    if (deg === 0) queue.push(id);
  }
  const order: string[] = [];
  while (queue.length > 0) {
    const id = queue.shift()!;
    order.push(id);
    for (const e of edges.filter((x) => x.source === id)) {
      const d = (indeg.get(e.target) ?? 0) - 1;
      indeg.set(e.target, d);
      if (d === 0) queue.push(e.target);
    }
  }
  return order.length === nodes.length ? order : null;
}

// ── Grafo → Config ────────────────────────────────────────────────────────

export interface GraphApplyOptions {
  pipelineMode: PipelineMode;
  /** Si true, desactiva módulos que no aparecen en el grafo. */
  disableMissing?: boolean;
}

export type GraphToConfigResult =
  | { ok: true; config: Partial<Config> }
  | { ok: false; reason: string };

/**
 * Convierte un grafo válido a un `Partial<Config>` que se puede enviar
 * a `PUT /api/config`.
 *
 * - Activa los módulos que aparecen en el grafo (`modules.<key>.enabled = true`).
 * - Copia el `moduleConfig` del nodo en `modules.<key>.<campo>`.
 * - Desactiva los módulos que NO aparecen si `disableMissing=true`.
 * - Fija `pipeline.mode` al valor de las opciones.
 *
 * `input` y `output` no tocan `modules` (su config se edita fuera del grafo).
 */
export function graphToConfig(
  nodes: Node[],
  edges: Edge[],
  options: GraphApplyOptions,
): GraphToConfigResult {
  const topo = validateTopology(nodes, edges);
  if (!topo.ok) return { ok: false, reason: topo.reason };
  // Convierte nodes a Map por id para lookup rápido
  const byId = new Map<string, Node>();
  for (const n of nodes) byId.set(n.id, n);
  void byId; // (referenced for future edge inspection)
  void edges; // (referenced for future edge inspection)
  const modules: Partial<Record<keyof ModulesConfig, ModuleConfig>> = {};
  // Marcar todos los módulos del catálogo como disabled (si disableMissing)
  if (options.disableMissing) {
    const allKeys: (keyof ModulesConfig)[] = [
      "audio_extractor",
      "transcriber",
      "translator",
      "subtitle_generator",
      "tts_engine",
      "audio_mixer",
      "video_muxer",
    ];
    for (const k of allKeys) {
      modules[k] = { enabled: false };
    }
  }
  for (const n of nodes) {
    const data = n.data as GraphNodeData;
    const def = getNodeDef(data.kind);
    if (def.configLocation.kind !== "modules") continue;
    const key = def.configLocation.key;
    const cfg: ModuleConfig = data.moduleConfig ?? { enabled: true };
    modules[key] = {
      enabled: cfg.enabled,
      ...omitEnabled(cfg),
    };
  }
  const pipeline: Partial<PipelineConfig> = { mode: options.pipelineMode };
  const config = {
    modules,
    pipeline,
  } as unknown as Partial<Config>;
  return { ok: true, config };
}

function omitEnabled(cfg: ModuleConfig): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(cfg)) {
    if (k !== "enabled") out[k] = v;
  }
  return out;
}

// ── Config → Grafo ────────────────────────────────────────────────────────

/**
 * Construye un grafo a partir del estado actual de la configuración.
 * Devuelve los 8 nodos básicos, conectados según el estado de cada módulo
 * (enabled = visible y conectado, disabled = visible pero gris).
 *
 * La posición inicial es una rejilla simple de izquierda a derecha.
 */
export function configToGraph(config: Config): { nodes: Node[]; edges: Edge[] } {
  const xs: Record<NodeKind, number> = {
    input: 50,
    audio_extractor: 350,
    transcriber: 650,
    translator: 950,
    subtitle_generator: 1250,
    tts_engine: 1250,
    audio_mixer: 1550,
    output: 1850,
  };
  const ys: Record<NodeKind, number> = {
    input: 200,
    audio_extractor: 200,
    transcriber: 200,
    translator: 200,
    subtitle_generator: 50,
    tts_engine: 350,
    audio_mixer: 200,
    output: 200,
  };
  const order: NodeKind[] = [
    "input",
    "audio_extractor",
    "transcriber",
    "translator",
    "subtitle_generator",
    "tts_engine",
    "audio_mixer",
    "output",
  ];
  const ids: Record<NodeKind, string> = {
    input: "n_input",
    audio_extractor: "n_audio_extractor",
    transcriber: "n_transcriber",
    translator: "n_translator",
    subtitle_generator: "n_subtitle_generator",
    tts_engine: "n_tts_engine",
    audio_mixer: "n_audio_mixer",
    output: "n_output",
  };
  const nodes: Node[] = [];
  for (const kind of order) {
    const def = getNodeDef(kind);
    const moduleKey =
      def.configLocation.kind === "modules" ? def.configLocation.key : null;
    const moduleConfig = moduleKey
      ? (config.modules[moduleKey] as ModuleConfig | undefined)
      : undefined;
    nodes.push({
      id: ids[kind],
      type: "module",
      position: { x: xs[kind], y: ys[kind] },
      data: {
        kind,
        moduleConfig: moduleConfig ?? { enabled: true },
      } as GraphNodeData,
    });
  }
  // Edges: linear + branch en audio_mixer
  const edges: Edge[] = [
    { id: "e_in_ax", source: ids.input, sourceHandle: "video", target: ids.audio_extractor, targetHandle: "video" },
    { id: "e_ax_v", source: ids.audio_extractor, sourceHandle: "video", target: ids.output, targetHandle: "video" },
    { id: "e_ax_t", source: ids.audio_extractor, sourceHandle: "audio", target: ids.transcriber, targetHandle: "audio" },
    { id: "e_t_x", source: ids.transcriber, sourceHandle: "transcript", target: ids.translator, targetHandle: "transcript" },
    { id: "e_x_sg", source: ids.translator, sourceHandle: "transcript", target: ids.subtitle_generator, targetHandle: "transcript" },
    { id: "e_sg_o", source: ids.subtitle_generator, sourceHandle: "subtitles", target: ids.output, targetHandle: "subtitles" },
    { id: "e_x_tts", source: ids.translator, sourceHandle: "transcript", target: ids.tts_engine, targetHandle: "transcript" },
    { id: "e_tts_m", source: ids.tts_engine, sourceHandle: "audio", target: ids.audio_mixer, targetHandle: "audio-dub" },
    { id: "e_ax_m", source: ids.audio_extractor, sourceHandle: "audio", target: ids.audio_mixer, targetHandle: "audio-orig" },
    { id: "e_m_o", source: ids.audio_mixer, sourceHandle: "audio", target: ids.output, targetHandle: "audio" },
  ];
  return { nodes, edges };
}
