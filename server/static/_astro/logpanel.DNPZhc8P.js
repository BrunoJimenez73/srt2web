function w(e) {
  const l = Math.floor(e / 60),
    s = Math.floor(e % 60);
  return `${l}:${s.toString().padStart(2, "0")}`;
}
function u(e) {
  return (typeof e == "string" ? new Date(e) : new Date(e)).toLocaleTimeString(
    "en-US",
    { hour12: !1 },
  );
}
let t = null,
  g = null,
  o = null,
  r = null,
  d = null;
const p = 500;
let a = "",
  i = !0;
function f() {
  g &&
    ((i = !i),
    g.classList.toggle("collapsed", i),
    d && (d.textContent = i ? "▶" : "▼"));
}
function y(e) {
  const l = document.createElement("div");
  return (l.textContent = e), l.innerHTML;
}
function C(e, l, s) {
  if (!t) return;
  o && o.parentElement === t && (o.remove(), (o = null));
  const n = document.createElement("div");
  (n.className = "log-entry"),
    n.setAttribute("role", "listitem"),
    (n.dataset.level = e),
    (n.dataset.message = l.toLowerCase());
  const c = s ? u(s) : new Date().toLocaleTimeString("es-ES"),
    m = e.toLowerCase();
  for (
    n.innerHTML = `
    <span class="log-timestamp">${c}</span>
    <span class="log-level ${m}">[${e}]</span>
    <span class="log-message">${y(l)}</span>
  `,
      a &&
        !n.dataset.message.includes(a.toLowerCase()) &&
        (n.style.display = "none"),
      t.appendChild(n);
    t.children.length > p;

  )
    t.firstChild && t.removeChild(t.firstChild);
  t.scrollTop = t.scrollHeight;
}
function L(e) {
  (a = e.toLowerCase()),
    t?.querySelectorAll(".log-entry")?.forEach((s) => {
      const n = s;
      if (a) {
        const c = n.dataset.message?.includes(a);
        n.style.display = c ? "" : "none";
      } else n.style.display = "";
    });
}
function h() {
  t &&
    ((t.innerHTML = ""),
    (o = document.createElement("div")),
    (o.className = "log-empty"),
    (o.id = "log-empty"),
    (o.innerHTML = `
    <span class="log-empty-icon">📝</span>
    <span class="log-empty-text">Sin registros aún</span>
  `),
    t.appendChild(o),
    (a = ""),
    r && (r.value = ""));
}
function E() {
  (t = document.getElementById("log-content")),
    (g = document.querySelector(".log-panel")),
    (o = document.getElementById("log-empty")),
    (r = document.getElementById("log-search")),
    (d = document.getElementById("log-collapse-icon")),
    r?.addEventListener("input", (e) => {
      const l = e.target.value;
      L(l);
    }),
    (window.toggleLogPanel = f),
    (window.clearLogs = h);
}
export { C as a, w as f, E as i };
