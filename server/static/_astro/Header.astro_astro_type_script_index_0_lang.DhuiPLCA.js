import { s as I, g as L } from "./api.D6SjT7hd.js";
import { s as b } from "./toast.BmJy0qds.js";
import { a as w, e as B } from "./pipeline-control.foNQ0eTb.js";
import {
  p as T,
  b as i,
  t as a,
  d as C,
  s as $,
  e as u,
} from "./InputCard.astro_astro_type_script_index_0_lang.DFbizcxd.js";
function g(e, t = "") {
  document.body.classList.toggle("loading", e), e && t && i("INFO", `${t}...`);
}
async function h() {
  try {
    const e = await fetch("/api/presets");
    if (!e.ok) return;
    const t = await e.json();
    T.value = t.presets || [];
  } catch (e) {
    i("ERROR", `${a("presets_load_error")}: ${e.message}`);
  }
}
async function _(e) {
  try {
    g(!0, `${a("preset_applying")}: ${e}`);
    const t = await fetch(`/api/presets/${encodeURIComponent(e)}/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!t.ok) {
      const p = await t.text();
      throw new Error(p || `Failed to apply preset: ${e}`);
    }
    const s = await t.json();
    (C.value = s.config),
      w(s.config),
      ($.value = e),
      u(`${a("preset_applied")}: ${e}`, "success"),
      i("INFO", `${a("preset_applied")}: ${e}`);
  } catch (t) {
    u(`${a("preset_error")}: ${t.message}`, "error"),
      i("ERROR", `${a("preset_error")}: ${t.message}`);
  } finally {
    g(!1);
  }
}
async function O(e) {
  try {
    g(!0, `${a("preset_saving")}: ${e}`);
    const t = await fetch("/api/presets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: e, description: "" }),
    });
    if (!t.ok) {
      const s = await t.text();
      throw new Error(s || `Failed to save preset: ${e}`);
    }
    await h(),
      u(`${a("preset_saved")}: ${e}`, "success"),
      i("INFO", `${a("preset_saved")}: ${e}`);
  } catch (t) {
    u(`${a("preset_save_error")}: ${t.message}`, "error"),
      i("ERROR", `${a("preset_save_error")}: ${t.message}`);
  } finally {
    g(!1);
  }
}
let c = null,
  r = null,
  d = null,
  l = null,
  n = null,
  o = null,
  v = null,
  E = null,
  k = null;
function f() {
  const e = L();
  e
    ? (l && (l.textContent = "Secure ON"),
      c?.classList.add("active"),
      n && (n.value = e))
    : (l && (l.textContent = "Secure OFF"),
      c?.classList.remove("active"),
      n && (n.value = ""));
}
function R() {
  if (!r || !d) return;
  const e = r.classList.toggle("hidden");
  d.classList.toggle("open", !e), e || (f(), n?.focus());
}
function y() {
  !r || !d || (r.classList.add("hidden"), d.classList.remove("open"));
}
function x() {
  !n ||
    !o ||
    (n.type === "password"
      ? ((n.type = "text"), (o.textContent = "🙈"))
      : ((n.type = "password"), (o.textContent = "👁")));
}
function P() {
  if (!n || !o) return;
  const e = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    t = 32;
  let s = "";
  const p = new Uint32Array(t);
  crypto.getRandomValues(p);
  for (let m = 0; m < t; m++) s += e[p[m] % e.length];
  (n.value = s), (n.type = "text"), (o.textContent = "🙈");
}
function S() {
  if (!n) return;
  const e = n.value.trim();
  I(e),
    f(),
    b(
      e
        ? "🔐 Token guardado. Recarga para aplicar."
        : "🔓 Autenticación desactivada.",
      e ? "success" : "info",
    ),
    y();
}
function F(e) {
  if (!r || !c) return;
  const t = e.target;
  !r.contains(t) && !c.contains(t) && y();
}
function N() {
  (c = document.getElementById("btn-secure-toggle")),
    (r = document.getElementById("secure-panel")),
    (d = document.getElementById("secure-arrow")),
    (l = document.getElementById("secure-label")),
    (n = document.getElementById("secure-token-input")),
    (o = document.getElementById("btn-eye-token")),
    (v = document.getElementById("btn-gen-token")),
    (E = document.getElementById("btn-save-secure")),
    (k = document.getElementById("btn-close-secure")),
    c?.addEventListener("click", (e) => {
      e.stopPropagation(), R();
    }),
    k?.addEventListener("click", y),
    document.addEventListener("click", F),
    o?.addEventListener("click", x),
    v?.addEventListener("click", P),
    E?.addEventListener("click", S),
    f();
}
N();
h();
document.getElementById("preset-list").addEventListener("click", async (e) => {
  const t = e.target.closest(".preset-item");
  if (!t) return;
  const s = t.dataset.preset;
  s && (($.value = s), await _(s));
});
document
  .getElementById("btn-confirm-save")
  .addEventListener("click", async () => {
    const e = document.getElementById("preset-name-input").value.trim();
    e &&
      (await O(e), (document.getElementById("preset-name-input").value = ""));
  });
document.getElementById("btn-export-config").addEventListener("click", () => {
  B();
});
document.getElementById("btn-save-preset").addEventListener("click", (e) => {
  e.stopPropagation(),
    document.getElementById("preset-panel").classList.toggle("hidden");
});
document.addEventListener("click", (e) => {
  const t = document.getElementById("preset-panel"),
    s = document.getElementById("btn-save-preset");
  !t.contains(e.target) && !s.contains(e.target) && t.classList.add("hidden");
});
