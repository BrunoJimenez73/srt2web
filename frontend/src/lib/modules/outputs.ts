import { apiCall } from '../api';
import { showToast } from '../utils';

export interface OutputStatus {
  name: string;
  type: string;
  state: string;
  enabled: boolean;
  processed_chunks: number;
  last_process_time_ms: number;
  extra?: Record<string, any>;
  stream_info?: Record<string, any>;
  error?: string;
}

export interface OutputConfig {
  type: string;
  name?: string;
  config?: Record<string, any>;
}

let outputs: OutputStatus[] = [];
let outputListeners: ((outputs: OutputStatus[]) => void)[] = [];

export async function fetchOutputs(): Promise<OutputStatus[]> {
  try {
    const response = await apiCall<{ outputs: OutputStatus[] }>('GET', 'api/outputs');
    outputs = response.outputs || [];
    notifyListeners();
    return outputs;
  } catch (e) {
    console.error('Failed to fetch outputs:', e);
    return [];
  }
}

export async function fetchAvailableTypes(): Promise<string[]> {
  try {
    const response = await apiCall<{ available_types: string[] }>('GET', 'api/outputs/available');
    return response.available_types || [];
  } catch (e) {
    console.error('Failed to fetch available output types:', e);
    return ['web', 'recording', 'srt', 'rtmp'];
  }
}

export async function addOutput(config: OutputConfig): Promise<boolean> {
  try {
    await apiCall('POST', 'api/outputs', config);
    showToast('Salida añadida correctamente', 'success');
    await fetchOutputs();
    return true;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    showToast(`Error al añadir salida: ${msg}`, 'error');
    return false;
  }
}

export async function removeOutput(name: string): Promise<boolean> {
  try {
    await apiCall('DELETE', `api/outputs/${name}`);
    showToast('Salida eliminada', 'success');
    await fetchOutputs();
    return true;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    showToast(`Error al eliminar: ${msg}`, 'error');
    return false;
  }
}

export async function toggleOutput(name: string, enabled: boolean): Promise<boolean> {
  try {
    await apiCall('POST', `api/outputs/${name}/toggle`, { enabled });
    await fetchOutputs();
    return true;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    showToast(`Error: ${msg}`, 'error');
    return false;
  }
}

export async function updateOutput(name: string, config: Record<string, any>): Promise<boolean> {
  try {
    await apiCall('PUT', `api/outputs/${name}`, { config });
    showToast('Salida actualizada', 'success');
    await fetchOutputs();
    return true;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    showToast(`Error: ${msg}`, 'error');
    return false;
  }
}

export function getOutputs(): OutputStatus[] {
  return outputs;
}

export function onOutputsChange(listener: (outputs: OutputStatus[]) => void): () => void {
  outputListeners.push(listener);
  return () => {
    outputListeners = outputListeners.filter(l => l !== listener);
  };
}

function notifyListeners(): void {
  outputListeners.forEach(l => l(outputs));
}

export function getOutputIcon(type: string): string {
  const icons: Record<string, string> = {
    web: '🌐',
    recording: '⏺',
    srt: '📡',
    rtmp: '📺',
    file: '📁',
    hls: '🌐',
  };
  return icons[type] || '📤';
}

export function getOutputTypeName(type: string): string {
  const names: Record<string, string> = {
    web: 'HLS',
    recording: 'REC',
    srt: 'SRT',
    rtmp: 'RTMP',
    file: 'FILE',
    hls: 'HLS',
  };
  return names[type] || type.toUpperCase();
}

export function formatOutputState(output: OutputStatus): string {
  if (output.error) return 'Error';
  if (!output.enabled) return 'Deshabilitado';
  return output.state === 'running' ? 'Activo' : 'Inactivo';
}
