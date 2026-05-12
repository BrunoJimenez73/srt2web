import "./index.astro_astro_type_script_index_0_lang.BJ9acpSA.js";
document.querySelectorAll(".collapsible-module-wrapper").forEach((n) => {
  const e = n.querySelector(".process-header"),
    s = n.querySelector(".process-content");
  if (!e || !s) return;
  const r = document.createElement("span");
  (r.className = "cm-collapse-icon"),
    (r.textContent = "▶"),
    r.setAttribute("aria-hidden", "true"),
    e.insertBefore(r, e.firstChild),
    (e.style.cursor = "pointer"),
    (e.title = "Click para colapsar/expandir");
  const o = () => {
    const t = n.classList.toggle("collapsed");
    (r.textContent = t ? "▶" : "▼"),
      e.setAttribute("aria-expanded", String(!t));
  };
  e.addEventListener("click", (t) => {
    t.target.closest(".toggle-switch, .gpu-badge, button, input, select, a") ||
      o();
  }),
    e.setAttribute("role", "button"),
    e.setAttribute("tabindex", "0"),
    e.setAttribute("aria-expanded", "true"),
    e.addEventListener("keydown", (t) => {
      (t.key === "Enter" || t.key === " ") && (t.preventDefault(), o());
    });
});
