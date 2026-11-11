// Helpers shared by every page.
const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const APP_TOKEN = document.querySelector('meta[name="app-token"]').content;

async function api(method, url, body) {
  const isForm = body instanceof FormData;
  const headers = { "X-App-Token": APP_TOKEN };
  if (body && !isForm) headers["Content-Type"] = "application/json";
  const res = await fetch(url, {
    method,
    headers,
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Something went wrong (${res.status})`);
  return data;
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.add("hidden"), 2000);
}

// Inside the Mac app window, links and copying go through the app (window.pywebview).
// In a normal browser they work the usual way.
function openExternal(url) {
  if (window.pywebview?.api?.open_url) window.pywebview.api.open_url(url);
  else if (url.startsWith("mailto:")) window.location.href = url;
  else window.open(url, "_blank", "noopener");
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (err) {
    if (window.pywebview?.api?.copy_text) await window.pywebview.api.copy_text(text);
    else throw err;
  }
}
