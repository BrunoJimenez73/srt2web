/**
 * Módulo para el panel de logs
 * Maneja la visualización, filtrado y gestión de logs
 */

import type { LogMessage } from "../types";
import { formatTimestamp } from "../utils";
import { t } from "../i18n";

// DOM Elements
let logContent: HTMLDivElement | null = null;
let logPanel: Element | null = null;
let logEmpty: HTMLDivElement | null = null;
let logSearch: HTMLInputElement | null = null;
let collapseIcon: HTMLSpanElement | null = null;
let logLevelFilter: HTMLSelectElement | null = null;
let logExportJson: HTMLButtonElement | null = null;
let logExportTxt: HTMLButtonElement | null = null;

// State
const maxLogs = 1000;
let currentFilter = "";
let currentLevel = "ALL";
let isCollapsed = true;
let filterDebounceTimeout: ReturnType<typeof setTimeout> | null = null;

/**
 * Alterna el estado colapsado/expandido del panel de logs
 */
export function toggleLogPanel(): void {
  if (!logPanel) return;

  isCollapsed = !isCollapsed;
  logPanel.classList.toggle("collapsed", isCollapsed);

  if (collapseIcon) {
    collapseIcon.textContent = isCollapsed ? "▶" : "▼";
  }
}

/**
 * Escapa caracteres HTML para prevenir XSS
 */
function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Agrega un log al panel
 * @param level - Nivel del log (info, warning, error, success)
 * @param message - Mensaje del log
 * @param timestamp - Timestamp opcional (ISO string)
 */
