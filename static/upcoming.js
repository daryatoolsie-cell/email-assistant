// Upcoming page: every exam and assignment across your classes, with check-offs and study checklists.

const KINDS = {
  exam: "📝 Exam", quiz: "✏️ Quiz", assignment: "📄 Assignment",
  project: "🧩 Project", presentation: "🎤 Presentation", other: "📌 Other",
};
let items = [];
let classes = [];
const openEdits = new Set(); // items whose edit form is open

function localToday() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}
function daysUntil(dateStr) {
  return Math.round((new Date(dateStr) - new Date(localToday())) / 86400000);
}

function groupOf(it) {
  if (it.done) return "done";
  if (!it.due_date) return "nodate";
  const d = daysUntil(it.due_date);
  if (d < 0) return "overdue";
  if (d <= 7) return "week";
  if (d <= 14) return "next";
  return "later";
}
const GROUPS = [
  ["overdue", "⚠️ Overdue"], ["week", "This week"], ["next", "Next week"],
  ["later", "Later"], ["nodate", "No date yet"], ["done", "✓ Completed"],
];

function dueText(it) {
  if (!it.due_date) return it.date_text ? `Syllabus says “${esc(it.date_text)}”` : "No date";
  const d = new Date(`${it.due_date}T${it.due_time || "00:00"}`);
  const day = d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
  const time = it.due_time ? ", " + d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "";
  const n = daysUntil(it.due_date);
  const when = it.done ? "" : n < 0 ? `${-n} day${n === -1 ? "" : "s"} ago` : n === 0 ? "today" : n === 1 ? "tomorrow" : `in ${n} days`;
  const urgency = it.done ? "" : n <= 2 ? "err" : n <= 7 ? "warn" : "";
  return `${day}${time}${when ? ` <span class="chip ${urgency}">${when}</span>` : ""}`;
}

function emailLinks(it) {
  const base = `/?prof=${it.professor_id}&item=${it.id}`;
  const links = [];
  if (["assignment", "project", "presentation", "other"].includes(it.kind)) links.push([`${base}&type=extension`, "⏰ Ask for an extension"]);
  links.push([`${base}&type=question`, "❓ Ask a question"]);
  if (it.kind === "exam" || it.kind === "quiz") links.push([`${base}&type=office_hours`, "🗓️ Office hours to prepare"]);
  return links.map(([href, label]) => `<a class="btn secondary" href="${href}">${label}</a>`).join("");
}

function checklistHtml(it) {
  if (!["exam", "quiz"].includes(it.kind) || it.done) return "";
  if (!it.checklist.length) {
    return `<button class="secondary" data-act="checklist">✨ Make a study checklist</button>`;
  }
  const doneCount = it.checklist.filter((c) => c.done).length;
  const pct = Math.round((doneCount / it.checklist.length) * 100);
  return `
    <div class="checklist">
      <div class="checklist-head"><strong>Study checklist</strong> <span class="muted small">${doneCount}/${it.checklist.length}</span>
        <button class="link" data-act="checklist" title="Make a new checklist">↻ Redo</button></div>
      <div class="progress"><span style="width:${pct}%"></span></div>
      ${it.checklist.map((c, i) => `
        <label class="toggle check-row"><input type="checkbox" data-check="${i}" ${c.done ? "checked" : ""}> <span class="${c.done ? "struck" : ""}">${esc(c.text)}</span></label>`).join("")}
    </div>`;
}

function editHtml(it) {
  return `
    <div class="up-edit">
      <div class="sr-item-grid">
        <label>Title <input data-e="title" value="${esc(it.title)}"></label>
        <label>Date <input type="date" data-e="due_date" value="${esc(it.due_date)}"></label>
        <label>Time <input type="time" data-e="due_time" value="${esc(it.due_time)}"></label>
      </div>
      <label>What's on it / notes <textarea data-e="topics" rows="2">${esc(it.topics)}</textarea></label>
      <div class="row"><button data-act="save-edit">Save</button><button class="secondary" data-act="cancel-edit">Cancel</button></div>
    </div>`;
}

function card(it) {
  const editing = openEdits.has(it.id);
  return `
  <div class="up-item ${it.done ? "is-done" : ""}" data-id="${it.id}">
    <label class="up-check" title="Mark as done"><input type="checkbox" data-act="done" ${it.done ? "checked" : ""}></label>
    <div class="up-body">
      <div class="up-title"><strong class="${it.done ? "struck" : ""}">${esc(it.title)}</strong>
        <span class="chip">${KINDS[it.kind] || it.kind}</span> <span class="chip">${esc(it.course)}</span>
        ${it.weight ? `<span class="chip">${esc(it.weight)}</span>` : ""}</div>
      <div class="small">${dueText(it)}</div>
      ${editing ? editHtml(it) : `
        ${it.topics ? `<div class="small up-topics"><strong>${it.kind === "exam" || it.kind === "quiz" ? "What's on it" : "Notes"}:</strong> ${esc(it.topics)}</div>` : ""}
        ${it.description ? `<div class="muted small">${esc(it.description)}</div>` : ""}
        ${checklistHtml(it)}
        <div class="row up-actions">
          ${it.done ? "" : emailLinks(it)}
          <button class="link" data-act="edit">Edit</button>
          <button class="link danger" data-act="delete">Delete</button>
        </div>`}
    </div>
  </div>`;
}

