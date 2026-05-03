import { i as l } from "./logpanel.Co3ahUsz.js";
let d = "";
function a(t) {
  (d = t.toLowerCase()),
    document.querySelectorAll(".log-entry").forEach((n) => {
      const e = n.dataset.level || "",
        o = n.dataset.message || "";
      d === "" || o.toLowerCase().includes(d) || e.includes(d)
        ? n.classList.remove("hidden")
        : n.classList.add("hidden");
    });
}
function i(t, s, n) {
  const e = document.getElementById("log-content");
  if (!e) return;
  const o = document.createElement("div");
  (o.className = "log-entry"),
    (o.dataset.level = t),
    (o.dataset.message = s),
    (o.textContent = `[${n}] ${s}`),
    d &&
      !s.toLowerCase().includes(d) &&
      !t.includes(d) &&
      o.classList.add("hidden"),
    e.appendChild(o),
    (e.scrollTop = e.scrollHeight);
}
l();
document.addEventListener("DOMContentLoaded", function () {
  const t = document.getElementById("log-header");
  t &&
    t.addEventListener("click", function () {
      window.toggleLogPanel();
    });
  const s = document.getElementById("log-search");
  s &&
    s.addEventListener("click", function (e) {
      e.stopPropagation();
    });
  const n = document.getElementById("btn-clear-logs");
  n &&
    n.addEventListener("click", function (e) {
      e.stopPropagation(), clearLogs();
    });
});
const c = document.getElementById("log-search");
c &&
  c.addEventListener("input", (t) => {
    a(t.target.value);
  });
window.addLogEntry = i;
