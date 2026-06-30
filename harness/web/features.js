// Features tab module
import { fetchJSON, apiCall, esc, showError } from "./api.js";

let allFeatures = [];
let currentId = null;

export async function loadFeatures() {
  const status = document.getElementById("filterStatus").value;
  const area = document.getElementById("filterArea").value;
  const q = document.getElementById("searchBox").value.toLowerCase();
  let url = "/api/features?";
  if (status) url += `status=${status}&`;
  if (area) url += `area=${area}&`;
  const d = await fetchJSON(url);
  allFeatures = d.features;
  if (q) {
    allFeatures = allFeatures.filter(
      (f) =>
        f.name.toLowerCase().includes(q) ||
        f.title.toLowerCase().includes(q) ||
        (f.description || "").toLowerCase().includes(q),
    );
  }
  renderList();
}

function renderList() {
  const ul = document.getElementById("featureList");
  ul.innerHTML = allFeatures
    .map(
      (f) => `
    <li class="feature-item ${
      f.id == currentId ? "active" : ""
    }" onclick="window.selectFeature('${f.id}')">
      <span class="fid">F${f.id}</span>
      <span class="ftitle">${esc(f.title)}</span>
      <div class="fmeta">
        <span class="status-badge status-${f.status}">${f.status}</span>
        <span>${f.area || "-"}</span>
        <span>${f.priority || "-"}</span>
      </div>
    </li>
  `,
    )
    .join("");
}

window.selectFeature = async function selectFeature(id) {
  currentId = id;
  renderList();
  const d = await fetchJSON(`/api/features/${id}`);
  const f = d.feature;
  const audit = await fetchJSON(`/api/features/${id}/audit`);
  const panel = document.getElementById("mainPanel");

  const risk = f.risk_assessment;
  panel.innerHTML = `
    <div class="detail-view">
      <h2><span class="status-badge status-${f.status}">${f.status}</span> F${
        f.id
      }: ${esc(f.title)}</h2>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
        <div class="field-group">
          <label>Name</label>
          <input id="d-name" value="${esc(f.name)}">
        </div>
        <div class="field-group">
          <label>Title</label>
          <input id="d-title" value="${esc(f.title)}">
        </div>
        <div class="field-group">
          <label>Status</label>
          <select id="d-status">
            ${["pending", "in_progress", "done", "blocked"]
              .map(
                (s) =>
                  `<option value="${s}" ${
                    f.status === s ? "selected" : ""
                  }>${s}</option>`,
              )
              .join("")}
          </select>
        </div>
        <div class="field-group">
          <label>Area</label>
          <input id="d-area" value="${esc(f.area)}">
        </div>
        <div class="field-group">
          <label>Priority</label>
          <select id="d-priority">
            ${["Alta", "Media", "Baja"]
              .map(
                (p) =>
                  `<option value="${p}" ${
                    f.priority === p ? "selected" : ""
                  }>${p}</option>`,
              )
              .join("")}
          </select>
        </div>
        <div class="field-group">
          <label>Phase</label>
          <input id="d-phase" value="${esc(f.phase || "")}">
        </div>
        <div class="field-group">
          <label>Completed Date</label>
          <input id="d-completed_date" value="${esc(f.completed_date || "")}">
        </div>
        <div class="field-group">
          <label>Started In Session</label>
          <input id="d-started_in_session" value="${esc(
            f.started_in_session || "",
          )}">
        </div>
      </div>

      <div class="field-group">
        <label>Description</label>
        <textarea id="d-description">${esc(f.description || "")}</textarea>
      </div>

      <div class="field-group">
        <label>Problems Identified (one per line)</label>
        <textarea id="d-problems_identified">${(
          f.problems_identified || []
        ).join("\n")}</textarea>
      </div>

      <div class="field-group">
        <label>Acceptance Criteria (one per line)</label>
        <textarea id="d-acceptance">${(f.acceptance || []).join(
          "\n",
        )}</textarea>
      </div>

      <div class="field-group">
        <label>Files To Touch (one per line)</label>
        <textarea id="d-files_to_touch">${(f.files_to_touch || []).join(
          "\n",
        )}</textarea>
      </div>

      <div class="field-group">
        <label>Fix / What Was Done (one per line)</label>
        <textarea id="d-fix">${(f.fix || []).join("\n")}</textarea>
      </div>

      <div class="field-group">
        <label>Completion Notes</label>
        <textarea id="d-completion_notes">${esc(
          f.completion_notes || "",
        )}</textarea>
      </div>

      <div class="field-group">
        <label>Dependencies (comma-separated IDs)</label>
        <input id="d-dependencies" value="${(f.dependencies || []).join(", ")}">
      </div>

      ${
        risk
          ? `
      <div class="field-group">
        <label>Risk Level</label>
        <input id="d-risk_level" value="${esc(risk.risk_level)}">
      </div>
      <div class="field-group">
        <label>Mitigation (one per line)</label>
        <textarea id="d-mitigation">${(risk.mitigation || []).join(
          "\n",
        )}</textarea>
      </div>
      `
          : ""
      }

      <div class="btn-row">
        <button class="btn primary" onclick="saveFeature()">Save</button>
        <button class="btn danger" onclick="deleteFeature()">Delete</button>
      </div>

      ${
        audit.entries.length
          ? `
      <div class="audit-list">
        <h3>Audit Trail (${audit.entries.length})</h3>
        ${audit.entries
          .slice(0, 20)
          .map(
            (e) => `
          <div class="audit-entry">
            <span class="ts">${e.timestamp}</span>
            <span class="field">${e.field_name}</span>:
            <span class="val">${esc(e.old_value || "(empty)")}</span> ->
            <span class="val">${esc(e.new_value || "(empty)")}</span>
            <span style="color:var(--purple)">${e.agent}</span>
          </div>
        `,
          )
          .join("")}
      </div>
      `
          : ""
      }
    </div>
  `;
};

