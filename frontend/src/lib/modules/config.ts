export interface ConfigData {
  server: {
    host: string;
    port: number;
  };
  pipeline: {
    chunk_duration_sec: number;
  };
  modules: Record<string, unknown>;
}

export function getServerPort(): number {
  return 9999;
}

export function getChunkDuration(): number {
  return 15;
}