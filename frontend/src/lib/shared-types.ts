/**
 * Shared Types - Barrel que re-exporta todos los tipos desde api.ts y types.ts.
 *
 * Esta interfaz existe para backwards compat.
 * api.ts es la fuente de verdad para tipos principales.
 * types.ts contiene tipos específicos para el sistema de salidas.
 */

// Tipos específicos para salidas desde types.ts
export type {
  BaseOutputConfig,
  AnyOutputConfig,
  OutputsResponse,
  OutputManagerState,
  OutputHandlers,
  OutputStatusCardProps,
  OutputConfigFormProps,
  OutputManagerCardProps,
  OutputFormState,
  ConfigUpdateTimeouts,
} from "./types";
