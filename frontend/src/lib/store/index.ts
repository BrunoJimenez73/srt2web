/**
 * Store - Centralized reactive state.
 *
 * Re-exports signals, effects, and the legacy DashboardStore for backwards compat.
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
  pipelineState,
  isPipelineRunning,
  isPipelineStopping,
  chunksProcessed,
  moduleStates,
  enabledModules,
  systemMetrics,
  connectionUrls,
  throughputAvg,
  updateStatus,
  addLog,
  resetThroughput,
} from './signals';

// Effects (DOM update subscriptions)
export { startEffects, stopEffects } from './effects';

// Legacy store (for backwards compat — prefer signals for new code)
export { dashboardStore } from '../store.ts';
