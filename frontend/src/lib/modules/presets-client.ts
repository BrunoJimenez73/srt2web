/**
 * Presets Client - Handles preset operations (load, apply, save).
 */

import { showToast } from "./toast";
import { t } from "../i18n";
import { pipelineConfig, presets, selectedPreset } from "../store/index";
import { addLog } from "../store/index";
import { applyConfigToUI } from "./config-collector";
import { fetchWithAuth } from "../api";

function setLoading(loading: boolean, action: string = ""): void {
  document.body.classList.toggle("loading", loading);
  if (loading && action) {
    addLog("INFO", `${action}...`);
  }
}

export async function loadPresets(): Promise<void> {
  try {
    const response = await fetchWithAuth("/api/presets");
    if (!response.ok) return;
    const data = await response.json();
    presets.value = data.presets || [];
  } catch (e) {
    addLog("ERROR", `${t("presets_load_error")}: ${(e as Error).message}`);
  }
}

export async function applyPreset(name: string): Promise<void> {
  try {
    setLoading(true, `${t("preset_applying")}: ${name}`);
    const response = await fetchWithAuth(
      `/api/presets/${encodeURIComponent(name)}/apply`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      },
    );
    if (!response.ok) {
      const err = await response.text();
      throw new Error(err || `Failed to apply preset: ${name}`);
    }
    const data = await response.json();
    pipelineConfig.value = data.config;
    applyConfigToUI(data.config);
    selectedPreset.value = name;
    showToast(`${t("preset_applied")}: ${name}`, "success");
    addLog("INFO", `${t("preset_applied")}: ${name}`);
  } catch (e) {
    showToast(`${t("preset_error")}: ${(e as Error).message}`, "error");
    addLog("ERROR", `${t("preset_error")}: ${(e as Error).message}`);
  } finally {
    setLoading(false);
  }
}

export async function savePreset(name: string): Promise<void> {
  try {
    setLoading(true, `${t("preset_saving")}: ${name}`);
    const response = await fetchWithAuth("/api/presets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description: "" }),
    });
    if (!response.ok) {
      const err = await response.text();
      throw new Error(err || `Failed to save preset: ${name}`);
    }
    await loadPresets();
    showToast(`${t("preset_saved")}: ${name}`, "success");
    addLog("INFO", `${t("preset_saved")}: ${name}`);
  } catch (e) {
    showToast(`${t("preset_save_error")}: ${(e as Error).message}`, "error");
    addLog("ERROR", `${t("preset_save_error")}: ${(e as Error).message}`);
  } finally {
    setLoading(false);
  }
}
