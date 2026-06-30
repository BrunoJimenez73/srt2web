// Harness API client
const API = "";

export async function fetchJSON(url, opts) {
  const r = await fetch(API + url, opts);
  const data = await r.json();
  if (!r.ok) {
    const msg = data.error || `HTTP ${r.status}`;
    throw new Error(msg);
  }
  if (data.error) {
    throw new Error(data.error);
  }
  return data;
}

export async function apiCall(method, url, body) {
  const opts = { method };
  if (body) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  return fetchJSON(url, opts);
}

export function esc(s) {
  if (!s) return "";
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function showError(msg) {
  const el = document.getElementById("errorBar");
  if (el) {
    el.textContent = msg;
    el.style.display = "block";
    setTimeout(() => {
      el.style.display = "none";
    }, 5000);
  } else {
    alert(msg);
  }
}
