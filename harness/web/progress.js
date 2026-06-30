// Progress tab module
import { fetchJSON, esc, showError } from "./api.js";

let allProgress = [];
let currentProgressId = null;

export async function loadProgress() {
  const d = await fetchJSON("/api/progress");
  allProgress = d.entries || [];
  renderProgressList();
}

function renderProgressList() {
  const ul = document.getElementById("progressList");
  ul.innerHTML = allProgress
    .map(
      (p) => `
    <li class="progress-item ${
      p.id == currentProgressId ? "active" : ""
    }" onclick="window.selectProgress(${p.id})">
      <span class="pdate">${p.date}</span>
      ${p.is_current ? '<span class="current-badge">CURRENT</span>' : ""}
      <div class="ptitle">${esc(p.title)}</div>
      <div class="pmeta">
        <span>${p.features_worked.length} features</span>
        <span>${p.files_changed.length} files</span>
      </div>
    </li>
  `,
    )
    .join("");
}

window.selectProgress = async function selectProgress(id) {
  currentProgressId = id;
  renderProgressList();
  const entry = allProgress.find((p) => p.id === id);
  if (!entry) return;

  const panel = document.getElementById("progressPanel");
  panel.innerHTML = `
    <div class="progress-detail">
      <h2>${entry.date} — ${esc(entry.title)}</h2>
      <div class="meta-grid">
        <div class="meta-box">
          <h4>Features Worked (${entry.features_worked.length})</h4>
          <div>${
            entry.features_worked
              .map((f) => `<span class="tag">F${f}</span>`)
              .join(" ") || '<span style="color:var(--text-dim)">none</span>'
          }</div>
        </div>
        <div class="meta-box">
          <h4>Files Changed (${entry.files_changed.length})</h4>
          <div style="font-size:11px;color:var(--text-dim);max-height:100px;overflow-y:auto">${
            entry.files_changed.map((f) => esc(f)).join("<br>") || "none"
          }</div>
        </div>
      </div>
      ${
        Object.keys(entry.verification).length
          ? `
      <div class="meta-box" style="margin-bottom:16px">
        <h4>Verification</h4>
        ${Object.entries(entry.verification)
          .map(
            ([k, v]) => `
          <div class="verify-item">${
            v === "PASS" ? "&#10003;" : "&#10007;"
          } ${esc(k)}: ${esc(v)}</div>
        `,
          )
          .join("")}
      </div>
      `
          : ""
      }
      <div class="content-md">${esc(entry.content_md || "(no content)")}</div>
    </div>
  `;
};

export async function doImportProgress() {
  if (!confirm("Re-import progress from markdown files?")) return;
  const d = await fetchJSON("/api/progress/import", { method: "POST" });
  alert(`Imported: ${d.imported} progress entries`);
  await loadProgress();
}
