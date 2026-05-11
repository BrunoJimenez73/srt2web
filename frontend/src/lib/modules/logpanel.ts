/**
 * Módulo para el panel de logs
 * Maneja la visualización, filtrado y gestión de logs
 */

import type { LogMessage } from '../types';
import { formatTimestamp } from '../utils';

// DOM Elements
let logContent: HTMLDivElement | null = null;
let logPanel: Element | null = null;
let logEmpty: HTMLDivElement | null = null;
let logSearch: HTMLInputElement | null = null;
let collapseIcon: HTMLSpanElement | null = null;

// State
const maxLogs = 500;
let currentFilter = '';
let isCollapsed = true;

/**
 * Alterna el estado colapsado/expandido del panel de logs
 */
export function toggleLogPanel(): void {
  if (!logPanel) return;
  
  isCollapsed = !isCollapsed;
  logPanel.classList.toggle('collapsed', isCollapsed);
  
  if (collapseIcon) {
    collapseIcon.textContent = isCollapsed ? '▶' : '▼';
  }
}

/**
 * Escapa caracteres HTML para prevenir XSS
 */
function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Agrega un log al panel
 * @param level - Nivel del log (info, warning, error, success)
 * @param message - Mensaje del log
 * @param timestamp - Timestamp opcional (ISO string)
 */
export function addLog(level: LogMessage['level'], message: string, timestamp?: string): void {
  console.log('[addLog] Called:', level, message?.substring(0, 50));
  if (!logContent) {
    console.error('Log content element not found');
    return;
  }
  
  // Hide empty state when adding first log
  if (logEmpty && logEmpty.parentElement === logContent) {
    logEmpty.remove();
    logEmpty = null;
  }
  
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  entry.setAttribute('role', 'listitem');
  entry.dataset.level = level;
  entry.dataset.message = message.toLowerCase();
  
  const time = timestamp ? formatTimestamp(timestamp) : new Date().toLocaleTimeString('es-ES');
  
  entry.innerHTML = `
    <span class="log-timestamp">${time}</span>
    <span class="log-level ${level}">[${level.toUpperCase()}]</span>
    <span class="log-message">${escapeHtml(message)}</span>
  `;
  
  // Apply current filter
  if (currentFilter && !entry.dataset.message.includes(currentFilter.toLowerCase())) {
    entry.style.display = 'none';
  }
  
  logContent.appendChild(entry);
  
  // Limit number of logs
  while (logContent.children.length > maxLogs) {
    if (logContent.firstChild) {
      logContent.removeChild(logContent.firstChild);
    }
  }
  
  // Scroll to bottom
  logContent.scrollTop = logContent.scrollHeight;
}

/**
 * Filtra los logs según el texto de búsqueda
 * @param filter - Texto a filtrar
 */
export function filterLogs(filter: string): void {
  currentFilter = filter.toLowerCase();
  
  const entries = logContent?.querySelectorAll('.log-entry');
  entries?.forEach((entry) => {
    const el = entry as HTMLElement;
    if (currentFilter) {
      const matches = el.dataset.message?.includes(currentFilter);
      el.style.display = matches ? '' : 'none';
    } else {
      el.style.display = '';
    }
  });
}

/**
 * Limpia todos los logs
 */
export function clearLogs(): void {
  if (!logContent) return;
  
  logContent.innerHTML = '';
  
  // Restore empty state
  logEmpty = document.createElement('div');
  logEmpty.className = 'log-empty';
  logEmpty.id = 'log-empty';
  logEmpty.innerHTML = `
    <span class="log-empty-icon">📝</span>
    <span class="log-empty-text">Sin registros aún</span>
  `;
  logContent.appendChild(logEmpty);
  
  currentFilter = '';
  if (logSearch) {
    logSearch.value = '';
  }
}

/**
 * Inicializa el panel de logs
 */
export function initLogPanel(): void {
  // Get DOM elements
  logContent = document.getElementById('log-content') as HTMLDivElement;
  logPanel = document.querySelector('.log-panel');
  logEmpty = document.getElementById('log-empty') as HTMLDivElement;
  logSearch = document.getElementById('log-search') as HTMLInputElement;
  collapseIcon = document.getElementById('log-collapse-icon') as HTMLSpanElement;
  
  // Setup search filter
  logSearch?.addEventListener('input', (e) => {
    const value = (e.target as HTMLInputElement).value;
    filterLogs(value);
  });
  
  // Expose global functions for onclick attributes
  (window as unknown as { 
    addLog: typeof addLog; 
    toggleLogPanel: typeof toggleLogPanel; 
    clearLogs: typeof clearLogs; 
  }).addLog = addLog;
  
  (window as unknown as { 
    addLog: typeof addLog; 
    toggleLogPanel: typeof toggleLogPanel; 
    clearLogs: typeof clearLogs; 
  }).toggleLogPanel = toggleLogPanel;
  
  (window as unknown as { 
    addLog: typeof addLog; 
    toggleLogPanel: typeof toggleLogPanel; 
    clearLogs: typeof clearLogs; 
  }).clearLogs = clearLogs;
}

/**
 * Obtiene el estado actual del panel
 */
export function getLogPanelState(): { isCollapsed: boolean; filter: string; logCount: number } {
  const logCount = logContent?.querySelectorAll('.log-entry').length || 0;
  return {
    isCollapsed,
    filter: currentFilter,
    logCount
  };
}