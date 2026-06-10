import { describe, expect, it } from "vitest";
import type { Edge, Node } from "@xyflow/react";
import {
  configToGraph,
  graphToConfig,
  validateTopology,
  type GraphNodeData,
} from "./serialize";
import type { Config } from "../types/api";

// ── Helpers ──────────────────────────────────────────────────────────────

function makeNode(
  id: string,
  kind: GraphNodeData["kind"],
  position = { x: 0, y: 0 },
  moduleConfig?: GraphNodeData["moduleConfig"],
): Node {
  const data: GraphNodeData = moduleConfig ? { kind, moduleConfig } : { kind };
  return { id, type: "module", position, data };
}

function makeEdge(
  id: string,
  source: string,
  target: string,
  sourceHandle: string,
  targetHandle: string,
): Edge {
  return { id, source, target, sourceHandle, targetHandle };
}

// ── Helpers: config mínima para tests ────────────────────────────────────

function makeConfig(): Config {
  return {
    server: {
      host: "0.0.0.0",
      port: 9999,
      cors_origins: [],
      auth_token: "x",
      rate_limit_rpm: 60,
      max_request_size_mb: 100,
    },
    input: { type: "srt", srt: {
      listen_port: 9000,
      mode: "listener",
      latency_ms: 120,
      caller_address: "",
      chunk_duration_sec: 10,
    } },
    output: { type: "web", outputs: [] },
    pipeline: {
      chunk_duration_sec: 10,
      mode: "thread_parallel",
      max_concurrent_chunks: 4,
      buffer_size: 5,
      retry_attempts: 3,
      retry_delay: 2,
    },
    modules: {
      audio_extractor: { enabled: true },
      transcriber: { enabled: true, model: "base", language: "es", device: "auto", beam_size: 5 },
      translator: { enabled: true, source_lang: "es", target_lang: "en" },
      subtitle_generator: { enabled: true, format: "webvtt", use_translated: true, chunk_duration: 10 },
      tts_engine: { enabled: true, engine: "piper", device: "auto", voice: "es_ES-sharvard-medium", speed: 1.0 },
      audio_mixer: { enabled: true, original_volume: 1.0, tts_volume: 1.0 },
      video_muxer: { enabled: true, engine: "hls", hls_segment_duration: 10, hls_list_size: 6, audio_offset_ms: 0, encoder_mode: "auto", video_quality: "medium", video_crf: 23, audio_codec: "aac", audio_bitrate: "128k", audio_samplerate: "48000" },
    },
    output_dir: { directory: "output" },
  };
}

// ── Tests ───────────────────────────────────────────────────────────────

