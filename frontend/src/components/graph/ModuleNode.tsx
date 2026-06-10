/**
 * Nodo visual de un módulo del pipeline.
 *
 * Renderiza un card con:
 * - Título del módulo (label del catálogo)
 * - Badge de estado (idle / running / error / disabled)
 * - Bordes pulsantes cuando hay actividad reciente
 * - `<Handle>`s tipados con colores por tipo de dato
 *   (video=rojo, audio=verde, transcript=azul, subtitles=amarillo)
 *
 * El `data` del nodo debe ser de tipo `GraphNodeData` (ver serialize.ts).
 * El `liveStatus` es opcional y se usa para colorear el nodo en vivo.
 */
import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { getNodeDef, HANDLE_TYPE_COLOR, HANDLE_TYPE_LABEL } from "../../lib/graph/nodeCatalog";
import type { GraphNodeData } from "../../lib/graph/serialize";
import type { LiveNodeStatus } from "../../lib/graph/liveStatus";
import type { HandleSpec } from "../../lib/graph/nodeCatalog";

export interface ModuleNodeProps extends NodeProps {
  data: GraphNodeData & { liveStatus?: LiveNodeStatus };
}

const STATE_COLOR: Record<string, string> = {
  idle: "#555570",
  running: "#10b981",
  error: "#ef4444",
  stopped: "#555570",
  degraded: "#f59e0b",
  disabled: "#555570",
  unknown: "#555570",
};

const STATE_LABEL: Record<string, string> = {
  idle: "Inactivo",
  running: "En ejecución",
  error: "Error",
  stopped: "Detenido",
  degraded: "Degradado",
  disabled: "Desactivado",
  unknown: "Desconocido",
};

function HandleForSpec({
  spec,
  isSource,
}: {
  spec: HandleSpec;
  isSource: boolean;
}) {
  const pos: Position = isSource ? Position.Right : Position.Left;
  const color = HANDLE_TYPE_COLOR[spec.type];
  return (
    <Handle
      type={isSource ? "source" : "target"}
      position={pos}
      id={spec.id}
      title={`${HANDLE_TYPE_LABEL[spec.type]} (${spec.label})`}
      style={{
        background: color,
        width: 10,
        height: 10,
        border: "2px solid #1a1a24",
      }}
      data-handletype={spec.type}
    />
  );
}

function ModuleNodeComponent({ data }: ModuleNodeProps) {
  const def = getNodeDef(data.kind);
  const live = data.liveStatus;
  const state = live?.state ?? "unknown";
  const stateColor = STATE_COLOR[state] ?? "#555570";
  const stateLabel = STATE_LABEL[state] ?? state;
  const isPulsing = live?.pulse ?? false;
  const isDisabled = state === "disabled" || (live?.enabled === false);

  return (
    <div
      className="module-node"
      style={{
        background: "var(--bg-card)",
        color: "var(--text-prime)",
        border: `1.5px solid ${isPulsing ? "#00ff00" : "var(--border-dim)"}`,
        borderRadius: "var(--radius-md)",
        padding: "10px 14px",
        minWidth: 180,
        maxWidth: 240,
        fontSize: 12,
        boxShadow: isPulsing
          ? "0 0 12px rgba(0, 255, 0, 0.5)"
          : "none",
        opacity: isDisabled ? 0.5 : 1,
        transition: "all 0.2s ease",
        fontFamily: "var(--font-mono, monospace)",
      }}
      data-testid={`module-node-${data.kind}`}
      data-state={state}
    >
      {def.inputs.map((spec) => (
        <HandleForSpec key={`in-${spec.id}`} spec={spec} isSource={false} />
      ))}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 6,
        }}
      >
        <span
          aria-hidden="true"
          style={{
            display: "inline-block",
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: stateColor,
            boxShadow:
              state === "running" ? `0 0 6px ${stateColor}` : "none",
            animation: isPulsing ? "graph-pulse 1.2s infinite" : undefined,
          }}
        />
        <span
          style={{
            fontWeight: 600,
            flex: 1,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
          title={def.description}
        >
          {def.label}
        </span>
        <span
          style={{
            fontSize: 10,
            padding: "1px 6px",
            borderRadius: 4,
            background: "rgba(255,255,255,0.05)",
            color: stateColor,
            border: `1px solid ${stateColor}40`,
          }}
        >
          {stateLabel}
        </span>
      </div>
      {live?.processedChunks !== undefined && live.processedChunks > 0 ? (
        <div style={{ fontSize: 10, color: "var(--text-sec)" }}>
          Chunks: {live.processedChunks}
        </div>
      ) : null}
      {def.outputs.map((spec) => (
        <HandleForSpec key={`out-${spec.id}`} spec={spec} isSource={true} />
      ))}
    </div>
  );
}

export const ModuleNode = memo(ModuleNodeComponent);
export default ModuleNode;
