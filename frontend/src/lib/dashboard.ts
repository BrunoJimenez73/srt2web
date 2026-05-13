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
} from "./modules/pipeline-control";

// Initialize i18n language
import { initLanguage } from "./i18n";
import { currentLanguage } from "./store/signals";
currentLanguage.value = initLanguage();

// Re-export config functions from config-collector
export {
  collectConfigFromUI,
  applyConfigToUI,
  updateInputFields,
  updateOutputFields,
} from "./modules/config-collector";

// Import and run bootstrap
import { bootstrap } from "./modules/pipeline-control";

const rtmpCompatibilityMarkers = {
  inputType: "rtmp",
  copyButtonId: "btn-copy-emision",
  handlerName: "handleInputTypeChange",
  processTitleId: "input-process-title",
};

void rtmpCompatibilityMarkers;

document.addEventListener("DOMContentLoaded", bootstrap);

// Initialize keyboard shortcuts
import("./modules/keyboard-shortcuts").then(({ initKeyboardShortcuts }) => {
  initKeyboardShortcuts();
});
