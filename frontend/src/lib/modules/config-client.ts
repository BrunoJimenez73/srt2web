/**
 * Config Client - Handles configuration save, load, and chunk sync.
 */

import { apiCall, getConfig, updateChunkDuration } from "../api";
import { showToast } from "../utils";
import { DEFAULTS } from "../constants";
import { t } from "../i18n";
import { pipelineConfig } from "../store/index";
import { addLog } from "../store/index";
import { collectConfigFromUI, applyConfigToUI } from "./config-collector";

let _isLoading = false;

function setLoading(loading: boolean, action: string = ""): void {
  _isLoading = loading;
  document.body.classList.toggle("loading", loading);
  if (loading && action) {
    addLog("INFO", `${action}...`);
  }
}

function isLoading(): boolean {
  return _isLoading;
}

export async function handleSaveConfig(): Promise<void> {
  if (isLoading()) return;
  setLoading(true, t("saving_config"));
  try {
    const newConfig = collectConfigFromUI();

    const chunkDuration = parseInt(
      (document.getElementById("input-chunk-duration") as HTMLInputElement)
        ?.value ||
        (document.getElementById("input-rtmp-chunk") as HTMLInputElement)
          ?.value ||
        (document.getElementById("input-file-chunk") as HTMLInputElement)
          ?.value ||
        String(DEFAULTS.CHUNK_DURATION),
    );

    await apiCall("PUT", "/api/config", { config: newConfig });

    try {
      await updateChunkDuration(chunkDuration);
      addLog("INFO", `${t("chunk_synced")}: ${chunkDuration}s`);
    } catch (chunkError) {
      addLog("WARNING", `Chunk sync failed: ${(chunkError as Error).message}`);
    }

    const cfg = await getConfig();
    pipelineConfig.value = cfg;
    applyConfigToUI(cfg);
    showToast(t("config_saved"), "success");
    addLog("INFO", t("config_saved"));
  } catch (e) {
    const msg = (e as Error).message;
    showToast(`${t("config_save_error")}: ${msg}`, "error");
    addLog("ERROR", `${t("config_save_error")}: ${msg}`);
  } finally {
    setLoading(false);
  }
}

export async function exportConfig(): Promise<void> {
  try {
    const cfg = pipelineConfig.value;
    if (!cfg) {
      showToast(t("config_export_error"), "error");
      return;
    }
    const yamlStr = dumpConfig(cfg);
    const blob = new Blob([yamlStr], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `srt2web-config-${new Date().toISOString().slice(0, 10)}.yaml`;
    a.click();
    URL.revokeObjectURL(url);
    showToast(t("config_exported"), "success");
  } catch (e) {
    showToast(`${t("error")}: ${(e as Error).message}`, "error");
  }
}

function dumpConfig(obj: unknown, indent = 0): string {
  const pad = "  ".repeat(indent);
  if (obj === null || obj === undefined) return "null";
  if (typeof obj === "string") return `"${obj}"`;
  if (typeof obj === "number" || typeof obj === "boolean") return String(obj);
  if (Array.isArray(obj)) {
    if (obj.length === 0) return "[]";
    return obj.map((v) => `${pad}- ${dumpConfig(v, indent + 1)}`).join("\n");
  }
  if (typeof obj === "object") {
    const entries = Object.entries(obj);
    if (entries.length === 0) return "{}";
    return entries
      .map(([k, v]) => `${pad}${k}:\n${dumpConfig(v, indent + 1)}`)
      .join("\n");
  }
  return String(obj);
}
