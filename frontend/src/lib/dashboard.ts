/**
 * Dashboard - Entry point for the SRT2Web frontend.
 *
 * This file has been refactored to import from modular components:
 * - config-collector.ts: Config collection and application
 * - pipeline-control.ts: Pipeline control, file input, RTMP helpers, initialization
 *
 * State management is delegated to signals (store/signals.ts).
 * DOM updates are handled automatically by effects (store/effects.ts).
 */

// Re-export all functions from pipeline-control for backwards compatibility
export {
  handleStart,
  handleStop,
  handleSaveConfig,
  updateRtmpUrl,
  fileInputPlay,
  fileInputPause,
  fileInputSeek,
  setupFilePlayerControls,
  stopFileInfoPolling,
  initDashboard,
  cleanup,
  setupEventListeners,
  refreshMetrics,
  bootstrap,
} from './modules/pipeline-control';

// Re-export config functions from config-collector
export {
  collectConfigFromUI,
  applyConfigToUI,
  updateInputFields,
  updateOutputFields,
} from './modules/config-collector';

// Import and run bootstrap
import { bootstrap } from './modules/pipeline-control';

const rtmpCompatibilityMarkers = {
  inputType: 'rtmp',
  copyButtonId: 'btn-copy-emision',
  handlerName: 'handleInputTypeChange',
  processTitleId: 'input-process-title',
};

void rtmpCompatibilityMarkers;

// Initialize on both DOMContentLoaded and load events for robustness
document.addEventListener('DOMContentLoaded', bootstrap);
document.addEventListener('load', () => {
  // Also try on load as fallback
  setTimeout(() => {
    // Re-import and call initDashboard and refreshMetrics for fallback
    import('./modules/pipeline-control').then(({ initDashboard, refreshMetrics }) => {
      initDashboard();
      refreshMetrics();
    });
  }, 500);
});

// Initialize keyboard shortcuts
import('./modules/keyboard-shortcuts').then(({ initKeyboardShortcuts }) => {
  initKeyboardShortcuts();
});
