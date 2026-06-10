/**
 * Validador de aristas tipadas para el editor visual de pipeline.
 *
 * Una arista es válida si y solo si:
 * 1. El tipo de dato del handle de origen coincide con el del handle de destino.
 * 2. No crea un ciclo en el grafo.
 * 3. No excede la cantidad máxima de entradas permitidas por nodo destino
 *    (1 para todos los nodos, excepto `audio_mixer` que admite 2).
 * 4. El nodo `input` no tiene entrantes; el nodo `output` no tiene salientes.
 *
 * Esta función se usa como callback `isValidConnection` de `<ReactFlow>`.
 */
import type { Connection, Edge, Node } from "@xyflow/react";
import { getNodeDef, isNodeKind, type NodeKind } from "./nodeCatalog";

// ── Lookup de handle por nodeId + handleId ─────────────────────────────────

/**
 * Devuelve el `HandleSpec` del catálogo que corresponde a un (node, handleId)
 * dados. Usado por el validador y por `ModuleNode` para renderizar handles
 * tipados. Retorna `null` si el handle no existe.
 */
export function findHandleSpec(
  nodeKind: NodeKind,
  handleId: string | null | undefined,
  isSource: boolean,
): { type: import("./nodeCatalog").HandleType; spec: import("./nodeCatalog").HandleSpec } | null {
  const def = getNodeDef(nodeKind);
  if (!def) return null;
  const list = isSource ? def.outputs : def.inputs;
  const id = handleId ?? (list[0]?.id ?? null);
  if (id === null) return null;
  const spec = list.find((h) => h.id === id);
  if (!spec) return null;
  return { type: spec.type, spec };
}

/** Tipo de dato que lleva un handle concreto. `null` si no se puede resolver. */
export function getHandleDataType(
  nodeKind: NodeKind,
  handleId: string | null | undefined,
  isSource: boolean,
): import("./nodeCatalog").HandleType | null {
  return findHandleSpec(nodeKind, handleId, isSource)?.type ?? null;
}

// ── Helpers de grafo ───────────────────────────────────────────────────────

/** Devuelve todos los nodos que salen de uno dado (outgoers). */
function getOutgoers(nodeId: string, nodes: Node[], edges: Edge[]): Node[] {
  const outIds = new Set(
    edges.filter((e) => e.source === nodeId).map((e) => e.target),
  );
  return nodes.filter((n) => outIds.has(n.id));
}

/** Detecta si `target` es alcanzable desde `source` por el grafo actual. */
function hasCycleFrom(
  source: string,
  target: string,
  nodes: Node[],
  edges: Edge[],
): boolean {
  if (source === target) return true;
  const visited = new Set<string>();
  const stack: string[] = [target];
  while (stack.length > 0) {
    const current = stack.pop()!;
    if (visited.has(current)) continue;
    visited.add(current);
    for (const out of getOutgoers(current, nodes, edges)) {
      if (out.id === source) return true;
      stack.push(out.id);
    }
  }
  return false;
}

/** Cuenta cuántas aristas llegan a `targetNodeId` (excluyendo `pendingEdgeId`). */
function countIncoming(
  targetNodeId: string,
  edges: Edge[],
  pendingEdgeId: string | null,
): number {
  return edges.filter(
    (e) => e.target === targetNodeId && e.id !== pendingEdgeId,
  ).length;
}

/** Límite de entradas por nodo. */
function maxIncomingFor(kind: NodeKind): number {
  if (kind === "audio_mixer") return 2;
  if (kind === "output") return 3; // video + audio + subtitles
  return 1;
}

// ── Validador principal ────────────────────────────────────────────────────

export interface ValidationResult {
  valid: boolean;
  reason?: string;
}

/**
 * Validador usado por `<ReactFlow isValidConnection={...}>`.
 * Devuelve `true` si la conexión es estructural y semánticamente correcta.
 *
 * Nota: la API de React Flow requiere `boolean`, pero internamente
 * registramos los rechazos vía `lastRejectionReason` (debug) para
 * mostrarlos en tests / logs.
 */
export let lastRejectionReason: string | null = null;

export function isValidConnection(
  connection: Connection | Edge,
  nodes: Node[],
  edges: Edge[],
): boolean {
  const result = validateConnection(connection, nodes, edges);
  lastRejectionReason = result.reason ?? null;
  return result.valid;
}

export function validateConnection(
  connection: Connection | Edge,
  nodes: Node[],
  edges: Edge[],
): ValidationResult {
  const { source, target, sourceHandle, targetHandle } = connection;
  if (!source || !target) {
    return { valid: false, reason: "Falta source o target" };
  }
  if (source === target) {
    return { valid: false, reason: "Un nodo no puede conectarse a sí mismo" };
  }
  const sourceNode = nodes.find((n) => n.id === source);
  const targetNode = nodes.find((n) => n.id === target);
  if (!sourceNode || !targetNode) {
    return { valid: false, reason: "Nodo source o target no existe" };
  }
  const sourceKind = (sourceNode.data as { kind?: string }).kind;
  const targetKind = (targetNode.data as { kind?: string }).kind;
  if (!sourceKind || !isNodeKind(sourceKind)) {
    return { valid: false, reason: `Tipo de nodo source inválido: ${sourceKind}` };
  }
  if (!targetKind || !isNodeKind(targetKind)) {
    return { valid: false, reason: `Tipo de nodo target inválido: ${targetKind}` };
  }
  const sourceDef = getNodeDef(sourceKind);
  const targetDef = getNodeDef(targetKind);

  // 1. Source no debe tener handles de salida
  if (sourceDef.outputs.length === 0) {
    return {
      valid: false,
      reason: `El nodo "${sourceDef.label}" no produce salida`,
    };
  }
  // 2. Target no debe tener handles de entrada
  if (targetDef.inputs.length === 0) {
    return {
      valid: false,
      reason: `El nodo "${targetDef.label}" no acepta entradas`,
    };
  }
  // 3. Tipo de dato debe coincidir
  const sourceType = getHandleDataType(sourceKind, sourceHandle, true);
  const targetType = getHandleDataType(targetKind, targetHandle, false);
  if (!sourceType || !targetType) {
    return {
      valid: false,
      reason: "Handle no resuelto (source o target handle inválido)",
    };
  }
  if (sourceType !== targetType) {
    return {
      valid: false,
      reason: `Tipo incompatible: ${sourceType} → ${targetType}`,
    };
  }
  // 4. No ciclos
  if (hasCycleFrom(source, target, nodes, edges)) {
    return { valid: false, reason: "La conexión crearía un ciclo" };
  }
  // 5. Límite de entradas por nodo
  const edgeId = "id" in connection ? connection.id : null;
  const incomingCount = countIncoming(target, edges, edgeId);
  const limit = maxIncomingFor(targetKind);
  if (incomingCount >= limit) {
    return {
      valid: false,
      reason: `El nodo "${targetDef.label}" ya tiene ${incomingCount}/${limit} entrada(s)`,
    };
  }
  return { valid: true };
}

// ── Snapshot puro para React Flow ─────────────────────────────────────────

/**
 * Wrapper sin estado que se pasa a `<ReactFlow isValidConnection={...}>`.
 * React Flow llama a este callback sin argumentos de contexto, así que
 * tenemos que pasar `nodes`/`edges` por closure (los consumers deben
 * memorizar el callback con `useCallback`).
 */
export function makeIsValidConnection(
  nodes: Node[],
  edges: Edge[],
): (connection: Connection | Edge) => boolean {
  return (connection) => isValidConnection(connection, nodes, edges);
}
