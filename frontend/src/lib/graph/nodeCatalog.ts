/**
 * Catálogo de nodos para el editor visual de pipeline (`/graph`).
 *
 * Define los 8 nodos que pueden aparecer en el grafo y la forma de sus
 * handles tipados (video / audio / transcript / subtitles). Los tipos se
 * derivan de los campos de `core.module_base.PipelineData`:
 *
 * - video: video_chunk_path, video_path
 * - audio: audio_chunk_path, audio_samples, dubbed_audio_path, mixed_audio_path
 * - transcript: transcript, transcript_segments, translated_text
 * - subtitles: subtitles_path
 *
 * Los handles usan IDs únicos por nodo. Para nodos con múltiples handles
 * del mismo tipo (p.ej. `audio_mixer` con `audio-orig` y `audio-dub`), el
 * ID incluye un sufijo. `getHandleDataType` en `typedEdge.ts` resuelve el
 * tipo a partir del ID.
 */
import type { ModulesConfig } from "../types/api";

// ── Tipos públicos ──────────────────────────────────────────────────────────

export type NodeKind =
  | "input"
  | "audio_extractor"
  | "transcriber"
  | "translator"
  | "subtitle_generator"
  | "tts_engine"
  | "audio_mixer"
  | "output";

export type HandleType = "video" | "audio" | "transcript" | "subtitles";

export type NodeCategory = "source" | "processing" | "sink";

export interface HandleSpec {
  /** ID único del handle dentro del nodo. Se usa como `handleId` en React Flow. */
  id: string;
  /** Tipo de dato que transporta este handle. */
  type: HandleType;
  /** Etiqueta visible. */
  label: string;
  /** Posición en el nodo. */
  position: "top" | "bottom" | "left" | "right";
}

export type FieldType = "boolean" | "number" | "string" | "enum";

export interface FieldDef {
  key: string;
  label: string;
  type: FieldType;
  /** Valores permitidos cuando type = "enum". */
  options?: readonly string[];
  /** Min/max cuando type = "number". */
  min?: number;
  max?: number;
  step?: number;
  /** Descripción tooltip. */
  description?: string;
}

export type ConfigLocation =
  | { kind: "modules"; key: keyof ModulesConfig }
  | { kind: "input" }
  | { kind: "output" };

export interface NodeDef {
  kind: NodeKind;
  label: string;
  description: string;
  category: NodeCategory;
  configLocation: ConfigLocation;
  inputs: readonly HandleSpec[];
  outputs: readonly HandleSpec[];
  /** Schema del inspector. Vacío si la config se edita fuera del grafo. */
  configFields: readonly FieldDef[];
}

// ── Definición del catálogo ────────────────────────────────────────────────

export const HANDLE_TYPE_COLOR: Record<HandleType, string> = {
  video: "#ef4444",
  audio: "#10b981",
  transcript: "#3b82f6",
  subtitles: "#f59e0b",
};

export const HANDLE_TYPE_LABEL: Record<HandleType, string> = {
  video: "Video",
  audio: "Audio",
  transcript: "Transcripción",
  subtitles: "Subtítulos",
};

export const NODE_KIND_TO_CATEGORY: Record<NodeKind, NodeCategory> = {
  input: "source",
  audio_extractor: "processing",
  transcriber: "processing",
  translator: "processing",
  subtitle_generator: "processing",
  tts_engine: "processing",
  audio_mixer: "processing",
  output: "sink",
};

export const WHISPER_MODELS = [
  "tiny",
  "base",
  "small",
  "medium",
  "large",
  "large-v2",
  "large-v3",
] as const;

export const LANGUAGES = [
  "auto",
  "en",
  "es",
  "fr",
  "de",
  "it",
  "pt",
  "ja",
  "zh",
  "ko",
  "ru",
] as const;

export const DEVICES = ["auto", "cpu", "cuda", "mps"] as const;

export const TTS_ENGINES = ["edge-tts", "piper", "elevenlabs"] as const;

export const SUBTITLE_FORMATS = ["webvtt", "srt", "ass"] as const;

