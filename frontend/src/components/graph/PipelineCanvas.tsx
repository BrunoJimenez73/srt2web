/**
 * Canvas principal del editor de grafo.
 *
 * Integra:
 * - `<ReactFlow>` con nodes/edges custom (`ModuleNode`)
 * - Validador de conexiones tipadas (`isValidConnection`)
 * - MiniMap con colores por categoría de nodo
 * - Background + Controls
 * - Estado en vivo vía `useLiveModuleStatus`
 * - Comunicación con el padre: `onGraphChange`, `onSelectionChange`
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  type Edge,
  type Node,
  type NodeChange,
  type EdgeChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  HANDLE_TYPE_COLOR,
  type NodeKind,
} from "../../lib/graph/nodeCatalog";
import { makeIsValidConnection } from "../../lib/graph/typedEdge";
import { useLiveModuleStatus, type LiveNodeStatus } from "../../lib/graph/liveStatus";
import { ModuleNode } from "./ModuleNode";
import type { GraphNodeData } from "../../lib/graph/serialize";

const nodeTypes = { module: ModuleNode };

const GRID_SIZE = 20;

function PipelineCanvasInner({
  initialNodes,
  initialEdges,
  readOnly = false,
  onChange,
  onSelection,
}: {
  initialNodes: Node[];
  initialEdges: Edge[];
  readOnly?: boolean;
  onChange?: (nodes: Node[], edges: Edge[]) => void;
  onSelection?: (data: GraphNodeData | null) => void;
}) {
  const [nodes, setNodes, onNodesChangeBase] = useNodesState<Node>(initialNodes);
  const [edges, setEdges, onEdgesChangeBase] = useEdgesState<Edge>(initialEdges);
  const liveStatus = useLiveModuleStatus();

  // Inyecta el live status en cada nodo
  const nodesWithLive = useMemo(() => {
    return nodes.map((n) => {
      const data = n.data as GraphNodeData;
      const status: LiveNodeStatus | undefined = liveStatus.get(data.kind);
      return {
        ...n,
        data: {
          ...data,
          liveStatus: status,
        },
      };
    });
  }, [nodes, liveStatus]);

  // Notifica cambios al padre
  useEffect(() => {
    onChange?.(nodes, edges);
  }, [nodes, edges, onChange]);

  const isValidConnection = useCallback(
    (connection: Connection | Edge) => makeIsValidConnection(nodes, edges)(connection),
    [nodes, edges],
  );

  const onConnect = useCallback(
    (params: Connection) => {
      if (readOnly) return;
      setEdges((els) => addEdge({ ...params, animated: true }, els));
    },
    [setEdges, readOnly],
  );

  const handleSelectionChange = useCallback(
    (sel: { nodes: Node[]; edges: Edge[] }) => {
      const node = sel.nodes[0];
      if (!node) {
        onSelection?.(null);
        return;
      }
      onSelection?.(node.data as GraphNodeData);
    },
    [onSelection],
  );

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      if (readOnly) return;
      onNodesChangeBase(changes);
    },
    [onNodesChangeBase, readOnly],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      if (readOnly) return;
      onEdgesChangeBase(changes);
    },
    [onEdgesChangeBase, readOnly],
  );

  return (
    <div
      style={{ width: "100%", height: "100%", minHeight: 400, background: "var(--bg-deep)" }}
      data-testid="pipeline-canvas"
    >
      <ReactFlow
        nodes={nodesWithLive}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        isValidConnection={isValidConnection}
        onSelectionChange={handleSelectionChange}
        fitView
        snapToGrid
        snapGrid={[GRID_SIZE, GRID_SIZE]}
        deleteKeyCode={readOnly ? null : ["Backspace", "Delete"]}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={GRID_SIZE} color="#1a1a24" />
        <Controls showInteractive={false} />
        <MiniMap
          pannable
          zoomable
          nodeColor={(n) => {
            const kind = (n.data as { kind?: NodeKind })?.kind;
            if (!kind) return "#555570";
            const out = Object.values(HANDLE_TYPE_COLOR);
            // Hash simple: rotar sobre el array para tener un color por nodo
            const idx = kind.length % out.length;
            return out[idx];
          }}
          maskColor="rgba(10, 10, 15, 0.7)"
        />
      </ReactFlow>
      <style>{`
        @keyframes graph-pulse {
          0%, 100% { opacity: 0.6; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.15); }
        }
        .react-flow__handle { transition: transform 0.15s ease; }
        .react-flow__handle:hover { transform: scale(1.4); }
      `}</style>
    </div>
  );
}

export function PipelineCanvas(props: {
  initialNodes: Node[];
  initialEdges: Edge[];
  readOnly?: boolean;
  onChange?: (nodes: Node[], edges: Edge[]) => void;
  onSelection?: (data: GraphNodeData | null) => void;
}) {
  // React Flow requiere un `ReactFlowProvider` en el árbol para que
  // hooks como `useReactFlow` funcionen. Lo montamos aquí para aislar
  // el provider de Astro.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          minHeight: 400,
          display: "grid",
          placeItems: "center",
          color: "var(--text-sec)",
          fontFamily: "var(--font-mono, monospace)",
          fontSize: 12,
        }}
      >
        Cargando editor…
      </div>
    );
  }
  return (
    <ReactFlowProvider>
      <PipelineCanvasInner {...props} />
    </ReactFlowProvider>
  );
}

export default PipelineCanvas;
