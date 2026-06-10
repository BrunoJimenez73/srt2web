import { describe, expect, it } from "vitest";
import {
  getNodeDef,
  isNodeKind,
  nodeKindToModuleKey,
  getInputTypes,
  getOutputTypes,
  HANDLE_TYPE_COLOR,
  NODE_CATALOG,
  type NodeKind,
} from "./nodeCatalog";

describe("nodeCatalog", () => {
  describe("NODE_CATALOG", () => {
    it("contiene exactamente 8 nodos", () => {
      expect(NODE_CATALOG).toHaveLength(8);
    });

    it("cada nodo tiene id, label, descripción, category y handles", () => {
      for (const def of NODE_CATALOG) {
        expect(def.kind).toBeTruthy();
        expect(def.label).toBeTruthy();
        expect(def.description).toBeTruthy();
        expect(["source", "processing", "sink"]).toContain(def.category);
        expect(Array.isArray(def.inputs)).toBe(true);
        expect(Array.isArray(def.outputs)).toBe(true);
      }
    });

    it("los ids de handle son únicos dentro de cada nodo", () => {
      for (const def of NODE_CATALOG) {
        const inIds = new Set(def.inputs.map((h) => h.id));
        expect(inIds.size).toBe(def.inputs.length);
        const outIds = new Set(def.outputs.map((h) => h.id));
        expect(outIds.size).toBe(def.outputs.length);
      }
    });
  });

  describe("getNodeDef", () => {
    it("devuelve el def correcto para un kind válido", () => {
      const def = getNodeDef("transcriber");
      expect(def.label).toBe("Whisper (Transcriber)");
      expect(def.category).toBe("processing");
    });
  });

  describe("isNodeKind", () => {
    it("acepta todos los kinds del catálogo", () => {
      const kinds: NodeKind[] = [
        "input",
        "audio_extractor",
        "transcriber",
        "translator",
        "subtitle_generator",
        "tts_engine",
        "audio_mixer",
        "output",
      ];
      for (const k of kinds) {
        expect(isNodeKind(k)).toBe(true);
      }
    });

    it("rechaza strings que no son kinds", () => {
      expect(isNodeKind("not-a-node")).toBe(false);
      expect(isNodeKind("")).toBe(false);
      expect(isNodeKind("INPUT")).toBe(false); // case-sensitive
    });
  });

  describe("nodeKindToModuleKey", () => {
    it("input y output no están en ModulesConfig", () => {
      expect(nodeKindToModuleKey("input")).toBeNull();
      expect(nodeKindToModuleKey("output")).toBeNull();
    });

    it("los nodos de procesamiento están en ModulesConfig", () => {
      expect(nodeKindToModuleKey("audio_extractor")).toBe("audio_extractor");
      expect(nodeKindToModuleKey("transcriber")).toBe("transcriber");
      expect(nodeKindToModuleKey("translator")).toBe("translator");
      expect(nodeKindToModuleKey("subtitle_generator")).toBe("subtitle_generator");
      expect(nodeKindToModuleKey("tts_engine")).toBe("tts_engine");
      expect(nodeKindToModuleKey("audio_mixer")).toBe("audio_mixer");
    });
  });

  describe("tipos de handles", () => {
    it("input produce video", () => {
      expect(getOutputTypes("input")).toEqual(["video"]);
      expect(getInputTypes("input")).toEqual([]);
    });

    it("output consume video + audio + subtitles", () => {
      const inputs = getInputTypes("output");
      expect(inputs).toContain("video");
      expect(inputs).toContain("audio");
      expect(inputs).toContain("subtitles");
    });

    it("transcriber consume audio y produce transcript", () => {
      expect(getInputTypes("transcriber")).toEqual(["audio"]);
      expect(getOutputTypes("transcriber")).toEqual(["transcript"]);
    });

    it("audio_mixer tiene 2 entradas de audio", () => {
      const def = getNodeDef("audio_mixer");
      expect(def.inputs).toHaveLength(2);
      expect(def.inputs.every((h) => h.type === "audio")).toBe(true);
    });
  });

  describe("HANDLE_TYPE_COLOR", () => {
    it("define colores para los 4 tipos", () => {
      expect(HANDLE_TYPE_COLOR.video).toBeTruthy();
      expect(HANDLE_TYPE_COLOR.audio).toBeTruthy();
      expect(HANDLE_TYPE_COLOR.transcript).toBeTruthy();
      expect(HANDLE_TYPE_COLOR.subtitles).toBeTruthy();
    });
  });
});