const NO_FIELDS: readonly FieldDef[] = [];

export const NODE_CATALOG: ReadonlyArray<NodeDef> = [
  {
    kind: "input",
    label: "Input",
    description: "Fuente de video (SRT / RTMP / File / WebRTC). Configurar en el dashboard principal.",
    category: "source",
    configLocation: { kind: "input" },
    inputs: [],
    outputs: [{ id: "video", type: "video", label: "Video", position: "right" }],
    configFields: NO_FIELDS,
  },
  {
    kind: "audio_extractor",
    label: "Audio Extractor",
    description: "Extrae la pista de audio del video con FFmpeg.",
    category: "processing",
    configLocation: { kind: "modules", key: "audio_extractor" },
    inputs: [{ id: "video", type: "video", label: "Video", position: "left" }],
    outputs: [
      { id: "video", type: "video", label: "Video", position: "right" },
      { id: "audio", type: "audio", label: "Audio", position: "right" },
    ],
    configFields: NO_FIELDS,
  },
  {
    kind: "transcriber",
    label: "Whisper (Transcriber)",
    description: "Transcribe el audio a texto con faster-whisper.",
    category: "processing",
    configLocation: { kind: "modules", key: "transcriber" },
    inputs: [{ id: "audio", type: "audio", label: "Audio", position: "left" }],
    outputs: [
      { id: "transcript", type: "transcript", label: "Transcripción", position: "right" },
    ],
    configFields: [
      {
        key: "model",
        label: "Modelo",
        type: "enum",
        options: WHISPER_MODELS,
        description: "Tamaño del modelo Whisper. tiny/base = rápidos, large = más preciso.",
      },
      {
        key: "language",
        label: "Idioma origen",
        type: "enum",
        options: LANGUAGES,
        description: "'auto' detecta automáticamente.",
      },
      {
        key: "device",
        label: "Dispositivo",
        type: "enum",
        options: DEVICES,
        description: "auto = CUDA si está disponible, si no CPU.",
      },
      {
        key: "beam_size",
        label: "Beam size",
        type: "number",
        min: 1,
        max: 10,
        step: 1,
        description: "Mayor = más preciso pero más lento.",
      },
    ],
  },
  {
    kind: "translator",
    label: "Translator (Argos)",
    description: "Traduce la transcripción al idioma destino.",
    category: "processing",
    configLocation: { kind: "modules", key: "translator" },
    inputs: [{ id: "transcript", type: "transcript", label: "Transcripción", position: "left" }],
    outputs: [
      { id: "transcript", type: "transcript", label: "Traducción", position: "right" },
    ],
    configFields: [
      {
        key: "source_lang",
        label: "Idioma origen",
        type: "enum",
        options: LANGUAGES,
      },
      {
        key: "target_lang",
        label: "Idioma destino",
        type: "enum",
        options: LANGUAGES,
        description: "Idioma al que se traduce la transcripción.",
      },
    ],
  },
  {
    kind: "subtitle_generator",
    label: "Subtitle Generator",
    description: "Genera archivos de subtítulos a partir de la transcripción.",
    category: "processing",
    configLocation: { kind: "modules", key: "subtitle_generator" },
    inputs: [{ id: "transcript", type: "transcript", label: "Transcripción", position: "left" }],
    outputs: [
      { id: "subtitles", type: "subtitles", label: "Subtítulos", position: "right" },
    ],
    configFields: [
      {
        key: "format",
        label: "Formato",
        type: "enum",
        options: SUBTITLE_FORMATS,
      },
      {
        key: "use_translated",
        label: "Usar traducción",
        type: "boolean",
        description: "Si está activo usa la traducción; si no, el texto original.",
      },
      {
        key: "chunk_duration",
        label: "Duración chunk (s)",
        type: "number",
        min: 1,
        max: 60,
        step: 1,
      },
    ],
  },
  {
    kind: "tts_engine",
    label: "TTS (Piper / Edge)",
    description: "Síntesis de voz para doblaje automático.",
    category: "processing",
    configLocation: { kind: "modules", key: "tts_engine" },
    inputs: [{ id: "transcript", type: "transcript", label: "Transcripción", position: "left" }],
    outputs: [
      { id: "audio", type: "audio", label: "Audio doblado", position: "right" },
    ],
    configFields: [
      {
        key: "engine",
        label: "Motor",
        type: "enum",
        options: TTS_ENGINES,
      },
      {
        key: "device",
        label: "Dispositivo",
        type: "enum",
        options: DEVICES,
      },
      {
        key: "voice",
        label: "Voz",
        type: "string",
        description: "Nombre de la voz (depende del motor). Ej. 'es_ES-sharvard-medium'.",
      },
      {
        key: "speed",
        label: "Velocidad",
        type: "number",
        min: 0.5,
        max: 2.0,
        step: 0.1,
      },
    ],
  },
  {
    kind: "audio_mixer",
    label: "Audio Mixer",
    description: "Mezcla audio original + doblaje. El único nodo que admite 2 entradas del mismo tipo.",
    category: "processing",
    configLocation: { kind: "modules", key: "audio_mixer" },
    inputs: [
      { id: "audio-orig", type: "audio", label: "Audio original", position: "left" },
      { id: "audio-dub", type: "audio", label: "Audio doblado", position: "left" },
    ],
    outputs: [
      { id: "audio", type: "audio", label: "Audio mezclado", position: "right" },
    ],
    configFields: [
      { key: "original_volume", label: "Volumen original", type: "number", min: 0, max: 2, step: 0.05 },
      { key: "tts_volume", label: "Volumen TTS", type: "number", min: 0, max: 2, step: 0.05 },
    ],
  },
  {
    kind: "output",
    label: "Output",
    description: "Salida final (HLS, RTMP, SRT, File, Recording). Configurar en el dashboard principal.",
    category: "sink",
    configLocation: { kind: "output" },
    inputs: [
      { id: "video", type: "video", label: "Video", position: "left" },
      { id: "audio", type: "audio", label: "Audio", position: "left" },
      { id: "subtitles", type: "subtitles", label: "Subtítulos", position: "left" },
    ],
    outputs: [],
    configFields: NO_FIELDS,
  },
];

