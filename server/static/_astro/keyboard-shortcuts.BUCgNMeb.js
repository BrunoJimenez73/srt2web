const __vite__mapDeps = (
  i,
  m = __vite__mapDeps,
  d = m.f ||
    (m.f = [
      "_astro/index.astro_astro_type_script_index_0_lang.BJ9acpSA.js",
      "_astro/store.BQ17F1K4.js",
      "_astro/api.BpNi2mzZ.js",
      "_astro/index.BpSbb1Lw.js",
      "_astro/logpanel.DVarbH4P.js",
    ]),
) => i.map((i) => d[i]);
import {
  h as i,
  _ as s,
  a as l,
  b as d,
} from "./index.astro_astro_type_script_index_0_lang.BJ9acpSA.js";
import { s as a } from "./index.BpSbb1Lw.js";
let o = !1;
const c = [
  {
    key: "s",
    ctrlKey: !0,
    handler: (t) => {
      t.preventDefault(), i(), a("Configuración guardada (Ctrl+S)", "info");
    },
    description: "Guardar configuración",
    preventDefault: !0,
  },
  {
    key: " ",
    handler: (t) => {
      const e = t.target.tagName;
      e === "INPUT" ||
        e === "TEXTAREA" ||
        e === "SELECT" ||
        (t.preventDefault(),
        s(
          async () => {
            const { pipelineStatus: r } = await import(
              "./index.astro_astro_type_script_index_0_lang.BJ9acpSA.js"
            ).then((n) => n.i);
            return { pipelineStatus: r };
          },
          __vite__mapDeps([0, 1, 2, 3, 4]),
        ).then(({ pipelineStatus: r }) => {
          r.value?.state === "running" ? l() : d();
        }));
    },
    description: "Iniciar/Detener pipeline",
    preventDefault: !0,
  },
  {
    key: "d",
    ctrlKey: !0,
    handler: (t) => {
      t.preventDefault();
      const e = document.documentElement;
      e.classList.contains("dark")
        ? (e.classList.remove("dark"),
          localStorage.setItem("srt2web_theme", "light"),
          a("Modo claro activado", "info"))
        : (e.classList.add("dark"),
          localStorage.setItem("srt2web_theme", "dark"),
          a("Modo oscuro activado", "info"));
    },
    description: "Alternar modo oscuro",
    preventDefault: !0,
  },
];
function u(t) {
  for (const e of c)
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
function p() {
  o || (document.addEventListener("keydown", u), (o = !0));
}
export { p as initKeyboardShortcuts };
