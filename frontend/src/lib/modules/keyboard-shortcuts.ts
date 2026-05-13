/**
 * Keyboard Shortcuts Module for SRT2Web
 *
 * Implements global keyboard shortcuts:
 * - Ctrl+S: Save configuration
 * - Space: Start/Stop pipeline (when no input focus)
 * - Ctrl+D: Toggle dark mode
 */

import { handleSaveConfig } from "../dashboard";
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

// ── Shortcut Definitions ───────────────────────────────────────────────

const shortcuts: ShortcutDefinition[] = [
  {
    key: "s",
    ctrlKey: true,
    handler: (e) => {
      e.preventDefault();
      handleSaveConfig();
      showToast(t("config_saved_shortcut"), "info");
    },
    description: "Guardar configuración",
    preventDefault: true,
  },

  {
    key: "d",
    ctrlKey: true,
    handler: (e) => {
      e.preventDefault();

      // Toggle dark mode
      const htmlElement = document.documentElement;
      const isDark = htmlElement.classList.contains("dark");

      if (isDark) {
        htmlElement.classList.remove("dark");
        localStorage.setItem("srt2web_theme", "light");
        showToast(t("light_mode_on"), "info");
      } else {
        htmlElement.classList.add("dark");
        localStorage.setItem("srt2web_theme", "dark");
        showToast(t("dark_mode_on"), "info");
      }
    },
    description: "Alternar modo oscuro",
    preventDefault: true,
  },
];

// ── Event Handler ──────────────────────────────────────────────────────────

function handleKeyDown(event: KeyboardEvent): void {
  // Check if any shortcut matches
  for (const shortcut of shortcuts) {
    if (
      event.key.toLowerCase() === shortcut.key.toLowerCase() &&
      (shortcut.ctrlKey === undefined || event.ctrlKey === shortcut.ctrlKey) &&
      (shortcut.shiftKey === undefined ||
        event.shiftKey === shortcut.shiftKey) &&
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

// ── Public API ───────────────────────────────────────────────────────────

/**
 * Initialize keyboard shortcuts
 * Call this function once when the app starts
 */
export function initKeyboardShortcuts(): void {
  if (initialized) return;

  document.addEventListener("keydown", handleKeyDown);
  initialized = true;
}

/**
 * Get list of available shortcuts (for help display)
 */
export function getShortcutsHelp(): Array<{
  key: string;
  description: string;
}> {
  return shortcuts.map((s) => ({
    key: `${s.ctrlKey ? "Ctrl+" : ""}${s.shiftKey ? "Shift+" : ""}${
      s.altKey ? "Alt+" : ""
    }${s.key.toUpperCase()}`,
    description: s.description,
  }));
}

/**
 * Cleanup function (for testing or hot module replacement)
 */
export function destroyKeyboardShortcuts(): void {
  if (!initialized) return;

  document.removeEventListener("keydown", handleKeyDown);
  initialized = false;
}

export default {
  initKeyboardShortcuts,
  getShortcutsHelp,
  destroyKeyboardShortcuts,
};