// ── Helpers ────────────────────────────────────────────────────────────────

const CATALOG_BY_KIND: Record<NodeKind, NodeDef> = NODE_CATALOG.reduce(
  (acc, def) => {
    acc[def.kind] = def;
    return acc;
  },
  {} as Record<NodeKind, NodeDef>,
);

export function getNodeDef(kind: NodeKind): NodeDef {
  return CATALOG_BY_KIND[kind];
}

export function isNodeKind(value: string): value is NodeKind {
  return value in CATALOG_BY_KIND;
}

/**
 * Mapea un NodeKind a la clave de `ModulesConfig` o null si no está en modules
 * (caso de `input` y `output`).
 */
export function nodeKindToModuleKey(
  kind: NodeKind,
): keyof ModulesConfig | null {
  const def = CATALOG_BY_KIND[kind];
  if (!def) return null;
  return def.configLocation.kind === "modules" ? def.configLocation.key : null;
}

/** Construye un handle por defecto con posición según el lado. */
export function defaultHandlePosition(
  isSource: boolean,
): "top" | "bottom" | "left" | "right" {
  return isSource ? "right" : "left";
}

/** Lista los handle types que produce este nodo (útil para edges). */
export function getOutputTypes(kind: NodeKind): HandleType[] {
  const def = CATALOG_BY_KIND[kind];
  if (!def) return [];
  const types = new Set<HandleType>();
  for (const h of def.outputs) types.add(h.type);
  return Array.from(types);
}

/** Lista los handle types que acepta este nodo como entrada. */
export function getInputTypes(kind: NodeKind): HandleType[] {
  const def = CATALOG_BY_KIND[kind];
  if (!def) return [];
  const types = new Set<HandleType>();
  for (const h of def.inputs) types.add(h.type);
  return Array.from(types);
}
