/**
 * Logger utility — Centralized logging with environment-aware output.
 *
 * In production (import.meta.env.PROD): only warnings and errors are visible on console.
 * In development: all levels are shown.
 *
 * Error-level messages also trigger a toast notification.
 */

import { showToast } from "../modules/toast";

const LOG_LEVELS: Record<string, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const currentLevel: "debug" | "info" | "warn" | "error" = import.meta.env.PROD
  ? "warn"
  : "debug";

function shouldLog(level: string): boolean {
  return LOG_LEVELS[level] >= LOG_LEVELS[currentLevel];
}

function fmt(level: string, module: string, message: string): string {
  return `[${level.toUpperCase()}] [${module}] ${message}`;
}

export const logger = {
  debug(module: string, message: string, ...args: unknown[]): void {
    if (!shouldLog("debug")) return;
    console.debug(fmt("debug", module, message), ...args);
  },

  info(module: string, message: string, ...args: unknown[]): void {
    if (!shouldLog("info")) return;
    console.info(fmt("info", module, message), ...args);
  },

  warn(module: string, message: string, ...args: unknown[]): void {
    if (!shouldLog("warn")) return;
    console.warn(fmt("warn", module, message), ...args);
  },

  error(module: string, message: string, ...args: unknown[]): void {
    if (!shouldLog("error")) return;
    console.error(fmt("error", module, message), ...args);
    try {
      showToast(message, "error", 5000);
    } catch {
      // toast unavailable
    }
  },
};
