/**
 * Keyboard Shortcuts Module for SRT2Web
 * 
 * Implements global keyboard shortcuts:
 * - Ctrl+S: Save configuration
 * - Space: Start/Stop pipeline (when no input focus)
 * - Ctrl+D: Toggle dark mode
 */

import { handleSaveConfig, handleStart, handleStop } from '../dashboard';
import { showToast } from '../utils';
import { MESSAGES } from '../constants';

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
    key: 's',
    ctrlKey: true,
    handler: (e) => {
      e.preventDefault();
      handleSaveConfig();
      showToast('Configuración guardada (Ctrl+S)', 'info');
    },
    description: 'Guardar configuración',
    preventDefault: true,
  },
  {
    key: ' ',
    handler: (e) => {
      // Only trigger if no input/textarea is focused
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
        return;
      }
      
      e.preventDefault();
      
      // Check current pipeline state and toggle
      import('../store/index').then(({ pipelineStatus }) => {
        if (pipelineStatus.value?.state === 'running') {
          handleStop();
        } else {
          handleStart();
        }
      });
    },
    description: 'Iniciar/Detener pipeline',
    preventDefault: true,
  },
  {
    key: 'd',
    ctrlKey: true,
    handler: (e) => {
      e.preventDefault();
      
      // Toggle dark mode
      const htmlElement = document.documentElement;
      const isDark = htmlElement.classList.contains('dark');
      
      if (isDark) {
        htmlElement.classList.remove('dark');
        localStorage.setItem('srt2web_theme', 'light');
        showToast('Modo claro activado', 'info');
      } else {
        htmlElement.classList.add('dark');
        localStorage.setItem('srt2web_theme', 'dark');
        showToast('Modo oscuro activado', 'info');
      }
    },
    description: 'Alternar modo oscuro',
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

// ── Public API ───────────────────────────────────────────────────────────

/**
 * Initialize keyboard shortcuts
 * Call this function once when the app starts
 */
export function initKeyboardShortcuts(): void {
  if (initialized) {
    console.warn('Keyboard shortcuts already initialized');
    return;
  }

  document.addEventListener('keydown', handleKeyDown);
  initialized = true;
  
  console.log('Keyboard shortcuts initialized:', shortcuts.map(s => ({
    key: `${s.ctrlKey ? 'Ctrl+' : ''}${s.shiftKey ? 'Shift+' : ''}${s.altKey ? 'Alt+' : ''}${s.key.toUpperCase()}`,
    description: s.description,
  })));
}

/**
 * Get list of available shortcuts (for help display)
 */
export function getShortcutsHelp(): Array<{ key: string; description: string }> {
  return shortcuts.map(s => ({
    key: `${s.ctrlKey ? 'Ctrl+' : ''}${s.shiftKey ? 'Shift+' : ''}${s.altKey ? 'Alt+' : ''}${s.key.toUpperCase()}`,
    description: s.description,
  }));
}

/**
 * Cleanup function (for testing or hot module replacement)
 */
export function destroyKeyboardShortcuts(): void {
  if (!initialized) return;
  
  document.removeEventListener('keydown', handleKeyDown);
  initialized = false;
  console.log('Keyboard shortcuts destroyed');
}

export default {
  initKeyboardShortcuts,
  getShortcutsHelp,
  destroyKeyboardShortcuts,
};
