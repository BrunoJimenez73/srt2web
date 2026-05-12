function U(e) {
  const t = Math.floor(e / 60),
    l = Math.floor(e % 60);
  return `${t}:${l.toString().padStart(2, "0")}`;
}
function T(e) {
  return (typeof e == "string" ? new Date(e) : new Date(e)).toLocaleTimeString(
    "en-US",
    { hour12: !1 },
  );
}
let o = null,
  y = null,
  a = null,
  p = null,
  v = null,
  d = null,
  S = null,
  h = null;
const q = 1e3;
let c = "",
  i = "ALL",
  g = !0,
  L = null;
function A() {
  y &&
    ((g = !g),
    y.classList.toggle("collapsed", g),
    v && (v.textContent = g ? "▶" : "▼"));
}
function I(e) {
  const t = document.createElement("div");
  return (t.textContent = e), t.innerHTML;
}
function R(e, t, l) {
  if (!o) return;
  a && a.parentElement === o && (a.remove(), (a = null));
  const n = document.createElement("div");
  (n.className = "log-entry"),
    n.setAttribute("role", "listitem"),
    (n.dataset.level = e),
    (n.dataset.message = t.toLowerCase());
  const s = l ? T(l) : new Date().toLocaleTimeString("es-ES"),
    r = e.toLowerCase();
  for (
    n.innerHTML = `
    <span class="log-timestamp">${s}</span>
    <span class="log-level ${r}">[${e}]</span>
    <span class="log-message">${I(t)}</span>
  `,
      $(e, t) || (n.style.display = "none"),
      o.appendChild(n);
    o.children.length > q;

  )
    o.firstChild && o.removeChild(o.firstChild);
  (o.scrollTop = o.scrollHeight), E();
}
function $(e, t) {
  const l = e.toUpperCase();
  return !(
    (i !== "ALL" && l !== i) ||
    (c && !t.toLowerCase().includes(c.toLowerCase()))
  );
}
function E() {
  if (!o) return;
  const e = o.querySelectorAll(".log-entry"),
    t = { ALL: 0, INFO: 0, WARNING: 0, ERROR: 0 };
  e.forEach((n) => {
    const s = n.dataset.level?.toUpperCase() || "INFO";
    t[s] !== void 0 && t[s]++, t.ALL++;
  }),
    o.parentElement?.querySelectorAll(".level-badge")?.forEach((n) => {
      const s = n.dataset.level;
      s && s in t && (n.textContent = String(t[s]));
    });
}
function B(e) {
  L && clearTimeout(L),
    (L = setTimeout(() => {
      (c = e.toLowerCase()), C();
    }, 200));
}
function N(e) {
  (i = e), C();
}
function C() {
  o?.querySelectorAll(".log-entry")?.forEach((t) => {
    const l = t,
      n = (l.dataset.level || "INFO").toUpperCase(),
      s = l.dataset.message || "",
      r = i === "ALL" || n === i,
      u = !c || s.includes(c);
    l.style.display = r && u ? "" : "none";
  }),
    E();
}
function w() {
  const e = o?.querySelectorAll(".log-entry:not([style*='display: none'])");
  if (!e || e.length === 0) {
    alert("No hay logs para exportar");
    return;
  }
  const t = [];
  e.forEach((s) => {
    const r = s,
      u = r.querySelector(".log-timestamp")?.textContent || "",
      m = r.querySelector(".log-level")?.textContent || "",
      f = r.querySelector(".log-message")?.textContent || "";
    t.push({
      timestamp: u,
      level: m.replace("[", "").replace("]", ""),
      message: f,
    });
  });
  const l = new Blob([JSON.stringify(t, null, 2)], {
      type: "application/json",
    }),
    n = new Date().toISOString().split("T")[0];
  b(l, `srt2web-logs-${n}.json`);
}
function x() {
  const e = o?.querySelectorAll(".log-entry:not([style*='display: none'])");
  if (!e || e.length === 0) {
    alert("No hay logs para exportar");
    return;
  }
  const t = [];
  e.forEach((s) => {
    const r = s,
      u = r.querySelector(".log-timestamp")?.textContent || "",
      m = r.querySelector(".log-level")?.textContent || "",
      f = r.querySelector(".log-message")?.textContent || "";
    t.push(`[${u}] ${m} ${f}`);
  });
  const l = new Blob(
      [
        t.join(`
`),
      ],
      { type: "text/plain" },
    ),
    n = new Date().toISOString().split("T")[0];
  b(l, `srt2web-logs-${n}.txt`);
}
function b(e, t) {
  const l = URL.createObjectURL(e),
    n = document.createElement("a");
  (n.href = l), (n.download = t), n.click(), URL.revokeObjectURL(l);
}
function O() {
  const e = o?.querySelectorAll(".log-entry").length || 0;
  (e > 50 && !confirm(`¿Estás seguro de que quieres borrar ${e} logs?`)) ||
    (o &&
      ((o.innerHTML = ""),
      (a = document.createElement("div")),
      (a.className = "log-empty"),
      (a.id = "log-empty"),
      (a.innerHTML = `
    <span class="log-empty-icon">📝</span>
    <span class="log-empty-text">Sin registros aún</span>
  `),
      o.appendChild(a),
      (c = ""),
      (i = "ALL"),
      p && (p.value = ""),
      d && (d.value = "ALL")));
}
function j() {
  (o = document.getElementById("log-content")),
    (y = document.querySelector(".log-panel")),
    (a = document.getElementById("log-empty")),
    (p = document.getElementById("log-search")),
    (v = document.getElementById("log-collapse-icon")),
    (d = document.getElementById("log-level-filter")),
    (S = document.getElementById("btn-export-json")),
    (h = document.getElementById("btn-export-txt")),
    p?.addEventListener("input", (e) => {
      const t = e.target.value;
      B(t);
    }),
    d?.addEventListener("change", (e) => {
      const t = e.target.value;
      N(t);
    }),
    S?.addEventListener("click", (e) => {
      e.stopPropagation(), w();
    }),
    h?.addEventListener("click", (e) => {
      e.stopPropagation(), x();
    }),
    (window.toggleLogPanel = A),
    (window.clearLogs = O),
    (window.exportLogsJson = w),
    (window.exportLogsTxt = x);
}
export { R as a, U as f, j as i };
