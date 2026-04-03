/**
 * Índice de módulos del frontend
 * Exporta todas las funciones y utilidades de los módulos
 */

// Módulo de UI
export {
  moduleToCard,
  moduleToIndicator,
  updatePipelineUI,
  updateModuleStatus,
  updateSystemMetrics,
  updateModulePerformanceMetrics,
  updateUrls,
  handleInputTypeChange,
  handleOutputFormatChange,
  copyUrl,
  showToast
} from './ui';

// Módulo de configuración
export {
  applyConfigToUI,
  collectConfigFromUI,
  setupAutoSaveFields,
  updateConfigFieldDebounced
} from './config';

// Módulo de eventos
export {
  handleStart,
  handleStop,
  handleSaveConfig,
  updateConfigField,
  setupEventListeners,
  updateInputFields
} from './events';

// Módulo del reproductor
export {
  initHlsPlayer
} from './player';

// Módulo del header (seguridad)
export {
  initSecurityPanel,
  updateSecureState,
  cleanupSecurityPanel
} from './header';

// Módulo de notificaciones toast
export {
  showToast as showNotification,
  clearAllToasts,
  type ToastType
} from './toast';

// Módulo del panel de logs
export {
  initLogPanel,
  addLog,
  filterLogs,
  clearLogs,
  toggleLogPanel,
  getLogPanelState
} from './logpanel';