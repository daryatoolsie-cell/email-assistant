const TYPE_LABELS = {
  sick: "Sick", missing_class: "Missing Class", extension: "Extension Request",
  question: "Question About Assignment", office_hours: "Office Hours Meeting", custom: "Custom",
};

let professors = [];
let selected = null;      // currently selected professor
let currentDraftId = null; // history row of the draft on screen
let currentType = null;    // which button made it (for Regenerate)

// ---------- professors ----------
async function loadProfessors() {
  professors = await api("GET", "/api/professors");
  const list = $("#prof-list");
  list.innerHTML = professors.map((p) => `
    <div class="card ${selected?.id === p.id ? "selected" : ""}" data-id="${p.id}">
      <div class="title">Email ${esc(p.course)} Professor</div>
      <div class="sub">${esc(p.name)} · ${esc(p.email)}</div>
      ${p.notes ? `<div class="sub">📝 ${esc(p.notes)}</div>` : ""}
      <div class="actions">
        <button class="link" data-edit="${p.id}">Edit</button>
        <button class="link danger" data-delete="${p.id}">Delete</button>
      </div>
    </div>`).join("");
  $("#prof-empty").classList.toggle("hidden", professors.length > 0);
}

const form = $("#prof-form");

function openForm(p = {}) {
  form.reset();
  for (const k of ["id", "name", "email", "course", "notes"]) form.elements[k].value = p[k] ?? "";
  form.classList.remove("hidden");
  form.elements.name.focus();
}

$("#show-add").onclick = () => openForm();
$("#prof-cancel").onclick = () => form.classList.add("hidden");

form.onsubmit = async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(form));
  try {
    if (data.id) await api("PUT", `/api/professors/${data.id}`, data);
    else await api("POST", "/api/professors", data);
    form.classList.add("hidden");
    toast("Saved");
    await loadProfessors();
    if (selected && String(selected.id) === data.id) selectProfessor(Number(data.id));
  } catch (err) { alert(err.message); }
};

$("#prof-list").onclick = async (e) => {
  const editId = e.target.dataset.edit;
  const delId = e.target.dataset.delete;
  if (editId) return openForm(professors.find((p) => p.id == editId));
  if (delId) {
    const p = professors.find((p) => p.id == delId);
    if (!confirm(`Delete ${p.name} (${p.course})?`)) return;
    await api("DELETE", `/api/professors/${delId}`);
    if (selected?.id == delId) { selected = null; $("#draft-panel").classList.add("hidden"); }
    return loadProfessors();
  }
  const card = e.target.closest(".card");
  if (card) selectProfessor(Number(card.dataset.id));
};

function selectProfessor(id) {
  selected = professors.find((p) => p.id === id);
  document.querySelectorAll(".card").forEach((c) => c.classList.toggle("selected", Number(c.dataset.id) === id));
  $("#draft-title").textContent = `Email ${selected.name} — ${selected.course}`;
  $("#draft-panel").classList.remove("hidden");
  $("#draft-output").classList.add("hidden");
  currentDraftId = null;
  currentType = null;
  $("#status").textContent = "Pick the kind of email you need.";
  $("#status").className = "muted";
  document.querySelectorAll(".type-btn").forEach((b) => b.classList.remove("active"));
  $("#draft-panel").scrollIntoView({ behavior: "smooth" });
}

// ---------- drafting ----------
document.querySelectorAll(".type-btn").forEach((btn) => {
  btn.onclick = () => generate(btn.dataset.type, btn);
});

// Disable every AI button while Claude is working, so you can't double-click.
function setBusy(busy, message) {
  document.querySelectorAll(".type-btn, .tweak-buttons button").forEach((b) => (b.disabled = busy));
  if (message) {
    $("#status").textContent = message;
    $("#status").className = "muted";
  }
}

function showError(err) {
  $("#status").textContent = err.message;
  $("#status").className = "error";
}

