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

// File pickers: inside the Mac app, open Finder through the app (window.pywebview.api.pick_file),
// because the window's built-in picker can grey out files. In a browser, the normal picker is used.
// Call once per <input type="file">; onFile(file) gets the chosen File either way.
function setupFilePicker(input, onFile) {
  input.addEventListener("click", async (e) => {
    if (!window.pywebview?.api?.pick_file) return; // browser: let the normal picker open
    e.preventDefault();
    try {
      const r = await window.pywebview.api.pick_file();
      if (!r) return; // cancelled
      if (r.error) throw new Error(r.error);
      const bytes = Uint8Array.from(atob(r.data), (c) => c.charCodeAt(0));
      onFile(new File([bytes], r.name));
    } catch (err) {
      alert(err.message || String(err));
    }
  });
  input.addEventListener("change", () => {
    const file = input.files[0];
    input.value = "";
    if (file) onFile(file);
  });
}

// Labels for exam/assignment types (Professors, Classes and syllabus review).
const KIND_LABELS = {
  exam: "📝 Exam", quiz: "✏️ Quiz", assignment: "📄 Assignment",
  project: "🧩 Project", presentation: "🎤 Presentation", other: "📌 Other",
};

function localToday() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}