function render() {
  const cls = $("#up-class").value;
  const showDone = $("#up-show-done").checked;
  const visible = items.filter((it) => (!cls || String(it.professor_id) === cls) && (showDone || !it.done));

  const week = items.filter((it) => !it.done && it.due_date && daysUntil(it.due_date) >= 0 && daysUntil(it.due_date) <= 7);
  const count = (k) => week.filter((it) => it.kind === k).length;
  const parts = [];
  if (count("exam")) parts.push(`${count("exam")} exam${count("exam") > 1 ? "s" : ""}`);
  if (count("quiz")) parts.push(`${count("quiz")} quiz${count("quiz") > 1 ? "zes" : ""}`);
  const rest = week.length - count("exam") - count("quiz");
  if (rest) parts.push(`${rest} assignment${rest > 1 ? "s" : ""}/other`);
  $("#up-summary").textContent = items.length
    ? (parts.length ? `This week: ${parts.join(", ")}.` : "Nothing due in the next 7 days. 🎉")
    : "";

  $("#up-groups").innerHTML = GROUPS.map(([g, label]) => {
    const list = visible.filter((it) => groupOf(it) === g);
    return list.length ? `<section class="panel"><h2>${label} <span class="muted small">${list.length}</span></h2>${list.map(card).join("")}</section>` : "";
  }).join("");
  $("#up-empty").classList.toggle("hidden", items.length > 0);
}

async function load() {
  [items, classes] = await Promise.all([api("GET", "/api/items"), api("GET", "/api/professors")]);
  const prev = $("#up-class").value;
  $("#up-class").innerHTML = `<option value="">All classes</option>` +
    classes.map((p) => `<option value="${p.id}">${esc(p.course)} · ${esc(p.name)}</option>`).join("");
  $("#up-class").value = prev;
  $("#up-add select[name=professor_id]").innerHTML = classes.map((p) => `<option value="${p.id}">${esc(p.course)}</option>`).join("");
  render();
}

$("#up-class").onchange = render;
$("#up-show-done").onchange = render;

// ---------- actions on items ----------
function replaceItem(updated) {
  const i = items.findIndex((x) => x.id === updated.id);
  const prof = classes.find((p) => p.id === updated.professor_id);
  items[i] = { ...updated, course: prof?.course || items[i].course, professor_name: prof?.name || "" };
}

$("#up-groups").addEventListener("change", async (e) => {
  const el = e.target.closest(".up-item");
  if (!el) return;
  const it = items.find((x) => x.id === Number(el.dataset.id));
  try {
    if (e.target.dataset.act === "done") {
      replaceItem(await api("PATCH", `/api/items/${it.id}`, { done: e.target.checked }));
      if (e.target.checked) toast("Nice work! ✓");
      render();
    } else if (e.target.dataset.check !== undefined) {
      const checklist = it.checklist.map((c, i) => (i === Number(e.target.dataset.check) ? { ...c, done: e.target.checked } : c));
      replaceItem(await api("PATCH", `/api/items/${it.id}`, { checklist }));
      render();
    }
  } catch (err) { alert(err.message); load(); }
});

$("#up-groups").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-act]");
  const el = e.target.closest(".up-item");
  if (!btn || !el) return;
  const it = items.find((x) => x.id === Number(el.dataset.id));
  const act = btn.dataset.act;
  try {
    if (act === "edit") { openEdits.add(it.id); render(); }
    else if (act === "cancel-edit") { openEdits.delete(it.id); render(); }
    else if (act === "save-edit") {
      const body = {};
      el.querySelectorAll("[data-e]").forEach((f) => (body[f.dataset.e] = f.value));
      replaceItem(await api("PATCH", `/api/items/${it.id}`, body));
      openEdits.delete(it.id);
      render();
      toast("Saved");
    } else if (act === "delete") {
      if (!confirm(`Delete “${it.title}”?`)) return;
      await api("DELETE", `/api/items/${it.id}`);
      items = items.filter((x) => x.id !== it.id);
      render();
    } else if (act === "checklist") {
      if (it.checklist.length && !confirm("Replace this checklist with a new one?")) return;
      btn.disabled = true;
      btn.textContent = "✨ Writing checklist…";
      replaceItem(await api("POST", `/api/items/${it.id}/checklist`));
      render();
    }
  } catch (err) {
    alert(err.message);
    render();
  }
});

// ---------- adding an item by hand ----------
const addForm = $("#up-add");
$("#up-add-btn").onclick = () => {
  if (!classes.length) return alert("Add a class first (Professors page).");
  addForm.reset();
  if ($("#up-class").value) addForm.elements.professor_id.value = $("#up-class").value;
  addForm.classList.remove("hidden");
  addForm.elements.title.focus();
};
$("#up-add-cancel").onclick = () => addForm.classList.add("hidden");
addForm.onsubmit = async (e) => {
  e.preventDefault();
  const body = Object.fromEntries(new FormData(addForm));
  body.professor_id = Number(body.professor_id);
  try {
    await api("POST", "/api/items", body);
    addForm.classList.add("hidden");
    toast("Added");
    load();
  } catch (err) { alert(err.message); }
};

load();
