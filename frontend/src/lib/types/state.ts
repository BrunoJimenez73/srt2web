/**
 * State types - Formal state definitions replacing hardcoded string literals.
 * These enums and types provide a single source of truth for all UI states.
 */

import type { Status, LogMessage } from '../api';

// ── Pipeline State ──────────────────────────────────────────────────────────

export enum PipelineState {
  STOPPED = 'stopped',
  RUNNING = 'running',
  STARTING = 'starting',
  STOPPING = 'stopping',
  ERROR = 'error',
}

export const PIPELINE_STATE_LABELS: Record<PipelineState, string> = {
  [PipelineState.STOPPED]: 'APAGADO',
  [PipelineState.RUNNING]: 'ACTIVO',
  [PipelineState.STARTING]: 'INICIANDO',
  [PipelineState.STOPPING]: 'DETENIENDO',
  [PipelineState.ERROR]: 'ERROR',
};

export function normalizePipelineState(state: string | undefined): PipelineState {
  switch (state) {
    case 'running': return PipelineState.RUNNING;
    case 'starting': return PipelineState.STARTING;
    case 'stopping': return PipelineState.STOPPING;
    case 'error': return PipelineState.ERROR;
    default: return PipelineState.STOPPED;
  }
}

// ── Module State ─────────────────────────────────────────────────────────────

export enum ModuleState {
  IDLE = 'idle',
  RUNNING = 'running',
  ERROR = 'error',
  DISABLED = 'disabled',
}

export const MODULE_STATE_LABELS: Record<ModuleState, string> = {
  [ModuleState.IDLE]: 'IDLE',
  [ModuleState.RUNNING]: 'RUNNING',
  [ModuleState.ERROR]: 'ERROR',
  [ModuleState.DISABLED]: 'DISABLED',
};

export function getModuleState(module: Status['modules'][number]): ModuleState {
  if (!module.enabled) return ModuleState.DISABLED;
  if (module.state === 'error') return ModuleState.ERROR;
  if (module.state === 'running') return ModuleState.RUNNING;
  return ModuleState.IDLE;
}

// ── Connection State ─────────────────────────────────────────────────────────

export enum ConnectionMode {
  LOCAL = 'local',
  REMOTE = 'remote',
}

export const CONNECTION_MODE_LABELS: Record<ConnectionMode, string> = {
  [ConnectionMode.LOCAL]: 'LOCAL',
  [ConnectionMode.REMOTE]: 'REMOTE',
};
