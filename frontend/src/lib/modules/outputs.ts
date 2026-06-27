/**
 * Outputs - Manages output status with reactive signals.
 *
 * F162: Converted from mutable arrays to @preact/signals-core for
 * consistency with the rest of the codebase.
 */

import { signal } from "@preact/signals-core";
import { apiCall, type OutputStatus } from "../api";
import { showToast } from "./toast";
import { logger } from "../utils/logger";

/** Reactive list of output statuses */
export const outputsSignal = signal<OutputStatus[]>([]);

export async function fetchOutputs(): Promise<OutputStatus[]> {
  try {
    const response = await apiCall<{ outputs: OutputStatus[] }>(
      "GET",
      "api/outputs",
    );
    outputsSignal.value = response.outputs || [];
    return outputsSignal.value;
  } catch (e) {
    logger.error("outputs", "Failed to fetch outputs", e);
    return [];
  }
}

export async function fetchAvailableTypes(): Promise<string[]> {
  try {
    const response = await apiCall<{ available_types: string[] }>(
      "GET",
      "api/outputs/available",
    );
    return response.available_types || [];
  } catch (e) {
    logger.warn("outputs", "Failed to fetch available output types", e);
    return ["web", "recording", "srt", "rtmp"];
  }
}

export async function addOutput(config: {
  type: string;
  name?: string;
  config?: Record<string, unknown>;
}): Promise<boolean> {
  try {
    await apiCall("POST", "api/outputs", config);
    showToast("Salida añadida correctamente", "success");
    await fetchOutputs();
    return true;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    showToast(`Error al añadir salida: ${msg}`, "error");
    return false;
  }
}

export async function removeOutput(name: string): Promise<boolean> {
  try {
    await apiCall("DELETE", `api/outputs/${encodeURIComponent(name)}`);
    showToast("Salida eliminada", "success");
    await fetchOutputs();
    return true;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    showToast(`Error al eliminar: ${msg}`, "error");
    return false;
  }
}

export async function toggleOutput(
  name: string,
  enabled: boolean,
): Promise<boolean> {
  try {
    await apiCall("POST", `api/outputs/${encodeURIComponent(name)}/toggle`, {
      enabled,
    });
    await fetchOutputs();
    return true;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    showToast(`Error: ${msg}`, "error");
    return false;
  }
}

export async function updateOutput(
  name: string,
  config: Record<string, unknown>,
): Promise<boolean> {
  try {
    await apiCall("PUT", `api/outputs/${encodeURIComponent(name)}`, { config });
    showToast("Salida actualizada", "success");
    await fetchOutputs();
    return true;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    showToast(`Error: ${msg}`, "error");
    return false;
  }
}

export function getOutputs(): OutputStatus[] {
  return outputsSignal.value;
}

/** @deprecated Use outputsSignal directly for reactive updates */
export function onOutputsChange(
  listener: (outputs: OutputStatus[]) => void,
): () => void {
  // F162: Legacy adapter — subscribe to signal changes
  let prev = outputsSignal.value;
  const check = () => {
    const curr = outputsSignal.value;
    if (curr !== prev) {
      prev = curr;
      listener(curr);
    }
  };
  // Poll for changes (signal subscriptions require effect() context)
  const interval = setInterval(check, 500);
  return () => clearInterval(interval);
}

export function getOutputIcon(type: string): string {
  const icons: Record<string, string> = {
    web: "\u{1F310}",
    recording: "\u23FA",
    srt: "\u{1F4E1}",
    rtmp: "\u{1F4FA}",
    file: "\u{1F4C1}",
    hls: "\u{1F310}",
  };
  return icons[type] || "\u{1F4E4}";
}

export function getOutputTypeName(type: string): string {
  const names: Record<string, string> = {
    web: "HLS",
    recording: "REC",
    srt: "SRT",
    rtmp: "RTMP",
    file: "FILE",
    hls: "HLS",
  };
  return names[type] || type.toUpperCase();
}

export function formatOutputState(output: OutputStatus): string {
  if (output.error) return "Error";
  if (!output.enabled) return "Deshabilitado";
  return output.state === "running" ? "Activo" : "Inactivo";
}
