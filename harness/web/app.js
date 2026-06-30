// Harness Web UI - Main application
import { fetchJSON, apiCall } from "./api.js";
import { loadFeatures } from "./features.js";
import { loadProgress, doImportProgress } from "./progress.js";

let currentTab = "features";

window.switchTab = function switchTab(tab) {
  currentTab = tab;
  document.getElementById("tab-features").className =
    tab === "features" ? "tab active" : "tab";
  document.getElementById("tab-progress").className =
    tab === "progress" ? "tab active" : "tab";
  document.getElementById("featuresView").style.display =
    tab === "features" ? "flex" : "none";
  document.getElementById("progressView").style.display =
    tab === "progress" ? "flex" : "none";
  if (tab === "progress") loadProgress();
};

export async function loadStats() {
  const d = await fetchJSON("/api/stats");
  const el = document.getElementById("headerStats");
  const c = d.counts;
  el.innerHTML = `
    <span class="stat"><span class="dot dot-done"></span>${
      c.done || 0
    } done</span>
    <span class="stat"><span class="dot dot-progress"></span>${
      c.in_progress || 0
    } active</span>
    <span class="stat"><span class="dot dot-pending"></span>${
      c.pending || 0
    } pending</span>
    <span class="stat"><span class="dot dot-blocked"></span>${
      c.blocked || 0
    } blocked</span>
  `;

  // Populate area filter
  const areaSelect = document.getElementById("filterArea");
  const currentArea = areaSelect.value;
  const areas = Object.keys(d.by_area || {}).sort();
  areaSelect.innerHTML =
    '<option value="">All areas</option>' +
    areas
      .map(
        (a) =>
          `<option value="${a}" ${a === currentArea ? "selected" : ""}>${a} (${
            d.by_area[a]
          })</option>`,
      )
      .join("");
}

export function switchTab(tab) {
  window.switchTab = switchTab;
  currentTab = tab;
  document.getElementById("tab-features").className =
    tab === "features" ? "tab active" : "tab";
  document.getElementById("tab-progress").className =
    tab === "progress" ? "tab active" : "tab";
  document.getElementById("featuresView").style.display =
    tab === "features" ? "flex" : "none";
  document.getElementById("progressView").style.display =
    tab === "progress" ? "flex" : "none";
  if (tab === "progress") loadProgress();
}

// Export/Import functions
window.doExport = async function doExport() {
  const d = await fetchJSON("/api/export", { method: "POST" });
  alert(`Exported ${d.exported} features to ${d.path}`);
};

window.doMigrate = async function doMigrate() {
  if (
    !confirm("Re-migrate feature_list.json? This will overwrite existing data.")
  )
    return;
  const d = await fetchJSON("/api/migrate", { method: "POST" });
  alert(`Migrated: ${d.imported} features`);
  await loadStats();
  await loadFeatures();
};

// Boot
document.addEventListener("DOMContentLoaded", () => {
  document
    .getElementById("filterStatus")
    .addEventListener("change", loadFeatures);
  document
    .getElementById("filterArea")
    .addEventListener("change", loadFeatures);
  document.getElementById("searchBox").addEventListener("input", loadFeatures);

  loadStats().then(loadFeatures);
});
