/**
 * Store - Centralized reactive state.
 *
 * Re-exports signals and effects.
 */

// Signals (reactive state atoms)
export {
  pipelineStatus,
  pipelineConfig,
  pipelineLogs,
  wsConnected,
  pollConnected,
  connectionMode,
  isOperationPending,
  throughputHistory,
  inputType,
  pipelineState,
  isPipelineRunning,
  isPipelineStopping,
  chunksProcessed,
  moduleStates,
  enabledModules,
  systemMetrics,
  connectionUrls,
  throughputAvg,
  pipelineLatency,
  cpuHistory,
  gpuHistory,
  cpuAlertActive,
  updateStatus,
  addLog,
  resetThroughput,
  presets,
  selectedPreset,
  currentLanguage,
  currentTheme,
} from "./signals";

// Effects (DOM update subscriptions)
export { startEffects, stopEffects } from "./effects";
