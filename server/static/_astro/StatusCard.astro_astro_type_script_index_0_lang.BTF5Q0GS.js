import { j as p } from "./vendor-signals.DQU3zyvD.js";
import {
  g as u,
  t as a,
  o as d,
} from "./InputCard.astro_astro_type_script_index_0_lang.DFbizcxd.js";
function n(t) {
  return document.getElementById(t);
}
p(() => {
  const t = u.value,
    e = n("status-dot"),
    r = n("status-text"),
    i = n("btn-start"),
    s = n("btn-stop");
  if (!e || !r) return;
  const o = t?.state === "running",
    c = t?.state === "stopping",
    l = t?.state === "error";
  (e.className = "status-dot"),
    e.classList.toggle("running", o),
    e.classList.toggle("error", l),
    e.classList.toggle("stopped", !o && !l && !c),
    (r.textContent = o
      ? a("status_active")
      : l
        ? a("status_error")
        : c
          ? a("status_stopping")
          : a("status_off")),
    i && ((i.disabled = o), (i.style.opacity = o ? "0.5" : "1")),
    s && ((s.disabled = !o), (s.style.opacity = o ? "1" : "0.5"));
});
p(() => {
  const t = d.value,
    e = n("url-emision-label"),
    r = n("url-emision"),
    i = n("url-stream"),
    s = n("url-player");
  e && (e.textContent = t.primaryLabel),
    r && (r.textContent = t.primaryUrl),
    i && (i.textContent = t.streamUrl),
    s && ((s.textContent = t.playerUrl), (s.href = t.playerUrl));
});
document.addEventListener("DOMContentLoaded", function () {
  const t = document.getElementById("btn-stop");
  t &&
    t.addEventListener("click", () => {
      window.stopPipeline && window.stopPipeline();
    });
  const e = document.getElementById("btn-start");
  e &&
    e.addEventListener("click", () => {
      window.startPipeline && window.startPipeline();
    });
});