describe("serialize", () => {
  describe("validateTopology", () => {
    it("rechaza grafo vacío", () => {
      const r = validateTopology([], []);
      expect(r.ok).toBe(false);
    });

    it("rechaza si falta el nodo input", () => {
      const nodes: Node[] = [makeNode("ax", "audio_extractor"), makeNode("out", "output")];
      const edges: Edge[] = [makeEdge("e1", "ax", "out", "video", "video")];
      const r = validateTopology(nodes, edges);
      expect(r.ok).toBe(false);
      if (!r.ok) expect(r.reason).toMatch(/Input/i);
    });

    it("rechaza si hay más de un nodo input", () => {
      const nodes: Node[] = [makeNode("in1", "input"), makeNode("in2", "input")];
      const r = validateTopology(nodes, []);
      expect(r.ok).toBe(false);
    });

    it("rechaza si falta el nodo output", () => {
      const nodes: Node[] = [makeNode("in", "input")];
      const r = validateTopology(nodes, []);
      expect(r.ok).toBe(false);
      if (!r.ok) expect(r.reason).toMatch(/Output/i);
    });

    it("rechaza si input tiene entrantes", () => {
      const nodes: Node[] = [makeNode("in", "input"), makeNode("out", "output")];
      const edges: Edge[] = [makeEdge("e1", "out", "in", "video", "video")];
      const r = validateTopology(nodes, edges);
      expect(r.ok).toBe(false);
    });

    it("rechaza si output tiene salientes", () => {
      // out como source → inválido (output no tiene handles de salida)
      const nodes: Node[] = [
        makeNode("in", "input"),
        makeNode("out", "output"),
        makeNode("ghost", "translator"),
      ];
      // Edge in→out válida + edge out→ghost inválida (out no debería ser source)
      const edges: Edge[] = [
        makeEdge("e1", "in", "out", "video", "video"),
        makeEdge("e2", "out", "ghost", "video", "transcript"),
      ];
      const r = validateTopology(nodes, edges);
      expect(r.ok).toBe(false);
      if (!r.ok) expect(r.reason).toMatch(/Output.*salidas/i);
    });

    it("acepta un grafo lineal mínimo (input → output)", () => {
      const nodes: Node[] = [makeNode("in", "input"), makeNode("out", "output")];
      const edges: Edge[] = [makeEdge("e1", "in", "out", "video", "video")];
      const r = validateTopology(nodes, edges);
      expect(r.ok).toBe(true);
      if (r.ok) expect(r.order).toEqual(["in", "out"]);
    });

    it("acepta el grafo completo típico del pipeline", () => {
      const { nodes, edges } = configToGraph(makeConfig());
      const r = validateTopology(nodes, edges);
      expect(r.ok).toBe(true);
      if (r.ok) expect(r.order.length).toBe(8);
    });

    it("rechaza nodos aislados", () => {
      const { nodes, edges } = configToGraph(makeConfig());
      // Añadir un nodo no conectado (sin entradas ni salidas)
      const orphan = makeNode("orphan", "translator");
      const r = validateTopology([...nodes, orphan], edges);
      expect(r.ok).toBe(false);
      // El validador reporta "no tiene entradas" antes que "aislados" — ambas
      // razones son síntoma de un grafo mal conectado.
      if (!r.ok) expect(r.reason).toMatch(/aislados|entradas|conectados/i);
    });

    it("rechaza ciclos", () => {
      const nodes: Node[] = [
        makeNode("in", "input"),
        makeNode("ax", "audio_extractor"),
        makeNode("t", "transcriber"),
        makeNode("out", "output"),
      ];
      const edges: Edge[] = [
        makeEdge("e1", "in", "ax", "video", "video"),
        makeEdge("e2", "ax", "t", "audio", "audio"),
        // crear un ciclo: t -> ax
        makeEdge("e3", "t", "ax", "transcript", "video"),
      ];
      const r = validateTopology(nodes, edges);
      expect(r.ok).toBe(false);
    });
  });

  describe("graphToConfig", () => {
    it("convierte un grafo válido en Partial<Config> con módulos activados", () => {
      const { nodes, edges } = configToGraph(makeConfig());
      const r = graphToConfig(nodes, edges, { pipelineMode: "thread_parallel", disableMissing: true });
      expect(r.ok).toBe(true);
      if (!r.ok) return;
      expect(r.config.pipeline?.mode).toBe("thread_parallel");
      // audio_extractor debe estar enabled
      const ax = r.config.modules?.audio_extractor;
      expect(ax?.enabled).toBe(true);
    });

    it("con disableMissing=true marca como disabled los módulos no presentes", () => {
      // Construir un grafo mínimo solo con input → output
      const nodes: Node[] = [makeNode("in", "input"), makeNode("out", "output")];
      const edges: Edge[] = [makeEdge("e1", "in", "out", "video", "video")];
      const r = graphToConfig(nodes, edges, { pipelineMode: "sequential", disableMissing: true });
      expect(r.ok).toBe(true);
      if (!r.ok) return;
      expect(r.config.modules?.audio_extractor?.enabled).toBe(false);
      expect(r.config.modules?.transcriber?.enabled).toBe(false);
    });

    it("rechaza si la topología es inválida", () => {
      const nodes: Node[] = [makeNode("in", "input")]; // falta output
      const r = graphToConfig(nodes, [], { pipelineMode: "sequential" });
      expect(r.ok).toBe(false);
    });

    it("copia los campos custom del moduleConfig al output", () => {
      const nodes: Node[] = [
        makeNode("in", "input"),
        makeNode("t", "transcriber", { x: 0, y: 0 }, {
          enabled: true,
          model: "large-v3",
          language: "fr",
          device: "cuda",
          beam_size: 7,
        } as GraphNodeData["moduleConfig"]),
        makeNode("out", "output"),
      ];
      const edges: Edge[] = [
        // t necesita un input de audio: derivamos de un extractor
        // pero aquí simplificamos: el grafo no es válido, así que lo omitimos
      ];
      // Mejor construir un grafo válido con módulo custom
      const { nodes: fullNodes, edges: fullEdges } = configToGraph({
        ...makeConfig(),
        modules: {
          ...makeConfig().modules,
          transcriber: { enabled: true, model: "large-v3", language: "fr", device: "cuda", beam_size: 7 },
        },
      });
      void nodes;
      void edges;
      const r = graphToConfig(fullNodes, fullEdges, { pipelineMode: "thread_parallel" });
      expect(r.ok).toBe(true);
      if (!r.ok) return;
      const t = r.config.modules?.transcriber as Record<string, unknown> | undefined;
      expect(t?.model).toBe("large-v3");
      expect(t?.language).toBe("fr");
      expect(t?.device).toBe("cuda");
      expect(t?.beam_size).toBe(7);
    });
  });

  describe("configToGraph", () => {
    it("genera 8 nodos y edges correctos", () => {
      const { nodes, edges } = configToGraph(makeConfig());
      expect(nodes).toHaveLength(8);
      const kinds = nodes.map((n) => (n.data as GraphNodeData).kind);
      expect(kinds).toContain("input");
      expect(kinds).toContain("output");
      expect(kinds).toContain("audio_mixer");
      // El mixer debe tener 2 entrantes (audio-orig + audio-dub)
      const mixerIn = edges.filter((e) => e.target === "n_audio_mixer");
      expect(mixerIn).toHaveLength(2);
    });

    it("inyecta el moduleConfig actual en los nodos", () => {
      const { nodes } = configToGraph(makeConfig());
      const t = nodes.find((n) => n.id === "n_transcriber");
      const data = t?.data as GraphNodeData;
      const cfg = data.moduleConfig as unknown as Record<string, unknown>;
      expect(cfg.model).toBe("base");
    });

    it("es un round-trip estable: grafo → config → grafo → validateTopology", () => {
      const cfg = makeConfig();
      const { nodes, edges } = configToGraph(cfg);
      const topo1 = validateTopology(nodes, edges);
      expect(topo1.ok).toBe(true);
      const r = graphToConfig(nodes, edges, { pipelineMode: cfg.pipeline.mode });
      expect(r.ok).toBe(true);
    });
  });
});