window.saveFeature = async function saveFeature() {
  if (!currentId) return;
  try {
    const data = {};
    [
      "name",
      "title",
      "status",
      "area",
      "priority",
      "phase",
      "description",
      "completed_date",
      "started_in_session",
      "completion_notes",
    ].forEach((k) => {
      data[k] = document.getElementById("d-" + k)?.value || "";
    });
    ["problems_identified", "acceptance", "files_to_touch", "fix"].forEach(
      (k) => {
        const val = document.getElementById("d-" + k)?.value || "";
        data[k] = val.split("\n").filter((x) => x.trim());
      },
    );
    const deps = document.getElementById("d-dependencies")?.value || "";
    data.dependencies = deps
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);

    const riskLevel = document.getElementById("d-risk_level")?.value;
    if (riskLevel) {
      const mitigation = (document.getElementById("d-mitigation")?.value || "")
        .split("\n")
        .filter((x) => x.trim());
      data.risk_assessment = { risk_level: riskLevel, mitigation };
    }

    await fetchJSON(`/api/features/${currentId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    await loadStats();
    await loadFeatures();
    window.selectFeature(currentId);
  } catch (e) {
    showError("Save failed: " + e.message);
  }
};

window.deleteFeature = async function deleteFeature() {
  if (!currentId || !confirm(`Delete feature F${currentId}?`)) return;
  await fetchJSON(`/api/features/${currentId}/delete`, { method: "POST" });
  currentId = null;
  document.getElementById("mainPanel").innerHTML =
    '<div class="empty-state"><div class="icon">📋</div><div>Select a feature</div></div>';
  await loadStats();
  await loadFeatures();
};

window.showNewModal = function showNewModal() {
  document.getElementById("modalContainer").innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal">
        <h3>New Feature</h3>
        <div class="field-group"><label>ID</label><input id="n-id" type="number"></div>
        <div class="field-group"><label>Name</label><input id="n-name"></div>
        <div class="field-group"><label>Title</label><input id="n-title"></div>
        <div class="field-group"><label>Area</label><input id="n-area"></div>
        <div class="field-group"><label>Priority</label>
          <select id="n-priority"><option>Media</option><option>Alta</option><option>Baja</option></select>
        </div>
        <div class="field-group"><label>Description</label><textarea id="n-description"></textarea></div>
        <div class="btn-row">
          <button class="btn" onclick="closeModal()">Cancel</button>
          <button class="btn primary" onclick="createFeature()">Create</button>
        </div>
      </div>
    </div>
  `;
};

window.closeModal = function closeModal() {
  document.getElementById("modalContainer").innerHTML = "";
};

window.createFeature = async function createFeature() {
  const data = {
    id: parseInt(document.getElementById("n-id").value),
    name: document.getElementById("n-name").value,
    title: document.getElementById("n-title").value,
    area: document.getElementById("n-area").value,
    priority: document.getElementById("n-priority").value,
    description: document.getElementById("n-description").value,
  };
  if (!data.id || !data.name || !data.title) {
    alert("ID, Name, Title required");
    return;
  }
  await fetchJSON("/api/features", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  closeModal();
  await loadStats();
  await loadFeatures();
};

export { allFeatures, currentId };
