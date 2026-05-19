import "./index.astro_astro_type_script_index_0_lang.EBc9GzDD.js";
import {
  e as n,
  t as r,
} from "./InputCard.astro_astro_type_script_index_0_lang.DFbizcxd.js";
import { h as u, c as p, d as m } from "./pipeline-control.foNQ0eTb.js";
let a = !1;
const h =
  "input:not([type=checkbox]):not([type=radio]), textarea, select, [contenteditable]";
function d() {
  return document.activeElement ? document.activeElement.matches(h) : !1;
}
const l = [
  {
    key: "s",
    ctrlKey: !0,
    handler: (t) => {
      u(), n(r("config_saved_shortcut"), "info");
    },
    description: "Guardar configuración",
    preventDefault: !0,
  },
  {
    key: "Enter",
    ctrlKey: !0,
    handler: async (t) => {
      document.getElementById("status-dot")?.classList.contains("running") ?? !1
        ? await p()
        : await m();
    },
    description: "Iniciar/Detener pipeline",
    preventDefault: !0,
  },
  {
    key: "/",
    ctrlKey: !0,
    handler: () => {
      c();
    },
    description: "Mostrar ayuda de atajos",
    preventDefault: !0,
  },
  {
    key: "?",
    ctrlKey: !1,
    handler: () => {
      d() || c();
    },
    description: "Mostrar ayuda de atajos",
    preventDefault: !1,
  },
  {
    key: "d",
    ctrlKey: !0,
    handler: (t) => {
      const e = document.documentElement,
        s = e.classList.contains("dark"),
        o = document.getElementById("theme-icon");
      s
        ? (e.classList.remove("dark"),
          localStorage.setItem("srt2web_theme", "light"),
          o && (o.textContent = "☀️"),
          n(r("light_mode_on"), "info"))
        : (e.classList.add("dark"),
          localStorage.setItem("srt2web_theme", "dark"),
          o && (o.textContent = "🌙"),
          n(r("dark_mode_on"), "info"));
    },
    description: "Alternar modo oscuro",
    preventDefault: !0,
  },
  {
    key: "l",
    ctrlKey: !0,
    handler: () => {
      const t = document.querySelector(".log-panel");
      if (t) {
        t.classList.toggle("collapsed");
        const e = document.getElementById("log-header");
        e &&
          e.setAttribute(
            "aria-expanded",
            String(!t.classList.contains("collapsed")),
          );
      }
    },
    description: "Alternar panel de logs",
    preventDefault: !0,
  },
  {
    key: "Escape",
    ctrlKey: !1,
    handler: () => {
      const t = document.getElementById("shortcuts-modal");
      t && (t.style.display = "none");
      const e = document.getElementById("secure-panel");
      if (e?.classList.contains("open")) {
        e.classList.remove("open");
        const s = document.getElementById("secure-arrow");
        s && s.classList.remove("open");
      }
    },
    description: "Cerrar modal / panel",
    preventDefault: !1,
  },
];
function y(t) {
  if (!(d() && t.key !== "Escape" && !t.key.startsWith("F"))) {
    for (const e of l)
      if (
        t.key.toLowerCase() === e.key.toLowerCase() &&
        (e.ctrlKey === void 0 || t.ctrlKey === e.ctrlKey) &&
        (e.shiftKey === void 0 || t.shiftKey === e.shiftKey) &&
        (e.altKey === void 0 || t.altKey === e.altKey)
      ) {
        e.preventDefault !== !1 && t.preventDefault(), e.handler(t);
        return;
      }
  }
}
function c() {
  const t = document.getElementById("shortcuts-modal");
  if (t) {
    t.remove();
    return;
  }
  const e = document.createElement("div");
  (e.id = "shortcuts-modal"),
    (e.className = "shortcuts-modal"),
    e.setAttribute("role", "dialog"),
    e.setAttribute("aria-label", r("keyboard_shortcuts"));
  const s = l
    .filter((o) => o.key !== "Escape")
    .map(
      (o) =>
        `<div class="shortcut-row"><kbd>${`${o.ctrlKey ? "Ctrl+" : ""}${
          o.shiftKey ? "Shift+" : ""
        }${o.altKey ? "Alt+" : ""}${
          o.key === "/" ? "/" : o.key.toUpperCase()
        }`}</kbd><span>${o.description}</span></div>`,
    )
    .join("");
  (e.innerHTML = `
    <div class="shortcuts-modal-backdrop"></div>
    <div class="shortcuts-modal-content">
      <div class="shortcuts-header">
        <span>⌨️ ${r("keyboard_shortcuts")}</span>
        <button class="shortcuts-close" id="shortcuts-close" aria-label="${r(
          "close",
        )}">✕</button>
      </div>
      <div class="shortcuts-body">${s}</div>
    </div>
  `),
    document.body.appendChild(e),
    document
      .getElementById("shortcuts-close")
      ?.addEventListener("click", () => e.remove()),
    e
      .querySelector(".shortcuts-modal-backdrop")
      ?.addEventListener("click", () => e.remove());
}
function x() {
  a || (document.addEventListener("keydown", y), (a = !0));
}
const i = "shortcuts-modal-styles";
if (!document.getElementById(i)) {
  const t = document.createElement("style");
  (t.id = i),
    (t.textContent = `
    .shortcuts-modal {
      position: fixed;
      inset: 0;
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .shortcuts-modal-backdrop {
      position: absolute;
      inset: 0;
      background: rgba(0,0,0,0.6);
    }
    .shortcuts-modal-content {
      position: relative;
      background: var(--bg-card);
      border: 1px solid var(--border-dim);
      border-radius: var(--radius-md);
      padding: 20px;
      min-width: 320px;
      max-width: 460px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }
    .shortcuts-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      font-size: 14px;
      font-weight: 600;
      color: var(--text-prime);
    }
    .shortcuts-close {
      background: none;
      border: none;
      color: var(--text-dim);
      cursor: pointer;
      font-size: 16px;
      padding: 4px;
    }
    .shortcuts-close:hover { color: var(--text-prime); }
    .shortcuts-body {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .shortcut-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-size: 12px;
      color: var(--text-sec);
    }
    .shortcut-row kbd {
      font-family: var(--font-mono);
      background: var(--bg-surface);
      border: 1px solid var(--border-dim);
      border-radius: 4px;
      padding: 3px 8px;
      font-size: 11px;
      color: var(--text-prime);
      white-space: nowrap;
    }
  `),
    document.head.appendChild(t);
}
export { x as initKeyboardShortcuts };
