const __vite__mapDeps = (
  i,
  m = __vite__mapDeps,
  d = m.f ||
    (m.f = [
      "_astro/index.astro_astro_type_script_index_0_lang.zf2FrLkp.js",
      "_astro/store.YvzDn7sh.js",
      "_astro/api.CwWA6hCN.js",
      "_astro/index.BpSbb1Lw.js",
      "_astro/logpanel.Dz867OYr.js",
    ]),
) => i.map((i) => d[i]);
import {
  h as s,
  _ as l,
  a as d,
  b as c,
} from "./index.astro_astro_type_script_index_0_lang.zf2FrLkp.js";
import { s as a } from "./index.BpSbb1Lw.js";
let o = !1;
const i = [
  {
    key: "s",
    ctrlKey: !0,
    handler: (e) => {
      e.preventDefault(), s(), a("Configuración guardada (Ctrl+S)", "info");
    },
    description: "Guardar configuración",
    preventDefault: !0,
  },
  {
    key: " ",
    handler: (e) => {
      const t = e.target.tagName;
      t === "INPUT" ||
        t === "TEXTAREA" ||
        t === "SELECT" ||
        (e.preventDefault(),
        l(
          async () => {
            const { pipelineStatus: r } = await import(
              "./index.astro_astro_type_script_index_0_lang.zf2FrLkp.js"
            ).then((n) => n.i);
            return { pipelineStatus: r };
          },
          __vite__mapDeps([0, 1, 2, 3, 4]),
        ).then(({ pipelineStatus: r }) => {
          r.value?.state === "running" ? d() : c();
        }));
    },
    description: "Iniciar/Detener pipeline",
    preventDefault: !0,
  },
  {
    key: "d",
    ctrlKey: !0,
    handler: (e) => {
      e.preventDefault();
      const t = document.documentElement;
      t.classList.contains("dark")
        ? (t.classList.remove("dark"),
          localStorage.setItem("srt2web_theme", "light"),
          a("Modo claro activado", "info"))
        : (t.classList.add("dark"),
          localStorage.setItem("srt2web_theme", "dark"),
          a("Modo oscuro activado", "info"));
    },
    description: "Alternar modo oscuro",
    preventDefault: !0,
  },
];
function u(e) {
  for (const t of i)
    if (
      e.key.toLowerCase() === t.key.toLowerCase() &&
      (t.ctrlKey === void 0 || e.ctrlKey === t.ctrlKey) &&
      (t.shiftKey === void 0 || e.shiftKey === t.shiftKey) &&
      (t.altKey === void 0 || e.altKey === t.altKey)
    ) {
      t.preventDefault !== !1 && e.preventDefault(), t.handler(e);
      return;
    }
}
function h() {
  if (o) {
    console.warn("Keyboard shortcuts already initialized");
    return;
  }
  document.addEventListener("keydown", u),
    (o = !0),
    console.log(
      "Keyboard shortcuts initialized:",
      i.map((e) => ({
        key: `${e.ctrlKey ? "Ctrl+" : ""}${e.shiftKey ? "Shift+" : ""}${
          e.altKey ? "Alt+" : ""
        }${e.key.toUpperCase()}`,
        description: e.description,
      })),
    );
}
export { h as initKeyboardShortcuts };
