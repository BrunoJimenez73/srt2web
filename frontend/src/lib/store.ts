/**
 * Dashboard State Store - Gestión centralizada de estado.
 * 
 * Patrón: Store observable con suscriptores.
 * Características:
 * ✅ Estado centralizado y tipado
 * ✅ Suscripciones a cambios parciales
 * ✅ Inmutabilidad de estado
 * ✅ Logging de cambios
 * ✅ Compatibilidad 100% con código existente
 */

import type { Config, Status, LogMessage } from './types';

export interface DashboardState {
  config: Config | null;
  status: Status | null;
  localMode: 'local' | 'remote';
  wsConnected: boolean;
  logs: LogMessage[];
  isLoading: boolean;
  error: string | null;
}

type StateListener = (state: DashboardState) => void;
type PartialState = Partial<DashboardState>;

const INITIAL_STATE: DashboardState = {
  config: null,
  status: null,
  localMode: 'local',
  wsConnected: false,
  logs: [],
  isLoading: false,
  error: null,
};

class DashboardStore {
  private state: DashboardState;
  private listeners: Set<StateListener> = new Set();
  private history: DashboardState[] = [];
  private maxHistoryLength = 20;

  constructor(initialState: Partial<DashboardState> = {}) {
    this.state = { ...INITIAL_STATE, ...initialState };
  }

  /**
   * Obtener una copia inmutable del estado actual.
   */
  getState(): Readonly<DashboardState> {
    return Object.freeze({ ...this.state });
  }

  /**
   * Actualizar estado parcialmente.
   * Notifica a todos los suscriptores si hubo cambios.
   */
  setState(partial: PartialState): void {
    const prevState = this.state;
    const nextState = { ...prevState, ...partial };

    // Comparar shallow para evitar notificaciones innecesarias
    const hasChanges = Object.keys(partial).some(
      key => prevState[key as keyof DashboardState] !== nextState[key as keyof DashboardState]
    );

    if (!hasChanges) {
      return;
    }

    // Guardar en historial
    this.history.push({ ...prevState });
    if (this.history.length > this.maxHistoryLength) {
      this.history.shift();
    }

    this.state = nextState;

    // Notificar suscriptores
    this.notify();
  }

  /**
   * Suscribirse a cambios de estado.
   * Retorna función para cancelar suscripción.
   */
  subscribe(listener: StateListener): () => void {
    this.listeners.add(listener);
    
    // Notificar inmediatamente con estado actual
    listener(this.getState());

    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Notificar a todos los suscriptores.
   */
  notify(): void {
    const state = this.getState();
    this.listeners.forEach(listener => {
      try {
        listener(state);
      } catch (e) {
        console.error('[Store] Error in listener:', e);
      }
    });
  }

  /**
   * Resetear estado a valores iniciales.
   */
  reset(): void {
    this.state = { ...INITIAL_STATE };
    this.notify();
  }

  /**
   * Obtener historial de cambios.
   */
  getHistory(): Readonly<DashboardState[]> {
    return Object.freeze([...this.history]);
  }

  // ---------------------------------------------------------------------------
  // Métodos de conveniencia para actualizaciones comunes
  // ---------------------------------------------------------------------------

  setConfig(config: Config): void {
    this.setState({ config });
  }

  setStatus(status: Status): void {
    this.setState({ status, error: null });
  }

  setWsConnected(connected: boolean): void {
    this.setState({ wsConnected: connected });
  }

  addLog(log: LogMessage): void {
    const maxLogs = 500;
    const logs = [...this.state.logs, log].slice(-maxLogs);
    this.setState({ logs });
  }

  setLoading(loading: boolean): void {
    this.setState({ isLoading: loading });
  }

  setError(error: string | null): void {
    this.setState({ error, isLoading: false });
  }

  clearLogs(): void {
    this.setState({ logs: [] });
  }
}

// Instancia singleton global para el dashboard
export const dashboardStore = new DashboardStore();

// Exportar también para uso en módulos individuales
export default dashboardStore;