export function addLog(
  level: LogMessage["level"],
  message: string,
  timestamp?: string,
): void {
  if (!logContent) return;

  // Hide empty state when adding first log
  if (logEmpty && logEmpty.parentElement === logContent) {
    logEmpty.remove();
    logEmpty = null;
  }

  const entry = document.createElement("div");
  entry.className = "log-entry";
  entry.setAttribute("role", "listitem");
  entry.dataset.level = level;
  entry.dataset.message = message.toLowerCase();

  const time = timestamp
    ? formatTimestamp(timestamp)
    : new Date().toLocaleTimeString("es-ES");
  const levelLower = level.toLowerCase();

  entry.innerHTML = `
    <span class="log-timestamp">${time}</span>
    <span class="log-level ${levelLower}">[${level}]</span>
    <span class="log-message">${escapeHtml(message)}</span>
  `;

  // Apply current filters (text and level)
  if (!shouldShowEntry(level, message)) {
    entry.style.display = "none";
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

  // Update level badges
  updateLevelCounts();
}

/**
 * Check if entry should be visible based on filters
 */
function shouldShowEntry(level: string, message: string): boolean {
  const levelUpper = level.toUpperCase();

  // Level filter
  if (currentLevel !== "ALL" && levelUpper !== currentLevel) {
    return false;
  }

  // Text filter
  if (
    currentFilter &&
    !message.toLowerCase().includes(currentFilter.toLowerCase())
  ) {
    return false;
  }

  return true;
}

/**
 * Update level filter counts in UI
 */
function updateLevelCounts(): void {
  if (!logContent) return;

  const entries = logContent.querySelectorAll(".log-entry");
  const counts = { ALL: 0, INFO: 0, WARNING: 0, ERROR: 0 };

  entries.forEach((entry) => {
    const level = (entry as HTMLElement).dataset.level?.toUpperCase() || "INFO";
    if (counts[level as keyof typeof counts] !== undefined) {
      counts[level as keyof typeof counts]++;
    }
    counts.ALL++;
  });

  // Update badge text if elements exist
  const badges = logContent.parentElement?.querySelectorAll(".level-badge");
  badges?.forEach((badge) => {
    const level = (badge as HTMLElement).dataset.level;
    if (level && level in counts) {
      badge.textContent = String(counts[level as keyof typeof counts]);
    }
  });
}

/**
 * Filtra los logs según el texto de búsqueda (con debounce 200ms)
 * @param filter - Texto a filtrar
 */
export function filterLogs(filter: string): void {
  if (filterDebounceTimeout) {
    clearTimeout(filterDebounceTimeout);
  }

  filterDebounceTimeout = setTimeout(() => {
    currentFilter = filter.toLowerCase();
    applyFilters();
  }, 200);
}

/**
 * Filtra por nivel
 * @param level - Nivel a filtrar (ALL, INFO, WARNING, ERROR)
 */
export function filterByLevel(level: string): void {
  currentLevel = level;
  applyFilters();
}

/**
 * Aplica ambos filtros (texto y nivel)
 */
function applyFilters(): void {
  const entries = logContent?.querySelectorAll(".log-entry");
  entries?.forEach((entry) => {
    const el = entry as HTMLElement;
    const level = (el.dataset.level || "INFO").toUpperCase();
    const message = el.dataset.message || "";

    const showLevel = currentLevel === "ALL" || level === currentLevel;
    const showText = !currentFilter || message.includes(currentFilter);

    el.style.display = showLevel && showText ? "" : "none";
  });

  updateLevelCounts();
}

/**
 * Exporta logs a archivo JSON
 */
export function exportLogsJson(): void {
  const entries = logContent?.querySelectorAll(
    ".log-entry:not([style*='display: none'])",
  );
  if (!entries || entries.length === 0) {
    alert(t("no_logs"));
    return;
  }

  const logs: { timestamp: string; level: string; message: string }[] = [];
  entries.forEach((entry) => {
    const el = entry as HTMLElement;
    const timeSpan = el.querySelector(".log-timestamp")?.textContent || "";
    const levelSpan = el.querySelector(".log-level")?.textContent || "";
    const msgSpan = el.querySelector(".log-message")?.textContent || "";

    logs.push({
      timestamp: timeSpan,
      level: levelSpan.replace("[", "").replace("]", ""),
      message: msgSpan,
    });
  });

  const blob = new Blob([JSON.stringify(logs, null, 2)], {
    type: "application/json",
  });
  const date = new Date().toISOString().split("T")[0];
  downloadBlob(blob, `srt2web-logs-${date}.json`);
}

/**
 * Exporta logs a archivo TXT
 */
export function exportLogsTxt(): void {
  const entries = logContent?.querySelectorAll(
    ".log-entry:not([style*='display: none'])",
  );
  if (!entries || entries.length === 0) {
    alert(t("no_logs"));
    return;
  }

  const lines: string[] = [];
  entries.forEach((entry) => {
    const el = entry as HTMLElement;
    const timeSpan = el.querySelector(".log-timestamp")?.textContent || "";
    const levelSpan = el.querySelector(".log-level")?.textContent || "";
    const msgSpan = el.querySelector(".log-message")?.textContent || "";

    lines.push(`[${timeSpan}] ${levelSpan} ${msgSpan}`);
  });

  const blob = new Blob([lines.join("\n")], { type: "text/plain" });
  const date = new Date().toISOString().split("T")[0];
  downloadBlob(blob, `srt2web-logs-${date}.txt`);
}

/**
 * Helper para descargar blob
 */
function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Limpia todos los logs (con confirmación)
 */
export function clearLogs(): void {
  const entryCount = logContent?.querySelectorAll(".log-entry").length || 0;

  // Confirm before clearing if there are many logs
  if (entryCount > 50) {
    if (!confirm(`${t("confirm_delete")} (${entryCount})`)) {
      return;
    }
  }

  if (!logContent) return;

  logContent.innerHTML = "";

  // Restore empty state
  logEmpty = document.createElement("div");
  logEmpty.className = "log-empty";
  logEmpty.id = "log-empty";
  logEmpty.innerHTML = `
    <span class="log-empty-icon">📝</span>
    <span class="log-empty-text">${t("no_logs_yet")}</span>
  `;
  logContent.appendChild(logEmpty);

  currentFilter = "";
  currentLevel = "ALL";
  if (logSearch) {
    logSearch.value = "";
  }
  if (logLevelFilter) {
    logLevelFilter.value = "ALL";
  }
}

/**
 * Inicializa el panel de logs
 */
export function initLogPanel(): void {
  // Get DOM elements
  logContent = document.getElementById("log-content") as HTMLDivElement;
  logPanel = document.querySelector(".log-panel");
  logEmpty = document.getElementById("log-empty") as HTMLDivElement;
  logSearch = document.getElementById("log-search") as HTMLInputElement;
  collapseIcon = document.getElementById(
    "log-collapse-icon",
  ) as HTMLSpanElement;
  logLevelFilter = document.getElementById(
    "log-level-filter",
  ) as HTMLSelectElement;
  logExportJson = document.getElementById(
    "btn-export-json",
  ) as HTMLButtonElement;
  logExportTxt = document.getElementById("btn-export-txt") as HTMLButtonElement;

  // Setup search filter with debounce
  logSearch?.addEventListener("input", (e) => {
    const value = (e.target as HTMLInputElement).value;
    filterLogs(value);
  });

  // Setup level filter
  logLevelFilter?.addEventListener("change", (e) => {
    const value = (e.target as HTMLSelectElement).value;
    filterByLevel(value);
  });

  // Setup export buttons
  logExportJson?.addEventListener("click", (e) => {
    e.stopPropagation();
    exportLogsJson();
  });

  logExportTxt?.addEventListener("click", (e) => {
    e.stopPropagation();
    exportLogsTxt();
  });

  // Expose global functions for onclick attributes
  (
    window as unknown as {
      toggleLogPanel: typeof toggleLogPanel;
      clearLogs: typeof clearLogs;
      exportLogsJson: typeof exportLogsJson;
      exportLogsTxt: typeof exportLogsTxt;
    }
  ).toggleLogPanel = toggleLogPanel;
  (
    window as unknown as {
      clearLogs: typeof clearLogs;
    }
  ).clearLogs = clearLogs;
  (
    window as unknown as {
      exportLogsJson: typeof exportLogsJson;
    }
  ).exportLogsJson = exportLogsJson;
  (
    window as unknown as {
      exportLogsTxt: typeof exportLogsTxt;
    }
  ).exportLogsTxt = exportLogsTxt;
}

/**
 * Obtiene el estado actual del panel
 */
export function getLogPanelState(): {
  isCollapsed: boolean;
  filter: string;
  logCount: number;
} {
  const logCount = logContent?.querySelectorAll(".log-entry").length || 0;
  return {
    isCollapsed,
    filter: currentFilter,
    logCount,
  };
}
