/**
 * Keyboard Shortcuts Module for SRT2Web
 *
 * Implements global keyboard shortcuts:
 * - Ctrl+S: Save configuration
 * - Ctrl+Enter: Start/Stop pipeline
 * - Ctrl+D: Toggle dark mode
 * - ? or Ctrl+/: Show shortcuts help
 * - Escape: Close modals
 */

import { handleSaveConfig, handleStart, handleStop } from "../dashboard";
import { showToast } from "../utils";
import { t } from "../i18n";

// ── Types ────────────────────────────────────────────────────────────────

interface ShortcutDefinition {
  key: string;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  handler: (event: KeyboardEvent) => void;
  description: string;
  preventDefault?: boolean;
}

// ── State ────────────────────────────────────────────────────────────────

let initialized = false;

const INPUT_SELECTOR = "input:not([type=checkbox]):not([type=radio]), textarea, select, [contenteditable]";

function isInputFocused(): boolean {
  return document.activeElement ? document.activeElement.matches(INPUT_SELECTOR) : false;
}

// ── Shortcut Definitions ───────────────────────────────────────────────

const shortcuts: ShortcutDefinition[] = [
  {
    key: "s",
    ctrlKey: true,
    handler: (_e) => {
      handleSaveConfig();
      showToast(t("config_saved_shortcut"), "info");
    },
    description: "Guardar configuración",
    preventDefault: true,
  },

  {
    key: "Enter",
    ctrlKey: true,
    handler: async (_e) => {
      const statusEl = document.getElementById("status-dot");
      const isRunning = statusEl?.classList.contains("running") ?? false;
      if (isRunning) {
        await handleStop();
      } else {
        await handleStart();
      }
    },
    description: "Iniciar/Detener pipeline",
    preventDefault: true,
  },

  {
    key: "/",
    ctrlKey: true,
    handler: () => {
      toggleShortcutsHelp();
    },
    description: "Mostrar ayuda de atajos",
    preventDefault: true,
  },

  {
    key: "?",
    ctrlKey: false,
    handler: () => {
      if (!isInputFocused()) toggleShortcutsHelp();
    },
    description: "Mostrar ayuda de atajos",
    preventDefault: false,
  },

  {
    key: "d",
    ctrlKey: true,
    handler: (_e) => {
      const htmlElement = document.documentElement;
      const isDark = htmlElement.classList.contains("dark");
      const themeIcon = document.getElementById("theme-icon") as HTMLSpanElement | null;

      if (isDark) {
        htmlElement.classList.remove("dark");
        localStorage.setItem("srt2web_theme", "light");
        if (themeIcon) themeIcon.textContent = "☀️";
        showToast(t("light_mode_on"), "info");
      } else {
        htmlElement.classList.add("dark");
        localStorage.setItem("srt2web_theme", "dark");
        if (themeIcon) themeIcon.textContent = "🌙";
        showToast(t("dark_mode_on"), "info");
      }
    },
    description: "Alternar modo oscuro",
    preventDefault: true,
  },

  {
    key: "l",
    ctrlKey: true,
    handler: () => {
      const panel = document.querySelector(".log-panel");
      if (panel) {
        panel.classList.toggle("collapsed");
        const header = document.getElementById("log-header");
        if (header) header.setAttribute("aria-expanded", String(!panel.classList.contains("collapsed")));
      }
    },
    description: "Alternar panel de logs",
    preventDefault: true,
  },

  {
    key: "Escape",
    ctrlKey: false,
    handler: () => {
      // Close shortcuts help modal
      const modal = document.getElementById("shortcuts-modal");
      if (modal) modal.style.display = "none";
      // Close security panel
      const secPanel = document.getElementById("secure-panel");
      if (secPanel?.classList.contains("open")) {
        secPanel.classList.remove("open");
        const arrow = document.getElementById("secure-arrow");
        if (arrow) arrow.classList.remove("open");
      }
    },
    description: "Cerrar modal / panel",
    preventDefault: false,
  },
];

// ── Event Handler ──────────────────────────────────────────────────────────

