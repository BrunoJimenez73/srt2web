import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { ModuleNode } from "./ModuleNode";
import { getNodeDef, type NodeKind } from "../../lib/graph/nodeCatalog";
import type { GraphNodeData } from "../../lib/graph/serialize";
import type { LiveNodeStatus } from "../../lib/graph/liveStatus";
import type { NodeProps } from "@xyflow/react";

// jsdom no implementa CSSStyleSheet, evita warnings
class _StubCSSStyleSheet {
  replaceSync() {
    /* noop */
  }
}
Object.defineProperty(window, "CSSStyleSheet", {
  value: _StubCSSStyleSheet,
  writable: true,
});

const KINDS: NodeKind[] = [
  "input",
  "audio_extractor",
  "transcriber",
  "translator",
  "subtitle_generator",
  "tts_engine",
  "audio_mixer",
  "output",
];

function makeProps(
  kind: NodeKind,
  live?: LiveNodeStatus,
): NodeProps & { data: GraphNodeData & { liveStatus?: LiveNodeStatus } } {
  const data: GraphNodeData & { liveStatus?: LiveNodeStatus } = { kind };
  if (live) data.liveStatus = live;
  return {
    id: `n_${kind}`,
    data,
    type: "module",
    selected: false,
    zIndex: 0,
    isConnectable: true,
    xPos: 0,
    yPos: 0,
    dragging: false,
    width: 180,
    height: 80,
  } as unknown as NodeProps & {
    data: GraphNodeData & { liveStatus?: LiveNodeStatus };
  };
}

describe("ModuleNode", () => {
  it("renderiza sin errores para cada NodeKind", () => {
    for (const kind of KINDS) {
      const { container, unmount } = render(<ModuleNode {...makeProps(kind)} />);
      const root = container.querySelector(`[data-testid="module-node-${kind}"]`);
      expect(root).toBeTruthy();
      expect(root?.getAttribute("data-state")).toBeTruthy();
      unmount();
    }
  });

  it("muestra el label del catálogo en el header", () => {
    const { container } = render(<ModuleNode {...makeProps("transcriber")} />);
    const def = getNodeDef("transcriber");
    expect(container.textContent).toContain(def.label);
  });

  it("muestra el badge de estado correcto cuando hay live status", () => {
    const { container } = render(
      <ModuleNode
        {...makeProps("transcriber", {
          state: "running",
          processedChunks: 42,
          lastActiveMs: 0,
          pulse: true,
          enabled: true,
        })}
      />,
    );
    const root = container.querySelector('[data-testid="module-node-transcriber"]');
    expect(root?.getAttribute("data-state")).toBe("running");
  });

  it("estado desconocido cuando no hay live status", () => {
    const { container } = render(<ModuleNode {...makeProps("tts_engine")} />);
    const root = container.querySelector('[data-testid="module-node-tts_engine"]');
    expect(root?.getAttribute("data-state")).toBe("unknown");
  });

  it("renderiza todos los handles esperados del catálogo", () => {
    // input tiene 0 inputs y 1 output (video)
    const { container: c1 } = render(<ModuleNode {...makeProps("input")} />);
    const in1 = c1.querySelectorAll(".react-flow__handle.target");
    const out1 = c1.querySelectorAll(".react-flow__handle.source");
    expect(in1.length).toBe(0);
    expect(out1.length).toBe(1);

    // audio_mixer tiene 2 inputs (audio-orig, audio-dub) y 1 output (audio)
    const { container: c2 } = render(<ModuleNode {...makeProps("audio_mixer")} />);
    const in2 = c2.querySelectorAll(".react-flow__handle.target");
    const out2 = c2.querySelectorAll(".react-flow__handle.source");
    expect(in2.length).toBe(2);
    expect(out2.length).toBe(1);
  });

  it("los handles tienen data-handletype correcto", () => {
    const { container } = render(<ModuleNode {...makeProps("transcriber")} />);
    const handles = container.querySelectorAll(".react-flow__handle");
    expect(handles.length).toBeGreaterThan(0);
    for (const h of Array.from(handles)) {
      const handleEl = h as HTMLElement;
      const t = handleEl.getAttribute("data-handletype");
      expect(["video", "audio", "transcript", "subtitles"]).toContain(t);
    }
  });
});
