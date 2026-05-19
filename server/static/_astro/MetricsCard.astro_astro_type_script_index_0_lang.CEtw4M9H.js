import { j as C } from "./vendor-signals.DQU3zyvD.js";
import {
  q as k,
  v as A,
  x as w,
  y as M,
  g as F,
  z as E,
  A as I,
  B as N,
} from "./InputCard.astro_astro_type_script_index_0_lang.DFbizcxd.js";
function e(t) {
  return document.getElementById(t);
}
function p(t) {
  return t < 40 ? "low" : t < 80 ? "medium" : "high";
}
function j(t) {
  return t < 80 ? "warning" : "critical";
}
function B(t) {
  return t < 70 ? "#22c55e" : t < 85 ? "#f59e0b" : "#ef4444";
}
let a = null;
C(() => {
  const t = k.value,
    c = A.value,
    r = w.value,
    u = e("metric-cpu-bar"),
    o = e("metric-cpu-value"),
    s = e("metric-cpu");
  u &&
    ((u.style.width = `${t.cpu}%`), (u.className = `metric-bar ${p(t.cpu)}`)),
    s && (s.className = `metric-item ${j(t.cpu)}`),
    o && (o.textContent = `${t.cpu.toFixed(0)}%`);
  const n = e("metric-memory-bar"),
    i = e("metric-memory-value"),
    l = e("metric-memory-percent");
  n &&
    ((n.style.width = `${t.memoryPercent}%`),
    (n.className = `metric-bar ${p(t.memoryPercent)}`)),
    i && (i.textContent = `${t.memoryMb.toFixed(0)} MB`),
    l && (l.textContent = `${t.memoryPercent.toFixed(0)}%`);
  const m = e("metric-gpu-bar"),
    f = e("metric-gpu-value"),
    g = e("metric-gpu-memory");
  m &&
    ((m.style.width = `${t.gpuUtil}%`),
    (m.className = `metric-bar ${p(t.gpuUtil)}`)),
    f && (f.textContent = `${t.gpuUtil.toFixed(0)}%`),
    g &&
      (g.textContent = t.gpuMemMb > 0 ? `${t.gpuMemMb.toFixed(0)} MB` : "N/A");
  const h = e("metric-throughput-bar"),
    y = e("metric-throughput-value");
  h && (h.style.width = `${Math.min(c * 10, 100)}%`),
    y && (y.textContent = `${c.toFixed(2)}/s`);
  const d = e("latency-value");
  d && (d.textContent = r > 0 ? `${r.toFixed(1)}s` : "0s");
  const $ = Date.now();
  t.cpu > 90
    ? a === null
      ? (a = $)
      : $ - a >= 5e3 && (M.value = !0)
    : ((a = null), (M.value = !1));
  const x = F.value?.chunks_failed ?? 0,
    v = e("chunks-failed"),
    b = e("chunks-failed-text");
  v &&
    b &&
    ((v.style.display = x > 0 ? "inline-flex" : "none"),
    (b.textContent = `${x} failed`));
});
C(() => {
  const t = E.value,
    c = I.value,
    r = N.value,
    u = document.getElementById("cpu-sparkline-line"),
    o = document.getElementById("gpu-sparkline-line"),
    s = document.getElementById("tp-sparkline-line");
  if (
    (u &&
      t.length > 1 &&
      (u.setAttribute(
        "points",
        t.map((n, i) => `${i},${20 - Math.min(n * 0.2, 20)}`).join(" "),
      ),
      (u.style.stroke = B(t[t.length - 1] || 0))),
    o &&
      c.length > 1 &&
      (o.setAttribute(
        "points",
        c.map((n, i) => `${i},${20 - Math.min(n * 0.2, 20)}`).join(" "),
      ),
      (o.style.stroke = B(c[c.length - 1] || 0))),
    s && r.length > 1)
  ) {
    const n = Math.max(...r, 0.1);
    s.setAttribute(
      "points",
      r.map((i, l) => `${l},${20 - Math.min((i / n) * 20, 20)}`).join(" "),
    );
  }
});