function showDraft(d) {
  if (d.to) $("#out-to").value = d.to;
  $("#out-subject").value = d.subject;
  $("#out-body").value = d.body;
  $("#draft-output").classList.remove("hidden");
}

async function generate(type, btn, regenerate = false) {
  if (!selected) return;
  if (btn) document.querySelectorAll(".type-btn").forEach((b) => b.classList.toggle("active", b === btn));
  setBusy(true, regenerate ? "🔄 Writing a new version…" : "✍️ Writing your email…");
  try {
    const d = await api("POST", "/api/draft", {
      professor_id: selected.id, draft_type: type, details: $("#details").value,
      draft_id: regenerate ? currentDraftId : null,
    });
    currentDraftId = d.id;
    currentType = type;
    showDraft(d);
    $("#status").textContent = "Here's your draft. Edit anything you like.";
    loadHistory();
  } catch (err) {
    showError(err);
  } finally {
    setBusy(false);
  }
}

$("#btn-regenerate").onclick = () => {
  if (currentType) generate(currentType, null, true);
};

const STYLE_MESSAGES = { shorter: "✂️ Shortening…", formal: "🎓 Making it more formal…", casual: "😊 Making it more casual…" };

document.querySelectorAll("[data-style]").forEach((btn) => {
  btn.onclick = async () => {
    const style = btn.dataset.style;
    setBusy(true, STYLE_MESSAGES[style]);
    try {
      const d = await api("POST", "/api/rewrite", {
        style, draft_id: currentDraftId, professor_id: selected?.id,
        subject: $("#out-subject").value, body: $("#out-body").value,
      });
      showDraft(d);
      $("#status").textContent = "Updated. Keep tweaking or copy it when it's ready.";
      loadHistory();
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  };
});

// Save manual edits to history when you click away from the subject/body
async function saveEdits() {
  if (!currentDraftId) return;
  await api("PUT", `/api/history/${currentDraftId}`, {
    subject: $("#out-subject").value, body: $("#out-body").value,
  });
  loadHistory();
}
$("#out-subject").onchange = saveEdits;
$("#out-body").onchange = saveEdits;

const draft = () => ({ to: $("#out-to").value, subject: $("#out-subject").value, body: $("#out-body").value });

$("#btn-copy").onclick = async () => {
  const { subject, body } = draft();
  await copyText(`Subject: ${subject}\n\n${body}`);
  toast("Copied to clipboard");
};

$("#btn-outlook").onclick = () => {
  const { to, subject, body } = draft();
  const q = new URLSearchParams({ to, subject, body }).toString().replace(/\+/g, "%20");
  openExternal(`https://outlook.office.com/mail/deeplink/compose?${q}`);
};

$("#btn-mailapp").onclick = () => {
  const { to, subject, body } = draft();
  openExternal(`mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`);
};

// ---------- history ----------
async function loadHistory() {
  const items = await api("GET", "/api/history");
  $("#history").innerHTML = items.map((d) => `
    <details class="history-item">
      <summary><strong>${esc(d.subject)}</strong>
        <div class="meta">${esc(TYPE_LABELS[d.draft_type] || d.draft_type)} · ${esc(d.professor_name)} (${esc(d.course)}) · ${esc(d.created_at)}</div>
      </summary>
      <pre>${esc(d.body)}</pre>
      <button class="link" data-copy="${d.id}">Copy</button>
      <button class="link danger" data-del="${d.id}">Delete</button>
    </details>`).join("");
  $("#history-empty").classList.toggle("hidden", items.length > 0);
  $("#history").onclick = async (e) => {
    const item = items.find((d) => d.id == (e.target.dataset.copy || e.target.dataset.del));
    if (!item) return;
    if (e.target.dataset.copy) {
      await copyText(`Subject: ${item.subject}\n\n${item.body}`);
      toast("Copied to clipboard");
    } else if (confirm("Delete this draft from history?")) {
      await api("DELETE", `/api/history/${item.id}`);
      loadHistory();
    }
  };
}

loadProfessors();
loadHistory();