function handleKeyDown(event: KeyboardEvent): void {
  // Ignore shortcuts when typing in input fields (except Escape and F-keys)
  if (isInputFocused() && event.key !== "Escape" && !event.key.startsWith("F")) return;

  for (const shortcut of shortcuts) {
    if (
      event.key.toLowerCase() === shortcut.key.toLowerCase() &&
      (shortcut.ctrlKey === undefined || event.ctrlKey === shortcut.ctrlKey) &&
      (shortcut.shiftKey === undefined || event.shiftKey === shortcut.shiftKey) &&
      (shortcut.altKey === undefined || event.altKey === shortcut.altKey)
    ) {
      if (shortcut.preventDefault !== false) {
        event.preventDefault();
      }
      shortcut.handler(event);
      return;
    }
  }
}

// ── Shortcuts Help Modal ─────────────────────────────────────────────────

function toggleShortcutsHelp(): void {
  const existing = document.getElementById("shortcuts-modal");
  if (existing) {
    existing.remove();
    return;
  }

  const modal = document.createElement("div");
  modal.id = "shortcuts-modal";
  modal.className = "shortcuts-modal";
  modal.setAttribute("role", "dialog");
  modal.setAttribute("aria-label", t("keyboard_shortcuts"));

  const shortcutsList = shortcuts
    .filter((s) => s.key !== "Escape")
    .map((s) => {
      const keys = `${s.ctrlKey ? "Ctrl+" : ""}${s.shiftKey ? "Shift+" : ""}${s.altKey ? "Alt+" : ""}${s.key === "/" ? "/" : s.key.toUpperCase()}`;
      return `<div class="shortcut-row"><kbd>${keys}</kbd><span>${s.description}</span></div>`;
    })
    .join("");

  modal.innerHTML = `
    <div class="shortcuts-modal-backdrop"></div>
    <div class="shortcuts-modal-content">
      <div class="shortcuts-header">
        <span>⌨️ ${t("keyboard_shortcuts")}</span>
        <button class="shortcuts-close" id="shortcuts-close" aria-label="${t("close")}">✕</button>
      </div>
      <div class="shortcuts-body">${shortcutsList}</div>
    </div>
  `;

  document.body.appendChild(modal);

  document.getElementById("shortcuts-close")?.addEventListener("click", () => modal.remove());
  modal.querySelector(".shortcuts-modal-backdrop")?.addEventListener("click", () => modal.remove());
}

// ── Public API ───────────────────────────────────────────────────────────

export function initKeyboardShortcuts(): void {
  if (initialized) return;

  document.addEventListener("keydown", handleKeyDown);
  initialized = true;
}

export function getShortcutsHelp(): Array<{ key: string; description: string }> {
  return shortcuts.map((s) => ({
    key: `${s.ctrlKey ? "Ctrl+" : ""}${s.shiftKey ? "Shift+" : ""}${s.altKey ? "Alt+" : ""}${s.key.toUpperCase()}`,
    description: s.description,
  }));
}

export function destroyKeyboardShortcuts(): void {
  if (!initialized) return;
  document.removeEventListener("keydown", handleKeyDown);
  initialized = false;
}

// Add CSS for shortcuts modal
const styleId = "shortcuts-modal-styles";
if (!document.getElementById(styleId)) {
  const style = document.createElement("style");
  style.id = styleId;
  style.textContent = `
    .shortcuts-modal {
      position: fixed;
      inset: 0;
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .shortcuts-modal-backdrop {
      position: absolute;
      inset: 0;
      background: rgba(0,0,0,0.6);
    }
    .shortcuts-modal-content {
      position: relative;
      background: var(--bg-card);
      border: 1px solid var(--border-dim);
      border-radius: var(--radius-md);
      padding: 20px;
      min-width: 320px;
      max-width: 460px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }
    .shortcuts-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      font-size: 14px;
      font-weight: 600;
      color: var(--text-prime);
    }
    .shortcuts-close {
      background: none;
      border: none;
      color: var(--text-dim);
      cursor: pointer;
      font-size: 16px;
      padding: 4px;
    }
    .shortcuts-close:hover { color: var(--text-prime); }
    .shortcuts-body {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .shortcut-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-size: 12px;
      color: var(--text-sec);
    }
    .shortcut-row kbd {
      font-family: var(--font-mono);
      background: var(--bg-surface);
      border: 1px solid var(--border-dim);
      border-radius: 4px;
      padding: 3px 8px;
      font-size: 11px;
      color: var(--text-prime);
      white-space: nowrap;
    }
  `;
  document.head.appendChild(style);
}

export default {
  initKeyboardShortcuts,
  getShortcutsHelp,
  destroyKeyboardShortcuts,
};
