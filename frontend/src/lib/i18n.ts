/**
 * SRT2Web Internationalization (i18n) System
 * Supports multiple languages for UI labels and messages.
 *
 * Translations are stored in frontend/src/lib/locales/{lang}.json
 */

import { STORAGE_KEYS } from "./constants";
import en from "./locales/en.json";
import es from "./locales/es.json";

export const SUPPORTED_LANGUAGES = ["en", "es"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

type TranslationDict = Record<string, string>;

const translations: Record<Language, TranslationDict> = { en, es };

// Translation type
export type TranslationKey = keyof typeof en;
export type Translations = typeof en;

// Current language state
let currentLanguage: Language = "en";

/**
 * Get the current language
 */
export function getCurrentLanguage(): Language {
  return currentLanguage;
}

/**
 * Set the current language and persist to localStorage
 */
export function setCurrentLanguage(lang: Language): void {
  currentLanguage = lang;
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEYS.LANGUAGE, lang);
  }
}

/**
 * Initialize language from localStorage
 */
export function initLanguage(): Language {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(
      STORAGE_KEYS.LANGUAGE,
    ) as Language | null;
    if (stored && SUPPORTED_LANGUAGES.includes(stored)) {
      currentLanguage = stored;
    }
  }
  return currentLanguage;
}

/**
 * Get a translation by key
 */
export function t(key: TranslationKey): string {
  return translations[currentLanguage][key] || translations.en[key] || key;
}

/**
 * Get translation with fallback
 */
export function tFallback(key: TranslationKey, fallback: string): string {
  return translations[currentLanguage][key] || fallback;
}

/**
 * Create a reactive store for language changes
 */
export function createLanguageStore() {
  const listeners: Set<(lang: Language) => void> = new Set();

  return {
    get current() {
      return currentLanguage;
    },
    set(lang: Language) {
      setCurrentLanguage(lang);
      listeners.forEach((fn) => fn(lang));
    },
    subscribe(fn: (lang: Language) => void) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}

// Export for framework integration
export const languageStore = createLanguageStore();

// Vue/React-like useLanguage hook pattern (for vanilla JS)
export function useLanguage() {
  return {
    current: currentLanguage,
    t,
    set: (lang: Language) => languageStore.set(lang),
  };
}

// Shorthand for templates: _('key') instead of t('key')
export const _ = t;
