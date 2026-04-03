/**
 * Store centralizado para el estado de la aplicación
 * Implementa un patrón observer simple para actualizaciones reactivas
 */

import type { Config, Status, LogMessage, ModuleStatus } from './types';

/**
 * Estado global del dashboard
 */
export interface DashboardState {
  config: Config | null;
  status: Status | null;
  wsConnected: boolean;
  localMode: 'local' | 'remote';
  isLoading: boolean;
  error: string | null;
}

/**
 * Tipo para las funciones listener
 */
type StateListener = (state: DashboardState) => void;

/**
 * Store centralizado para el estado del dashboard
 */
class DashboardStore {
  private static instance: DashboardStore;
  private state: DashboardState = {
    config: null,
    status: null,
    wsConnected: false,
    localMode: 'local',
    isLoading: false,
    error: null,
  };
  private listeners: Set<StateListener> = new Set();

  private constructor() {}

  /**
   * Obtiene la instancia singleton del store
   */
  static getInstance(): DashboardStore {
    if (!DashboardStore.instance) {
      DashboardStore.instance = new DashboardStore();
    }
    return DashboardStore.instance;
  }

  /**
   * Suscribe un listener a los cambios de estado
   */
  subscribe(listener: StateListener): () => void {
    this.listeners.add(listener);
    // Call immediately with current state
    listener(this.state);
    
    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Actualiza el estado con nuevos valores
   */
  updateState(updates: Partial<DashboardState>): void {
    const previousState = { ...this.state };
    this.state = { ...this.state, ...updates };
    
    // Notify listeners only if state changed
    if (JSON.stringify(previousState) !== JSON.stringify(this.state)) {
      this.notifyListeners();
    }
  }

  /**
   * Obtiene el estado actual
   */
  getState(): DashboardState {
    return { ...this.state };
  }

  /**
   * Obtiene un valor específico del estado
   */
  get<K extends keyof DashboardState>(key: K): DashboardState[K] {
    return this.state[key];
  }

  /**
   * Actualiza la configuración
   */
  setConfig(config: Config | null): void {
    this.updateState({ config });
  }

  /**
   * Actualiza el estado del pipeline
   */
  setStatus(status: Status | null): void {
    this.updateState({ status });
  }

  /**
   * Actualiza el estado de conexión WebSocket
   */
  setWsConnected(connected: boolean): void {
    this.updateState({ wsConnected: connected });
  }

  /**
   * Actualiza el modo local/remoto
   */
  setLocalMode(mode: 'local' | 'remote'): void {
    this.updateState({ localMode: mode });
  }

  /**
   * Actualiza el estado de carga
   */
  setLoading(isLoading: boolean): void {
    this.updateState({ isLoading });
  }

  /**
   * Actualiza el estado de error
   */
  setError(error: string | null): void {
    this.updateState({ error });
  }

  /**
   * Limpia el error
   */
  clearError(): void {
    this.updateState({ error: null });
  }

  /**
   * Obtiene el estado de un módulo específico
   */
  getModuleStatus(moduleName: string): ModuleStatus | undefined {
    return this.state.status?.modules?.find(m => m.name === moduleName);
  }

  /**
   * Verifica si un módulo está habilitado
   */
  isModuleEnabled(moduleName: string): boolean {
    const module = this.getModuleStatus(moduleName);
    return module?.enabled ?? false;
  }

  /**
   * Verifica si el pipeline está corriendo
   */
  isPipelineRunning(): boolean {
    return this.state.status?.state === 'running';
  }

  /**
   * Notifica a todos los listeners sobre cambios
   */
  private notifyListeners(): void {
    this.listeners.forEach(listener => {
      try {
        listener(this.state);
      } catch (error) {
        console.error('Error in store listener:', error);
      }
    });
  }

  /**
   * Reinicia el store a su estado inicial
   */
  reset(): void {
    this.state = {
      config: null,
      status: null,
      wsConnected: false,
      localMode: 'local',
      isLoading: false,
      error: null,
    };
    this.notifyListeners();
  }
}

// Exportar instancia singleton
export const store = DashboardStore.getInstance();

// Exportar la clase para testing
export { DashboardStore };